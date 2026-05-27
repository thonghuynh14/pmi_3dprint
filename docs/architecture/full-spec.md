# Spec hệ thống quản lý sản phẩm & SKU cho doanh nghiệp in 3D bán đa kênh

## TL;DR
- **Khuyến nghị kiến trúc cốt lõi**: Build hệ thống PIM-lite tự phát triển trên **PostgreSQL 16 + JSONB cho attributes biến động**, **NestJS (TypeScript) backend**, **Next.js + react-stl-viewer/Google `<model-viewer>` frontend**, **MinIO/S3 cho file STL/GCODE**, **Meilisearch cho catalog search**, và **Redis + BullMQ làm queue cho job sync đa kênh** — đây là stack cho phép team nhỏ (3–5 dev) đi từ MVP đến production trong 3–4 tháng mà không bị khóa vào vendor.
- **Mô hình dữ liệu chốt**: lấy cảm hứng từ Akeneo (Product → ProductModel → Variant với family_variant) nhưng đơn giản hóa thành 3 tầng: `Product` (thông tin chung) → `Variant` (biến thể vật lý có SKU + barcode) → `ChannelListing` (mapping với Shopee item_id, Lazada SkuId, Tiki product_id). Mỗi Variant có BOM định lượng vật liệu (gram filament, ml resin) và mapping đến danh sách máy in tương thích.
- **Pitfall lớn nhất cần né**: (1) đặt SKU không nhất quán giữa các kênh → mất sync inventory và overselling; (2) lưu file STL vào RDBMS thay vì object storage; (3) hardcode attribute (color, material) thành cột thay vì dùng JSONB → mỗi lần thêm thuộc tính mới phải migration. Tuân thủ "1 master SKU = 1 mapping row" và bảng `channel_mappings` riêng cho từng marketplace.

## Key Findings

### Khả thi kỹ thuật & lựa chọn nền tảng
1. **PIM thương mại không đáng đầu tư cho use case 3D printing**. Theo Akeneo Product Support Dates (help.akeneo.com), Akeneo PIM v7 (release 8/3/2023) chỉ được support đến **30/9/2026** cho cả Community và Enterprise — sau đó CE users không có upgrade path miễn phí; CEO Fred de Gombert cũng đã xác nhận Akeneo dồn lực phát triển vào bản Serenity SaaS. Pimcore thì là PIM+MDM+DAM tổng thể, implementation cost rất cao và đòi hỏi nhiều dev resource. Cả hai đều thiếu các khái niệm đặc thù 3D printing (file STL versioning, BOM theo gram filament, mapping máy in) — phải custom dù chọn nền tảng nào, nên tự build sẽ chủ động hơn.
2. **EAV pattern (Magento-style) đã lỗi thời với PostgreSQL hiện đại**. Theo benchmark thực nghiệm của Jeroen Coussement (coussej.github.io, 2016) với 10 triệu entities × 7 thuộc tính, query có indexed lookup trên JSONB với GIN + `@>` containment operator hoàn thành trong **0.153 ms — nhanh gấp ~15.000 lần so với EAV** trên cùng bộ dữ liệu; đồng thời storage footprint của 1 bảng JSONB + GIN index nhỏ hơn đáng kể so với 3 bảng EAV + 3 indexes (mức cụ thể phụ thuộc số attribute/entity). Đặc biệt phù hợp với catalog 3D printing có nhiều thuộc tính tùy chọn theo loại sản phẩm (figure cosplay khác với gadget cơ khí).
3. **Marketplace API integration phức tạp hơn nhiều người tưởng**:
   - **Shopee Open Platform v2** dùng HMAC-SHA256 sign với base string `${PARTNER_ID}${path}${timestamp}${accessToken}${shopId}`, access token TTL = 14400 giây (4 giờ — xác nhận chéo từ Rollout integration guide); endpoints chính: `POST /api/v2/product/add_item`, `POST /api/v2/product/init_item` (kích hoạt tier-variation), `POST /api/v2/product/update_price`, `POST /api/v2/product/update_stock` (max 50 variations/call), `GET /api/v2/product/get_item_list`. Production host `partner.shopeemobile.com`, sandbox `partner.test-stable.shopeemobile.com`.
   - **Lazada Open Platform** dùng OAuth 2.0 + signed request (HMAC-SHA256, hex uppercase, `sign_method=sha256`); token endpoint `POST https://auth.lazada.com/rest/auth/token/create` trả `expires_in: 604800` giây (7 ngày) cho access token, refresh token ~30 ngày; có khái niệm SPU (Standard Product Unit, master product) ↔ PRODUCT ↔ SKU (variant) với endpoint `POST /product/create`, `POST /product/price_quantity/update`, regional host VN là `https://api.lazada.vn/rest`. Tài liệu Lazada Seller Center API: *"The highest level of an SKU is SPU. A product inherits attributes from the SPU, and the SKU inherits attributes from the PRODUCT... One item may contain at least one SKU which has 8 images."*
   - **Tiki Open API** dùng OAuth 2.0 đầy đủ, token endpoint `POST https://api.tiki.vn/sc/oauth2/token`, scopes là `offline product order` (scope `all` đã deprecated); **giới hạn cứng tối đa 2 option attributes** mỗi sản phẩm — verbatim từ docs Tiki: *"Tiki support up to 2 option attributes (size, color, capacity, …) so if you have products with more than 2, combine them or create separate products before making a product request."* Endpoint chính: `POST /integration/v2/requests` (tạo product), `PUT /integration/v2.1/products/updateSku` (update đa kho).
4. **Đặc thù sản phẩm in 3D đòi hỏi data model riêng**:
   - Biến thể không chỉ là size/color như thời trang mà còn loại vật liệu (PLA, PLA+, ABS, PETG, TPU, ASA, Nylon, PC, PEEK; resin Standard/Tough/Flexible/Castable; SLS PA12), độ phân giải layer (0.08–0.32mm cho FDM, 25–100µm cho SLA), infill % (10–100%), nhiệt độ in (PLA ~190–220°C nozzle vs ABS ~230–260°C).
   - Cost calculation phải bao gồm 5 thành phần: vật liệu (gram × đơn giá/kg), điện năng (kWh = wattage × hour ÷ 1000 × tariff), khấu hao máy (giá máy ÷ tuổi thọ giờ in, thường 3.000–10.000 giờ theo Printpal/Snapmaker), labor (pre-press + post-processing) và buffer thất bại (~5%). Shapeways còn cộng thêm machine space cost (volume bounding box trong build plate, lost opportunity cost).
   - File STL có thể nặng 5–500 MB → bắt buộc dùng S3-compatible object storage, không lưu trong database.
5. **License management là rủi ro pháp lý** khi nhập file từ Thingiverse/Printables/Cults3D. CC BY-NC là license phổ biến nhất cho file miễn phí — **không được bán in commercial** dù có gắn credit. Hệ thống phải bắt buộc nhập license type cho mọi file thiết kế import từ bên ngoài, và block không cho gắn vào SKU "đang bán" nếu license = NC.

### Pitfall điển hình
- **Overselling** do sync chậm: một sàn bán hết stock, sàn khác vẫn còn listing → khách order → cancel → bị marketplace phạt account health. Giải pháp: real-time webhook + safety stock buffer 5–10% trên mỗi kênh.
- **SKU không khớp giữa kênh**: SKU nội bộ `PLA-RED-S` nhưng trên Shopee gõ thành `PLA_RED_S` → bridge sync không match được. Phải có bảng `channel_mapping` cứng và validate trước khi push.
- **Variant explosion**: 5 màu × 4 vật liệu × 3 size × 3 độ phân giải = 180 SKU cho 1 sản phẩm. Phần lớn sẽ không bao giờ bán → audit quarterly và retire variants có velocity < 10 units/90 ngày.
- **Tiki hard limit 2 option attributes** → phải merge các biến thể ít quan trọng vào tên SKU thay vì làm option khi push lên Tiki.

---

## Details

### 1. Module Quản lý Catalog sản phẩm in 3D

**Cấu trúc dữ liệu sản phẩm chính** (`products` table):
```
id (uuid PK)
sku_root (varchar 16, unique) -- mã gốc, không thay đổi
name (varchar 200)
slug (varchar 220, unique)
short_description (text)
long_description (text, rich-text/markdown)
brand_id (fk)
status (enum: draft, idea, poc, production, archived)
lifecycle_stage (enum: idea, concept, prototype, ready, selling, eol)
default_variant_id (fk -> variants, nullable)
seo_title, seo_description, seo_keywords (varchar/text)
attributes (jsonb) -- thuộc tính chung (dimensions, weight bao bì, etc.)
tags (text[]) -- gin-indexed
created_at, updated_at, deleted_at
created_by, updated_by (fk users)
```

**Category phân cấp** dùng pattern `materialized path` hoặc `nested set` để query subtree nhanh:
```
categories
  id, parent_id, path (ltree hoặc text "1.4.12"), name, slug, depth, sort_order
product_categories (m2m)
  product_id, category_id, is_primary
```
Lý do dùng `ltree` (PostgreSQL extension) thay vì self-join đệ quy: query "tất cả sản phẩm thuộc danh mục cha + cháu" chỉ cần `WHERE path <@ 'gadget.phone_accessory'` thay vì recursive CTE.

**Media (hình ảnh đa góc, video, model 3D)**:
```
media_assets
  id, owner_type (product|variant|design_file), owner_id,
  type (image|video|3d_model|document),
  storage_key (s3 key), cdn_url, mime_type, size_bytes,
  width, height, duration_seconds,
  alt_text, caption, position (sort), is_primary,
  metadata (jsonb) -- exif, thumbnail URLs, etc.
```
- Hình sản phẩm: 8 góc (front, back, left, right, top, bottom, perspective, scale-reference) — match đúng số ảnh tối đa Lazada cho phép mỗi SKU (theo docs Lazada: *"One item may contain at least one SKU which has 8 images"*).
- Video: hỗ trợ MP4 ≤ 30s cho marketplace, lưu MinIO + transcode bằng FFmpeg worker.
- 3D model preview: GLB/GLTF cho web (dùng Google `<model-viewer>` web component, hỗ trợ AR trên Android/iOS), STL cho download/in.

**SEO metadata**: lưu cùng level product, có thể override theo channel (Shopify website cần meta_title khác với Shopee description).

### 2. Module SKU & Variants (đặc thù 3D)

**Variants table** — đây là bảng "hàng được bán":
```
variants
  id (uuid PK)
  product_id (fk products)
  sku (varchar 32, unique) -- mã đầy đủ, vd "FIG-DRAGON-PLA-RED-S-02"
  barcode (varchar 14, nullable) -- EAN-13 hoặc internal 020-029 prefix
  qr_code_url (text) -- pre-generated PNG path
  
  -- variant axes (5 trục đặc thù 3D printing)
  material_type (fk materials) -- PLA, ABS, PETG, resin, etc.
  material_color (varchar 32) -- red, blue, transparent...
  size_preset (varchar 16) -- S/M/L/XL hoặc 100mm/150mm
  layer_resolution_mm (decimal 4,3) -- 0.08, 0.12, 0.20, 0.28
  infill_percent (smallint) -- 10, 20, 50, 100
  
  -- bán hàng
  base_price (numeric 12,2)
  cost_price (numeric 12,2) -- giá vốn tính từ POC mới nhất
  weight_g (decimal 8,2) -- nặng thật (gram)
  dimensions_mm (jsonb) -- {l, w, h}
  
  -- thuộc tính mở rộng (EAV-lite qua JSONB)
  attributes (jsonb) 
  
  status (enum: active, inactive, oos, eol)
  is_made_to_order (boolean) -- true nếu in theo order
  lead_time_hours (smallint) -- thời gian giao tối thiểu nếu MTO
  
  created_at, updated_at
```

**Quy tắc đặt tên SKU (naming convention chuẩn)** — tham chiếu best-practice Shopify Help Center (*"Keep your SKUs as short as possible, such as no more than 16 characters... Don't use special characters, symbols, or spaces"*) và OmniOrders SKU guide:
- **Pattern**: `[CAT3]-[PROD]-[MAT]-[COLOR]-[SIZE]-[NN]`
- **Độ dài**: 12–24 ký tự, uppercase, dấu gạch ngang, **không space/special char**.
- **Ví dụ cụ thể**:
  - `FIG-DRAGON-PLA-RED-M-01` (figure rồng, PLA đỏ, size M, lần in 01)
  - `GDT-PHCASE-TPU-BLK-IP15-01` (gadget phone case, TPU đen, model iPhone 15)
  - `JWL-RING-RES-CLR-7-01` (jewelry ring, resin trong, size 7)
- **Auto-generate logic**:
  ```pseudo
  function generateSKU(product, axes):
    parts = [
      category.code_3,            # FIG, GDT, JWL
      product.slug_compact_6,     # DRAGON, PHCASE
      material.code_3,            # PLA, ABS, RES, TPU
      color.code_3,               # RED, BLK, CLR
      size.code,                  # S, M, L, IP15, 7
      next_sequence(2)            # 01, 02
    ]
    return join('-', parts)
  ```
- **Bảng abbreviation library** (`sku_codes`): lưu mapping `entity_type` + `value` → `code`, ví dụ `material PLA → PLA`, `color "Royal Blue" → BLU`. Bắt buộc tham chiếu để không bị "Royal Blue" lúc viết `RBL`, lúc viết `BLU`.

**Barcode/QR generation**:
- Barcode: dùng GS1 prefix nội bộ `020`–`029` cho EAN-13 trong-nhà (theo tài liệu chính thức GS1 "Summary of GS1 Prefixes 20–29 by GS1 Member Organisation" và Wikipedia EAN-13: *"GS1 defines the prefixes 020–029 as being available for retailer internal use... Some retailers use this for proprietary (own brand or unbranded) products"*). Khi cần bán retail offline có scan tại POS thật thì mới đăng ký GS1 Company Prefix.
- QR code: encode URL `https://shop.domain/p/{sku}` → khách scan thấy trang chi tiết sản phẩm. Tem in qua máy in nhiệt khổ 40×25mm.
- Library: `bwip-js` (Node.js) cho EAN-13, `qrcode` npm package cho QR.

### 3. Module File thiết kế 3D

**Bảng `design_files`**:
```
design_files
  id, product_id (nullable, có thể chưa gắn product),
  filename, storage_key, cdn_url,
  format (enum: stl, obj, 3mf, step, gcode, blend, fbx, gltf),
  size_bytes,
  triangles_count (int, parse STL header),
  bounding_box (jsonb {x, y, z}),
  
  version (varchar 16) -- v1.0, v1.1
  parent_file_id (fk self) -- để build version tree
  changelog (text)
  
  source (enum: original, thingiverse, printables, cults3d, mymf, commission),
  source_url (text),
  source_author (varchar 200),
  
  license_type (enum: cc0, cc_by, cc_by_sa, cc_by_nc, cc_by_nc_sa, cc_by_nd, all_rights_reserved, custom, proprietary),
  license_allows_commercial (boolean) -- derived field, dùng để validate
  license_requires_attribution (boolean)
  license_notes (text)
  
  uploaded_by (fk), uploaded_at
```

**Versioning**: dùng pattern parent_file_id self-reference + version string semver-like. Khi upload file mới với cùng `product_id`, system clone metadata, increment version, link parent.

**Preview 3D trên web**:
- **GLB** (binary glTF) là format khuyến nghị cho preview vì size nhỏ + load nhanh + được Google `<model-viewer>` hỗ trợ native (per `modelviewer.dev` docs và Google ARCore developer site: *"Models in the gltf and glb file format are supported by `<model-viewer>`"*). Pipeline: dev upload STL → background worker convert STL → GLB qua `assimp` hoặc `gltf-pipeline` → lưu kèm.
- Frontend: 
  ```html
  <model-viewer 
    src="/files/{id}.glb" 
    poster="/files/{id}-thumb.jpg"
    ar ar-modes="webxr scene-viewer quick-look"
    camera-controls 
    auto-rotate>
  </model-viewer>
  ```
- Alternative: `react-stl-viewer` (gabotechs/react-stl-viewer trên npm) nếu chỉ cần STL.

**Quản lý license — flow nghiệp vụ bắt buộc**:
1. Upload file → form bắt buộc chọn license_type.
2. Nếu license = `cc_by_nc` → đặt `license_allows_commercial = false`.
3. Khi gắn file vào `variant.design_file_id` và `variant.status` chuyển sang `active` (bán), system check `license_allows_commercial`. Nếu false → block + show error "License does not permit commercial use".
4. Audit log mọi lần thay đổi license và file binding.

### 4. Module Ý tưởng & POC

**`product_ideas`** — pre-product staging:
```
product_ideas
  id, title, description,
  status (enum: idea, sketching, poc, validated, in_production, rejected, on_hold),
  pipeline_stage (enum: capture, research, prototype, test, launch),
  mood_board_assets (jsonb) -- list of media_asset_ids
  reference_links (jsonb) -- [{url, title, source}]
  estimated_market_demand (enum: low, medium, high),
  notes (text),
  assigned_to (fk users),
  promoted_to_product_id (fk products, nullable) -- khi idea thành sản phẩm thật
  created_at, updated_at
```

**Pipeline UI**: Kanban board với columns = enum `pipeline_stage`. Drag-drop để chuyển stage. Khi idea promoted, system tạo `product` record skeleton và link.

### 5. Module POC & Cost Calculation

**`poc_versions`** — mỗi lần in thử lưu lại 1 version:
```
poc_versions
  id, variant_id (fk),
  version_label (vd "POC-v3"),
  printed_at,
  printer_id (fk printers) -- máy đã dùng
  
  -- inputs từ slicer (Cura/PrusaSlicer/Bambu Studio)
  print_duration_minutes (int),
  filament_used_g (decimal 8,2),
  filament_used_mm (decimal 10,2),
  support_material_g (decimal 8,2),
  
  -- cost breakdown (đơn vị VND)
  material_cost (numeric 12,2),
  electricity_cost (numeric 12,2),
  depreciation_cost (numeric 12,2),
  labor_cost (numeric 12,2),
  postprocess_cost (numeric 12,2),
  failure_buffer_cost (numeric 12,2),
  total_cost (numeric 12,2), -- computed
  
  -- markup
  suggested_price (numeric 12,2),
  markup_strategy (varchar 32), -- "fixed_30pct", "tier_high", "promo"
  
  notes (text),
  attachments (jsonb), -- ảnh kết quả in, gcode link
  is_current (boolean) -- chỉ 1 version active làm baseline pricing
```

**Cost formula chuẩn** (theo công thức của Snapmaker / Prusa / Firgelli):
```
material_cost = (filament_used_g / 1000) × material.price_per_kg
electricity_cost = (printer.wattage / 1000) × print_duration_hours × electricity_tariff
depreciation_cost = print_duration_hours × (printer.purchase_price / printer.lifetime_hours)
labor_cost = (pre_press_minutes + post_process_minutes) / 60 × hourly_rate
failure_buffer_cost = (material_cost + electricity_cost) × failure_rate_percent / 100
total_cost = SUM(all above)
suggested_price = total_cost × (1 + markup_percent / 100) + shipping_buffer
```

**Cấu hình mặc định gợi ý cho Việt Nam (2026)**:
- Điện EVN bậc kinh doanh: ~3.000 VND/kWh.
- PLA bình dân: 350.000–500.000 VND/kg; PETG ~500.000; resin tiêu chuẩn: 800.000–1.500.000/L.
- Lifetime FDM hobby (Ender 3, Bambu A1): ~5.000 giờ; FDM bán công nghiệp (Bambu X1C, Prusa MK4): ~8.000–10.000 giờ.
- Failure rate target: 5% (sản phẩm đã production), 15–20% (POC chưa optimize).

### 6. Module Vật liệu & BOM

**`materials`** — master data vật liệu:
```
materials
  id, code (varchar 16, unique), name,
  type (enum: filament, resin, powder, support, paint, glue, packaging, other),
  subtype (enum: pla, plaplus, abs, petg, tpu, asa, nylon, pc, peek, standard_resin, tough_resin, flexible_resin, pa12, ...),
  color, color_hex,
  diameter_mm (1.75 / 2.85), -- chỉ filament
  density_g_cm3, -- PLA 1.24, ABS 1.04, PETG 1.27 (per EngineerCalc 3D print cost calculator)
  price_per_unit (numeric), unit (g, ml, kg, piece),
  supplier_id (fk),
  print_temp_min_c, print_temp_max_c,
  bed_temp_min_c, bed_temp_max_c,
  requires_enclosure (boolean),
  food_safe (boolean), uv_resistant (boolean),
  notes (text)
```

**`bills_of_material`** — BOM cho mỗi SKU (cấu trúc lấy cảm hứng Odoo Manufacturing BoM):
```
boms
  id, variant_id (fk, unique constraint),
  version, is_active, notes,
  created_at, updated_at

bom_lines
  id, bom_id (fk),
  material_id (fk),
  quantity (decimal 10,3),
  unit (g, ml, piece),
  is_primary (boolean), -- vật liệu chính vs phụ trợ
  notes -- "support PVA dùng cho overhang > 45°"
```

**Use case ví dụ**: variant `FIG-DRAGON-PLA-RED-M-01` có BOM:
- 85g PLA Red (primary)
- 4g PLA White (multicolor body)
- 2g PVA support
- 1 piece hộp giấy 100×80×60mm
- 0.5g super glue (lắp đầu vào thân)

Query "tính tổng PLA Red cần để in batch 100 sản phẩm X" = `SUM(bom_lines.quantity WHERE material = PLA_RED) × 100`.

### 7. Module Máy in (Printer Database)

**`printers`** — danh sách máy của xưởng + máy của partner outsource:
```
printers
  id, code (varchar 16), name, brand, model,
  technology (enum: fdm, sla, msla, dlp, sls, mjf, other),
  build_volume (jsonb {x, y, z}) -- mm
  nozzle_sizes (decimal[]) -- [0.2, 0.4, 0.6, 0.8] cho FDM multi-nozzle
  layer_min_mm, layer_max_mm,
  supported_materials (int[]) -- fk materials
  max_temp_nozzle_c, max_temp_bed_c,
  has_enclosure (boolean), has_ams (boolean), -- AMS = Bambu Auto Material System
  is_active, is_owned, location, -- HCM_1, partner_HN_3
  purchase_price (numeric),
  purchase_date (date),
  lifetime_hours (int) DEFAULT 5000,
  hours_used (int) DEFAULT 0, -- track wear
  notes
```

**Mapping variant ↔ printer**:
```
variant_compatible_printers
  variant_id, printer_id,
  estimated_minutes (int), -- in trên máy này tốn bao nhiêu phút
  is_preferred (boolean),
  notes
```

Production manager khi nhận order chọn máy phù hợp: WHERE has_enclosure=true cho ABS, WHERE supports material_id=X, WHERE build_volume >= product_dimensions.

### 8. Module Đa kênh & Sync

**`channel_listings`** — mapping SKU nội bộ với từng kênh:
```
channel_listings
  id, variant_id (fk),
  channel (enum: shopee, lazada, tiki, shopify, woocommerce, pos),
  shop_id (varchar) -- shop_id Shopee, seller_id Lazada
  external_product_id (varchar) -- item_id Shopee, ProductId Lazada, product_id Tiki
  external_sku_id (varchar) -- variation_id Shopee, SkuId Lazada
  external_seller_sku (varchar) -- "SellerSku" Lazada, original_sku Tiki
  status (enum: synced, draft, error, deleted),
  price_override (numeric, nullable) -- giá khác base trên kênh
  stock_override (int, nullable) -- buffer riêng
  channel_attributes (jsonb) -- attrs riêng theo kênh (vd: shipping class)
  last_synced_at, last_sync_status, last_sync_error,
  external_url (text)
```

**Connector architecture** — 1 connector mỗi marketplace:
```
ChannelConnector (interface)
  authenticate(credentials) -> AccessToken
  refreshToken(refreshToken) -> AccessToken
  pushProduct(variant) -> ExternalProductId
  pushStockUpdate(variant_id, qty) -> Result
  pushPriceUpdate(variant_id, price) -> Result
  pullOrders(since) -> Order[]
  handleWebhook(payload) -> Event
```

**Implementation chi tiết theo từng kênh** (tham chiếu API thật):

| Khía cạnh | Shopee | Lazada | Tiki |
|---|---|---|---|
| Auth | HMAC-SHA256 sign + access_token | OAuth 2.0 + signed (HMAC-SHA256, hex upper) | OAuth 2.0 chuẩn |
| Token TTL | 14400s (4h) | 604800s (7 ngày), refresh ~30 ngày | Theo OAuth 2.0 spec, refresh token |
| Token endpoint | `POST /api/v2/auth/token/get` | `POST https://auth.lazada.com/rest/auth/token/create` | `POST https://api.tiki.vn/sc/oauth2/token` |
| Tạo product | `POST /api/v2/product/add_item` | `POST /product/create` (XML body) | `POST /integration/v2/requests` |
| Init variants | `POST /api/v2/product/init_item` | Inline trong CreateProduct `<Skus>` | option1/option2 inline |
| Update stock | `POST /api/v2/product/update_stock` (≤50 variants/call) | `POST /product/price_quantity/update` | `PUT /integration/v2.1/products/updateSku` (multi-warehouse) |
| Update price | `POST /api/v2/product/update_price` | Cùng endpoint price_quantity | Cùng endpoint updateSku |
| List products | `GET /api/v2/product/get_item_list` | `GET /products/get` | `GET /integration/v2/products/findBy?original_sku=` |
| Variant axes limit | Không hardcoded (tier_variation 2 levels) | Lazada model qua SPU + variant attrs | **Hard limit 2 option attributes** (size + color) |
| Webhook | Push Mechanism Console, callback URL HTTPS | Push notification API | Event queue API |
| Sandbox | `partner.test-stable.shopeemobile.com` | có sandbox riêng | có sandbox |

**Critical**: Tiki giới hạn 2 option_attributes/sản phẩm (verbatim từ docs Tiki: *"option_attributes not valid → TIKI support 2 option attributes at most so if you need more than 2 option, please merge some of them before create product"*). Với 3D printing có thể 5 trục biến thể, phải merge khi sync sang Tiki:
- Strategy 1: Chọn 2 axes quan trọng nhất (vd: color + size), các axis còn lại (material, layer res) tách thành sản phẩm riêng trên Tiki.
- Strategy 2: Tạo composite option (vd "PLA-Red-0.2mm" thành 1 giá trị color).

**Rate limit safety**:
- Shopee: ~10 req/s/shop (theo InlinexDev integration guide: *"Rate limits are per-shop — 10 requests per second for most endpoints"* — community-documented, không phải SLA chính thức). Lazada: trả lỗi *"Api access frequency exceeds the limit. this ban will last 1 seconds"* khi vượt — không có số chính thức. Tiki: chưa publish.
- → Áp dụng token bucket 5 req/s mỗi kênh + exponential backoff khi HTTP 429.

**Queue & worker**:
- BullMQ (Redis-backed) với queues: `shopee-sync`, `lazada-sync`, `tiki-sync`, `pos-broadcast`.
- Job types: `push-product`, `update-stock`, `update-price`, `pull-orders`, `reconcile`.
- Reconcile job chạy mỗi 6 giờ: pull full inventory từ kênh, so với DB, alert nếu drift > 2 units.

**POS offline**:
- App POS chạy Next.js PWA hoặc Electron, kết nối barcode scanner USB (đọc qua HID, browser nhận `keydown` events).
- In tem: thermal printer (Xprinter, Brother QL) qua driver browser hoặc `printer-thermal-escpos` Node library.
- Offline-first: dùng IndexedDB cache catalog + Service Worker, sync khi online.

### 9. Best Practices từ PIM/ERP hiện có

**Akeneo product model concept (đáng học)** — theo Akeneo Help Center: *"A variant product is a product, and it is also a variant of a product model. It shares the common attributes of a product model but also has its own properties... up to 3 levels of enrichment can be managed for products with variants"*:
- 3 tầng: `ProductModel` (root) → `ProductModel` (sub, level 2) → `Product` (variant). Mỗi `family_variant` định nghĩa axes (vd "size, color"). Áp dụng cho 3D: ProductModel "Dragon Figure" → ProductModel sub "Dragon Figure - PLA" → Variants per color×size.
- `family` định nghĩa attribute set bắt buộc theo category (vd category Figure phải có "characters_universe", "scale_ratio").

**Vietnamese systems (Sapo, KiotViet, Nhanh.vn)** — họ làm gì:
- **Sapo**: mạnh đa kênh (Shopee/Lazada/Tiki/TikTok Shop). Theo Sapo Help Center mục FAQ: *"Gói dịch vụ Omnichannel có chi phí là 799.000đ/tháng, hiện tại chi phí đang được khuyến mãi ưu đãi chỉ còn 599.000đ/tháng"* — tức **giá niêm yết là 799K/tháng**, 599K chỉ là giá khuyến mãi tại thời điểm tra cứu. Biến thể thuộc tính (size, màu), đồng bộ live. Phù hợp shop bán lẻ.
- **KiotViet**: mạnh tại quầy, quy đổi đơn vị tính tốt (tấn↔kg, thùng↔lẻ), nhưng yếu đa kênh online.
- **Nhanh.vn**: chuyên đơn hàng + vận chuyển đa sàn, không mạnh POS.
- → Hệ thống tự build sẽ **tập trung sâu vào pipeline POC → SKU cho 3D printing** mà các tool VN không cover được, đồng thời học khả năng đa kênh từ Sapo.

**Shapeways pricing model** (đáng học cho cost calc) — theo Shapeways support docs:
- Tính phí theo Material Volume + Bounding Box / Machine Space + Support Volume + Manufacturing Speed (Priority/Economy/Rush) + Minimum price per part.
- Verbatim Shapeways: *"Machine Space - The amount of space your product takes inside our 3D printers... Bounding Box Volume - The dimensions of your product used to determine the space it takes inside our 3D printers."*
- Lý do: 1 print spider-structure tốn ít material nhưng chiếm nhiều bed space → block job khác.

### 10. Tech stack đề xuất

| Layer | Lựa chọn chính | Lý do | Alternative |
|---|---|---|---|
| Backend | **NestJS 10 (TypeScript)** | Modular, DI, OpenAPI auto-gen, dev pool VN dồi dào, share types với frontend | Django REST / FastAPI nếu team Python; Go (Fiber/Gin) nếu cần perf cực cao |
| Primary DB | **PostgreSQL 16** với JSONB + ltree + pg_trgm | Variant attributes dynamic qua JSONB; category tree qua ltree; fuzzy search qua trgm | MongoDB nếu thực sự document-heavy (nhưng JSONB Postgres đã đủ) |
| Object storage | **MinIO** self-hosted hoặc **AWS S3 / Cloudflare R2** | STL/GCODE file 5–500MB, không lưu DB | Backblaze B2 (rẻ nhất) |
| Search | **Meilisearch** | Setup 1 ngày, typo-tolerant, instant search, đủ cho catalog <1M SKUs (Meilisearch docs: *"intended to deliver performant instant-search experiences aimed at end-users"*) | Elasticsearch nếu cần analytics phức tạp |
| Cache + Queue | **Redis 7 + BullMQ** | BullMQ TypeScript native, retry, delay, rate-limit built-in | RabbitMQ + Celery (nếu Python) |
| Frontend admin | **Next.js 14 (App Router) + Tailwind + shadcn/ui** | SSR cho SEO public page, ISR cho catalog, share component | Refine / Retool nếu admin-only và muốn rapid |
| 3D viewer | **`<model-viewer>` (Google)** cho GLB; **`react-stl-viewer`** cho STL | Web component standard, AR built-in | Three.js raw nếu cần custom shader |
| Mobile/POS | Next.js PWA, sau này có thể wrap Capacitor | Reuse codebase | Flutter nếu cần native UX |
| Auth | **Keycloak** self-hosted hoặc **Supabase Auth** | RBAC sẵn, OAuth, audit log | Auth0 (đắt) / build tay với JWT + Passport |
| File conversion | Worker Node.js với `assimp`, `gltf-pipeline`, `gltfpack` | STL → GLB cho preview | Blender headless cho complex |
| Barcode/QR | `bwip-js`, `qrcode` npm | Mature | Server-side ZPL nếu in thermal |
| Observability | OpenTelemetry + Grafana + Loki + Prometheus | Open source, đầy đủ trace+log+metrics | Sentry cho error tracking |
| Containerization | Docker + Docker Compose (dev) → k3s/Kubernetes (prod) | Reproducible | Bare metal nếu cost-sensitive |
| CI/CD | GitHub Actions + Docker registry private | Phổ biến VN | GitLab CI |

**Quan trọng — chọn ngôn ngữ**: NestJS (TS) thắng vì (1) cùng ngôn ngữ với Next.js frontend → share type via npm workspace + Zod schema chung, (2) marketplace SDK cộng đồng (shopee-sdk, lazada-open-platform-sdk) phong phú hơn cho Node, (3) tuyển dev VN dễ. Django mạnh hơn về admin auto-gen nhưng kém về real-time/queue ecosystem.

### 11. User stories chi tiết

**Admin / Catalog Manager**:
- US-001: *Là Catalog Manager, tôi muốn tạo 1 sản phẩm mới với 5 biến thể màu × 3 size, mỗi biến thể auto-generate SKU theo convention, để tiết kiệm thời gian nhập liệu.*  
  → UI: form "create product" → tab "Variants" → matrix selector axes (color: red/blue/green/yellow/black × size: S/M/L) → "Generate All" → preview 15 SKU rows với SKU pre-filled, cho phép edit từng dòng.
- US-002: *Là Catalog Manager, tôi muốn upload 1 file STL và preview 3D trên web trước khi gắn vào variant.*  
  → Upload → background worker convert STL→GLB → khi xong WebSocket notify → user thấy `<model-viewer>` xoay được.
- US-003: *Là Catalog Manager, tôi muốn bulk import 200 SKU từ Excel với template chuẩn.*  
  → Template `.xlsx` tải về từ UI; backend dùng `exceljs` + Zod validation, return row-by-row error report.
- US-004: *Là Catalog Manager, tôi muốn xem version history của một file STL và rollback về v1.2 nếu v1.3 in lỗi.*

**Production Manager**:
- US-010: *Là Production Manager, tôi muốn xem định lượng PLA cần thiết để in batch 100 sản phẩm "Dragon Figure size M", với breakdown theo màu.*  
  → Report query: BOM × 100, group by material+color.
- US-011: *Là Production Manager, tôi muốn biết SKU X có thể in trên máy nào, máy nào nhanh nhất.*  
  → Lookup `variant_compatible_printers` ORDER BY estimated_minutes ASC.
- US-012: *Là Production Manager, tôi muốn nhập kết quả POC v3 của SKU X (thời gian in, gram filament thực tế), system tự tính giá vốn và gợi ý giá bán.*

**Channel Operator**:
- US-020: *Là Channel Operator, tôi muốn push variant X lên Shopee + Lazada cùng lúc, hệ thống map SKU + giá + 8 ảnh + mô tả tự động.*  
  → Click "Publish" → modal chọn kênh + override (giá Lazada cao hơn 5%) → background job push → notify khi xong.
- US-021: *Là Channel Operator, tôi muốn khi 1 SKU bán trên Tiki, stock trên Shopee + Lazada giảm tương ứng trong <30s.*  
  → Webhook order Tiki → reduce stock master → fan-out update Shopee + Lazada.
- US-022: *Là Channel Operator, tôi muốn reconcile inventory daily, alert nếu chênh lệch.*

**Product Designer**:
- US-030: *Là Designer, tôi muốn capture ý tưởng vào pipeline với mood board + link tham khảo, gắn nhãn "concept".*
- US-031: *Là Designer, tôi muốn promote idea thành product khi POC pass test.*

**Cashier (POS)**:
- US-040: *Là Cashier, tôi muốn scan barcode để add vào hóa đơn, kể cả khi mất mạng.*
- US-041: *Là Cashier, tôi muốn in tem QR cho sản phẩm vừa hoàn thiện trước khi ship.*

### 12. Tính năng nâng cao

- **Bulk import/export**: CSV/XLSX, async queue, idempotent (re-import không tạo duplicate, dùng `sku_root` làm key).
- **Audit log**: bảng `audit_logs (id, entity_type, entity_id, action, diff_jsonb, user_id, ip, ua, created_at)`. Trigger tự động từ Prisma/TypeORM middleware. Diff format: JSON Patch (RFC 6902).
- **RBAC**: roles `super_admin`, `catalog_manager`, `production_manager`, `channel_operator`, `designer`, `cashier`, `viewer`. Permissions granular: `product:create`, `product:update`, `variant:price_update`, `channel:publish_shopee`, etc. Library: CASL (JS) hoặc tự code matrix.
- **Public API**: REST + GraphQL (Apollo Server hoặc TypeGraphQL). Auth qua API key + scope. Rate limit per key.
- **Webhook outbound**: cho phép admin đăng ký URL nhận event `product.created`, `variant.stock_changed`, `order.synced`. Retry 3 lần với exponential backoff + dead-letter queue.
- **Custom attributes (EAV-lite)**: thay vì EAV truyền thống, dùng JSONB column `attributes` trên `products` và `variants` + bảng meta `attribute_definitions` (id, code, label, type, options, applies_to). UI tự render form theo định nghĩa.
- **i18n**: bảng `translations(entity_type, entity_id, field, locale, value)`. Hoặc lưu trực tiếp `name_vi`, `name_en` trong jsonb.

### 13. Roadmap MVP → Full version

**MVP (Tháng 1–3) — phải có để bán được hàng**:
1. Auth + RBAC cơ bản (admin/staff)
2. CRUD `products`, `variants`, `categories`, `media` 
3. SKU auto-generate + barcode internal (020-prefix)
4. Upload file STL (chưa preview 3D, chỉ download)
5. BOM cơ bản (link material → variant với qty)
6. Material master + Printer master (CRUD)
7. POC cost calculator (form nhập tay, công thức cố định)
8. Search catalog (Meilisearch index, basic facets)
9. Bulk import/export CSV
10. **Connector Shopee** (1 kênh) — push product + sync stock 1 chiều
11. POS offline cơ bản (barcode scan, in tem, không full inventory)

**Phase 2 (Tháng 4–6) — đa kênh & 3D preview**:
1. Connector Lazada + Tiki
2. Order pull từ 3 sàn → unified order view
3. Real-time stock sync 2 chiều với webhook
4. Reconcile job + alert
5. 3D preview qua `<model-viewer>` (STL→GLB pipeline)
6. File versioning + license management
7. Idea pipeline (Kanban board)
8. Audit log full
9. Public API + API key management

**Phase 3 (Tháng 7–9) — scale & nâng cao**:
1. Multi-warehouse stock management
2. Webhook outbound cho integration đối tác
3. Advanced pricing (markup theo segment, promo rules)
4. Workflow approval (vd: variant price update cần approve)
5. Analytics dashboard (best-selling SKU, channel performance, material consumption forecast)
6. Mobile app native (React Native hoặc Flutter) cho production floor
7. AI tag/description generator (GPT-4 cho mô tả SP + ảnh)
8. Connector Shopify / WooCommerce / TikTok Shop / Sendo

**Phase 4 (Năm 2) — chỉ khi cần**:
- Multi-tenant SaaS hóa nếu muốn bán cho shop khác.
- Slicer integration (parse GCODE tự động cho POC).
- IoT printer farm: Klipper/OctoPrint API tích hợp để monitor live print + auto-update hours_used.

### 14. Pitfall thường gặp & cách né

| Pitfall | Hậu quả | Giải pháp |
|---|---|---|
| SKU không match giữa kênh | Overselling, inventory drift | Bảng `channel_listings` cứng, validate khi publish |
| Lưu STL trong RDBMS | DB phình to, slow backup | Object storage (MinIO/S3) từ ngày đầu |
| Hardcode attribute color/material thành column | Mỗi lần thêm thuộc tính phải migration | JSONB `attributes` + `attribute_definitions` |
| Variant explosion 5 trục | 100+ variants/product, 70% không bán | Audit quarterly, retire <10 units/90 ngày; hỏi "có track inventory riêng không" trước khi tạo |
| Sync mỗi 15 phút | Spike traffic → overselling | Real-time webhook + safety stock buffer 5–10% |
| Không versioning file STL | Mất design cũ khi update, không rollback được | parent_file_id self-ref + immutable storage |
| License không track | Bị DMCA / kiện | Bắt buộc `license_type` khi upload, block bán nếu NC |
| EAV truyền thống Magento-style | Query 5-attribute filter cần 5 self-join, chậm | JSONB + GIN index trên path-ops |
| Tiki 2-option-attr limit không xử lý | Push thất bại hoặc mất variant | Strategy merge axes hoặc split product khi sync Tiki |
| Webhook không idempotent | Trừ stock 2 lần | Dùng `idempotency_key` từ marketplace event_id, bảng `processed_events` |
| Không có sandbox test | Bug push lên production sàn → khách thật bị ảnh hưởng | Mỗi connector có mode `sandbox` toggle, test full E2E trước |
| Marketplace API breaking change | Hệ thống chết | Version connector, monitor changelog email, auto-test daily với sandbox |
| Cost calc không track máy đã in | Tính khấu hao sai | Increment `printers.hours_used` mỗi POC completed |
| Không có data backup | Mất hết SKU | PG dump daily + MinIO replicate cross-region |

---

## Recommendations

### Hành động ngay (Tháng 0 — pre-build)
1. **Tuyển/xác nhận team**: 1 tech lead (fullstack TypeScript), 2 backend NestJS, 1 frontend Next.js, 1 designer/PM kiêm QA. Tổng 4–5 người trong 6 tháng đầu.
2. **Đăng ký developer accounts**:
   - Shopee Open Platform (open.shopee.com) — đăng ký Third-party Partner, có thể mất 2–4 tuần duyệt.
   - Lazada Open Platform — đăng ký app, lấy app_key/app_secret.
   - Tiki Developer Platform — xác minh business 1–2 ngày theo Tiki Docs (*"Only verified profile can create and manage apps on TIKI Developer Platform. The verification process might take 1 to 2 working days"*), tạo in-house app.
   → Bắt đầu **ngay tuần này** vì cycle duyệt dài.
3. **Đăng ký GS1 Vietnam (gs1vn.org.vn)** nếu có kế hoạch bán retail offline qua POS scan barcode chuẩn. Theo Sinoautoid (cập nhật 2025), chi phí GS1 VN gồm 2 phần riêng biệt: **~1.000.000 VNĐ nộp 1 lần** để được cấp mã doanh nghiệp (GS1 Company Prefix) cộng **phí duy trì ~500.000 VNĐ/năm** cho gói mã 10 số (dưới 100 sản phẩm); từ 1/1/2026 thủ tục thực hiện qua cổng dịch vụ công tại vnpc.gs1.gov.vn. Nếu chỉ bán online + scan nội bộ, dùng prefix 020–029 free.
4. **Khảo sát hiện trạng**: liệt kê tất cả SKU hiện hữu (Excel/Google Sheet), classify theo 5 trục biến thể, đo distribution → dùng để thiết kế default attribute set.

### Bắt đầu MVP (Tháng 1)
5. **Setup repo monorepo** (`apps/api`, `apps/web`, `apps/pos`, `packages/shared-types`, `packages/connectors`) — dùng Turborepo hoặc Nx.
6. **Database schema first** — viết Prisma schema cho 10 bảng core (products, variants, categories, materials, printers, boms, poc_versions, design_files, media_assets, channel_listings), review với team trước khi code.
7. **Spike Shopee connector** — chọn Shopee làm kênh đầu vì doanh thu thường lớn nhất ở VN; build trong sandbox 2 tuần để hiểu rate limit + edge case trước khi build connector Lazada/Tiki.

### Benchmark để escalate
- **Chuyển sang microservice / event-driven nếu**: hệ thống > 10k SKU active hoặc > 5 kênh hoặc > 1000 orders/day. Trước đó giữ monolith NestJS.
- **Thay Meilisearch bằng Elasticsearch nếu**: cần aggregation phức tạp (sales by material × color × month), > 1M documents.
- **Thay PostgreSQL JSONB bằng pattern hybrid (column + JSONB) nếu**: query filter trên cùng 1 attribute > 1000 lần/ngày — promote attribute đó thành column riêng có index.
- **Build dedicated WMS riêng nếu**: > 3 kho vật lý hoặc > 2 đối tác fulfillment.
- **Mua/license PIM thương mại nếu**: catalog vượt 100k SKU và có ≥ 10 ngôn ngữ — lúc đó Akeneo Growth/Enterprise có thể rẻ hơn dev cost (lưu ý: Akeneo CE v7 end-of-support 30/9/2026 nên CE không phải lựa chọn dài hạn).

### Đo lường thành công
- MVP thành công khi: catalog manager có thể tạo + publish 1 SKU lên Shopee trong < 5 phút.
- Phase 2 thành công khi: overselling rate < 0.5% trong 30 ngày, stock drift giữa các kênh < 1%.
- Phase 3 thành công khi: thời gian từ "idea" đến "selling" giảm < 14 ngày trung bình.

---

## Caveats

1. **API marketplace thay đổi thường xuyên**. Shopee đã ép migrate v1 → v2 OpenAPI; Lazada cũng từng đổi platform (theo Lazada New Seller API Integration doc: *"Lazada is migrating sellers to a new platform... some endpoints have changed, especially for product listing"*). Connector phải tách layer rõ (versioned interface) và monitor email changelog của 3 sàn. Có thể tốn 1–2 sprint/năm cho việc maintain.
2. **Rate limit số chính xác không public** cho Shopee/Lazada/Tiki. Số "10 req/s/shop Shopee" là community-documented (InlinexDev blog), không phải SLA chính thức. Khuyến nghị thiết kế conservative (5 req/s) + observability để adjust.
3. **Tiki 2 option_attributes** là hard limit không vượt được — bắt buộc business logic chấp nhận compromise (split product hoặc merge axes) khi sync Tiki. Lazada cũng có giới hạn nhưng linh hoạt hơn.
4. **License STL từ Thingiverse/Cults3D**: tự động parse license metadata từ file là không khả thi vì thông tin license nằm ở metadata trang web chứ không trong file STL. Workflow phải có thao tác manual nhập license khi import — đào tạo team.
5. **Cost numbers Việt Nam (giá filament, điện EVN) thay đổi theo thời gian** — không hardcode vào logic, lưu trong bảng `settings` hoặc `material_price_history` để audit và recalc khi giá đổi.
6. **POS offline-first đòi hỏi conflict resolution strategy** nếu 2 máy POS bán cùng SKU cuối khi mất mạng. Đề xuất MVP: chấp nhận eventual consistency, có audit reconciliation thủ công. Full version: CRDT-based hoặc last-write-wins per timestamp + manual review.
7. **3D preview GLB không thay thế file STL gốc** — khách hàng tải về để tự in cần STL nguyên bản; GLB chỉ cho preview UI. Hệ thống phải lưu cả hai.
8. **Markup percentage 30–50% là gợi ý, không phải chuẩn ngành**. Pricing strategy nên A/B test theo category — figure cosplay có thể markup 100%+, gadget functional thường 40–60%.
9. **Build vs Buy**: nếu doanh nghiệp < 1000 SKU và < 100 orders/ngày, dùng KiotViet/Sapo + custom file management bên ngoài có thể rẻ và nhanh hơn build full. Quyết định build chỉ hợp lý khi đặc thù 3D printing (POC, BOM định lượng filament, file STL versioning, license) là core competitive advantage.
10. **Tài liệu API Lazada một số trang render JS, không fetch được**. Phải đọc từ readme.io mirror hoặc Postman collection community. Schedule budget 1 tuần đầu cho team chỉ để đọc + test sandbox 3 API.