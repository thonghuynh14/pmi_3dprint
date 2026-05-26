# Marketplace Connectors

Mỗi marketplace có 1 connector class implement interface chung. Pattern: Strategy + Adapter.

## Base interface

```python
# apps/channels/connectors/base.py
from abc import ABC, abstractmethod
from typing import Protocol
from dataclasses import dataclass


@dataclass
class ChannelCredentials:
    shop_id: str
    access_token: str
    refresh_token: str | None = None
    expires_at: float | None = None
    extra: dict = None


@dataclass
class PushProductResult:
    external_product_id: str
    external_sku_ids: dict[str, str]  # local_sku → external_sku_id
    warnings: list[str]


class BaseConnector(ABC):
    """Interface cho mọi marketplace connector."""
    
    channel: str  # 'shopee' | 'lazada' | 'tiki'
    
    def __init__(self, credentials: ChannelCredentials):
        self.credentials = credentials
    
    @abstractmethod
    def refresh_token_if_needed(self) -> ChannelCredentials: ...
    
    @abstractmethod
    def create_product(self, listing) -> PushProductResult: ...
    
    @abstractmethod
    def update_product(self, listing) -> PushProductResult: ...
    
    @abstractmethod
    def update_stock(self, variants_stock: dict[str, int]) -> dict: ...
    
    @abstractmethod
    def update_price(self, variants_price: dict[str, float]) -> dict: ...
    
    @abstractmethod
    def list_orders(self, since): ...
    
    @abstractmethod
    def handle_webhook(self, payload: dict, signature: str) -> dict: ...
```

## Shopee connector

```python
# apps/channels/connectors/shopee.py
import hashlib
import hmac
import time
import requests
from django.conf import settings
from apps.channels.connectors.base import BaseConnector, PushProductResult


class ShopeeConnector(BaseConnector):
    channel = 'shopee'
    BASE_URL = 'https://partner.shopeemobile.com'
    SANDBOX_URL = 'https://partner.test-stable.shopeemobile.com'
    
    @property
    def base_url(self):
        return self.SANDBOX_URL if settings.SHOPEE_SANDBOX else self.BASE_URL
    
    def _sign(self, path: str, timestamp: int) -> str:
        """HMAC-SHA256 sign for Shopee Open Platform v2."""
        partner_id = settings.SHOPEE_PARTNER_ID
        partner_key = settings.SHOPEE_PARTNER_KEY.encode()
        access_token = self.credentials.access_token
        shop_id = self.credentials.shop_id
        
        base_string = f"{partner_id}{path}{timestamp}{access_token}{shop_id}".encode()
        return hmac.new(partner_key, base_string, hashlib.sha256).hexdigest()
    
    def _request(self, method: str, path: str, json=None, params=None):
        timestamp = int(time.time())
        sign = self._sign(path, timestamp)
        
        query = {
            'partner_id': settings.SHOPEE_PARTNER_ID,
            'timestamp': timestamp,
            'access_token': self.credentials.access_token,
            'shop_id': self.credentials.shop_id,
            'sign': sign,
            **(params or {}),
        }
        url = f"{self.base_url}{path}"
        resp = requests.request(method, url, params=query, json=json, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if data.get('error'):
            raise ShopeeAPIError(data['error'], data.get('message'))
        return data
    
    def refresh_token_if_needed(self):
        if self.credentials.expires_at and time.time() < self.credentials.expires_at - 300:
            return self.credentials
        # Call /api/v2/auth/access_token/get with refresh_token
        ...
    
    def create_product(self, listing) -> PushProductResult:
        variant = listing.variant
        product = variant.product
        
        # Step 1: add_item (creates base item)
        item_payload = {
            'original_price': float(variant.base_price),
            'description': product.long_description[:3000],
            'item_name': product.name[:120],
            'category_id': listing.channel_attributes.get('shopee_category_id'),
            'item_status': 'NORMAL',
            'images': {
                'image_id_list': self._upload_images(product),
            },
            'weight': float(variant.weight_g or 100) / 1000,  # kg
            'dimension': {
                'package_length': int(variant.dimensions_mm.get('l', 10)),
                'package_width': int(variant.dimensions_mm.get('w', 10)),
                'package_height': int(variant.dimensions_mm.get('h', 10)),
            },
            'logistic_info': listing.channel_attributes.get('logistics', []),
        }
        
        result = self._request('POST', '/api/v2/product/add_item', json=item_payload)
        external_item_id = result['response']['item_id']
        
        # Step 2: init_item for tier variations if multi-variant
        sibling_variants = product.variants.filter(status='active')
        if sibling_variants.count() > 1:
            self._init_tier_variations(external_item_id, sibling_variants)
        
        return PushProductResult(
            external_product_id=str(external_item_id),
            external_sku_ids={variant.sku: str(external_item_id)},
            warnings=[],
        )
    
    def update_stock(self, variants_stock: dict[str, int]):
        """variants_stock = {external_sku_id: quantity}.
        
        Shopee giới hạn 50 variants/call → batch.
        """
        items = [
            {'model_id': int(sid), 'normal_stock': qty}
            for sid, qty in variants_stock.items()
        ]
        results = []
        for batch in _chunked(items, 50):
            r = self._request('POST', '/api/v2/product/update_stock', json={
                'item_id': ...,
                'stock_list': batch,
            })
            results.append(r)
        return results
    
    def handle_webhook(self, payload: dict, signature: str):
        # Verify signature first
        body = json.dumps(payload).encode()
        expected = hmac.new(
            settings.SHOPEE_PARTNER_KEY.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise InvalidWebhookSignature()
        
        # Dispatch by event type
        code = payload.get('code')
        if code == 3:  # Order status update
            from apps.channels.tasks import process_shopee_order_webhook
            process_shopee_order_webhook.delay(payload)
        ...


class ShopeeAPIError(Exception):
    def __init__(self, error_code, message):
        self.error_code = error_code
        self.message = message
        super().__init__(f"[{error_code}] {message}")
```

## Lazada connector

```python
# apps/channels/connectors/lazada.py
import hashlib
import hmac
import time
from urllib.parse import quote
from xml.etree.ElementTree import Element, SubElement, tostring

class LazadaConnector(BaseConnector):
    channel = 'lazada'
    BASE_URL_VN = 'https://api.lazada.vn/rest'
    
    def _sign(self, api_path: str, params: dict) -> str:
        """HMAC-SHA256 of sorted params, hex uppercase."""
        sorted_params = sorted(params.items())
        base = api_path + ''.join(f"{k}{v}" for k, v in sorted_params)
        sign = hmac.new(
            settings.LAZADA_APP_SECRET.encode(),
            base.encode(),
            hashlib.sha256,
        ).hexdigest().upper()
        return sign
    
    def create_product(self, listing) -> PushProductResult:
        """POST /product/create with XML body."""
        variant = listing.variant
        product = variant.product
        
        # Build XML
        root = Element('Request')
        product_el = SubElement(root, 'Product')
        
        primary_category = SubElement(product_el, 'PrimaryCategory')
        primary_category.text = str(listing.channel_attributes.get('lazada_category_id'))
        
        attributes = SubElement(product_el, 'Attributes')
        SubElement(attributes, 'name').text = product.name[:255]
        SubElement(attributes, 'short_description').text = product.short_description[:255]
        SubElement(attributes, 'description').text = product.long_description
        SubElement(attributes, 'brand').text = product.brand.name if product.brand else 'No Brand'
        
        skus = SubElement(product_el, 'Skus')
        for sibling in product.variants.filter(status='active'):
            sku_el = SubElement(skus, 'Sku')
            SubElement(sku_el, 'SellerSku').text = sibling.sku
            SubElement(sku_el, 'price').text = str(sibling.base_price)
            SubElement(sku_el, 'package_length').text = str(sibling.dimensions_mm.get('l', 10))
            # ... 8 images, color, size attrs
        
        body = tostring(root, encoding='unicode')
        return self._request('POST', '/product/create', body=body)
```

## Tiki connector

```python
# apps/channels/connectors/tiki.py
class TikiConnector(BaseConnector):
    channel = 'tiki'
    BASE_URL = 'https://api.tiki.vn/integration'
    
    MAX_OPTION_ATTRIBUTES = 2  # Tiki hard limit
    
    def create_product(self, listing) -> PushProductResult:
        variant = listing.variant
        product = variant.product
        
        # Check Tiki 2-axes limit
        active_axes = self._count_active_axes(product)
        if len(active_axes) > self.MAX_OPTION_ATTRIBUTES:
            raise TikiOptionAttributesExceededError(
                f"Product has {len(active_axes)} variant axes but Tiki supports max 2. "
                f"Active axes: {active_axes}. Suggestions: merge to composite axis."
            )
        
        payload = {
            'product': {
                'sku': product.sku_root,
                'name': product.name[:120],
                'description': product.long_description,
                'category_id': listing.channel_attributes.get('tiki_category_id'),
                'attributes': self._map_attributes(product, listing),
                'images': self._build_images(product),
                'option1': active_axes[0] if len(active_axes) >= 1 else None,
                'option2': active_axes[1] if len(active_axes) >= 2 else None,
            },
            'variants': [
                {
                    'sku': v.sku,
                    'price': float(v.base_price),
                    'option1': v.axes.get(active_axes[0]) if len(active_axes) >= 1 else None,
                    'option2': v.axes.get(active_axes[1]) if len(active_axes) >= 2 else None,
                    'quantity': self._compute_pushable_stock(v, listing),
                }
                for v in product.variants.filter(status='active')
            ],
        }
        
        return self._request('POST', '/v2/requests', json=payload)
    
    def update_sku_multi_warehouse(self, sku: str, warehouse_qtys: dict):
        """PUT /v2.1/products/updateSku - update price + stock per warehouse."""
        ...
```

## Token storage

```python
# apps/channels/models/credentials.py
from django.db import models
from django.utils.encryption import encrypt_field  # custom helper

class MarketplaceCredential(models.Model):
    channel = models.CharField(max_length=16)  # shopee/lazada/tiki
    shop_id = models.CharField(max_length=64)
    access_token_encrypted = models.TextField()  # AES-encrypted
    refresh_token_encrypted = models.TextField(blank=True)
    expires_at = models.DateTimeField(null=True)
    extra = models.JSONField(default=dict)  # partner_id, region, etc.
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('channel', 'shop_id')
```

## Rate limit guard

```python
# apps/channels/connectors/rate_limiter.py
from django.core.cache import cache
import time

def rate_limit(channel: str, shop_id: str, max_per_sec: int = 5):
    key = f"rl:{channel}:{shop_id}"
    now = time.time()
    
    pipe = cache.client.get_client().pipeline()
    pipe.zremrangebyscore(key, 0, now - 1)
    pipe.zcard(key)
    pipe.zadd(key, {str(now): now})
    pipe.expire(key, 2)
    _, count, _, _ = pipe.execute()
    
    if count >= max_per_sec:
        time.sleep(1)  # Or raise BackoffRequired exception
```
