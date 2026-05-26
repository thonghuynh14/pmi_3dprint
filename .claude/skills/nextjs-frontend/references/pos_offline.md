# POS Offline Pattern

POS app phải hoạt động được khi mất mạng (offline-first), sync khi online lại.

## Stack

- **IndexedDB** qua `idb` library (typed wrapper)
- **Service Worker** cache app shell
- **Background Sync API** để sync pending orders khi online
- **Web Bluetooth/USB API** cho barcode scanner + thermal printer

## Schema IndexedDB

```ts
// lib/db/pos-db.ts
import { openDB, type DBSchema } from 'idb';

interface PosDB extends DBSchema {
  catalog: {
    key: string; // sku
    value: {
      sku: string;
      product_name: string;
      variant_label: string;
      base_price: number;
      stock_available: number;
      barcode?: string;
      image_thumb?: string;
      last_synced_at: number;
    };
    indexes: {
      'by-barcode': string;
    };
  };
  pending_orders: {
    key: string; // local uuid
    value: {
      id: string;
      items: Array<{ sku: string; quantity: number; price: number }>;
      total: number;
      payment_method: 'cash' | 'card' | 'transfer';
      created_at: number;
      status: 'pending' | 'syncing' | 'synced' | 'failed';
      sync_error?: string;
    };
    indexes: {
      'by-status': string;
    };
  };
  settings: {
    key: string;
    value: any;
  };
}

export async function getPosDB() {
  return openDB<PosDB>('pos-db', 1, {
    upgrade(db) {
      const catalogStore = db.createObjectStore('catalog', { keyPath: 'sku' });
      catalogStore.createIndex('by-barcode', 'barcode');
      
      const ordersStore = db.createObjectStore('pending_orders', { keyPath: 'id' });
      ordersStore.createIndex('by-status', 'status');
      
      db.createObjectStore('settings');
    },
  });
}
```

## Sync logic

```ts
// lib/pos/sync.ts
import { getPosDB } from '@/lib/db/pos-db';
import { apiClient } from '@/lib/api/client';
import { v4 as uuid } from 'uuid';

export async function syncCatalogFromServer() {
  const db = await getPosDB();
  const lastSyncedAt = (await db.get('settings', 'last_catalog_sync')) ?? 0;
  
  const { data } = await apiClient.get('/v1/pos/catalog/', {
    params: { modified_since: new Date(lastSyncedAt).toISOString() },
  });
  
  const tx = db.transaction('catalog', 'readwrite');
  for (const item of data.results) {
    await tx.store.put({ ...item, last_synced_at: Date.now() });
  }
  await tx.done;
  
  await db.put('settings', Date.now(), 'last_catalog_sync');
}

export async function createOrderOffline(items: Array<{ sku: string; quantity: number; price: number }>) {
  const db = await getPosDB();
  const order = {
    id: uuid(),
    items,
    total: items.reduce((s, i) => s + i.price * i.quantity, 0),
    payment_method: 'cash' as const,
    created_at: Date.now(),
    status: 'pending' as const,
  };
  await db.add('pending_orders', order);
  
  // Trigger sync if online
  if (navigator.onLine) {
    void syncPendingOrders();
  } else {
    // Background sync khi online lại
    if ('serviceWorker' in navigator && 'SyncManager' in window) {
      const reg = await navigator.serviceWorker.ready;
      // @ts-expect-error - Background Sync API
      await reg.sync.register('sync-pending-orders');
    }
  }
  
  return order;
}

export async function syncPendingOrders() {
  const db = await getPosDB();
  const pendings = await db.getAllFromIndex('pending_orders', 'by-status', 'pending');
  
  for (const order of pendings) {
    // Mark syncing
    await db.put('pending_orders', { ...order, status: 'syncing' });
    
    try {
      await apiClient.post('/v1/pos/orders/', order, {
        headers: { 'Idempotency-Key': order.id },
      });
      await db.put('pending_orders', { ...order, status: 'synced' });
    } catch (e: any) {
      await db.put('pending_orders', {
        ...order,
        status: 'failed',
        sync_error: e.message ?? 'Unknown',
      });
    }
  }
}

// Listen for online event
if (typeof window !== 'undefined') {
  window.addEventListener('online', () => {
    void syncPendingOrders();
  });
}
```

## Barcode scanner integration

USB HID scanners gửi data như keyboard → listen `keypress` events:

```ts
// lib/pos/barcode-scanner.ts
let buffer = '';
let lastKeyTime = Date.now();

export function startBarcodeListener(onScan: (code: string) => void) {
  const handler = (e: KeyboardEvent) => {
    const now = Date.now();
    if (now - lastKeyTime > 100) buffer = '';
    lastKeyTime = now;
    
    if (e.key === 'Enter') {
      if (buffer.length > 0) {
        onScan(buffer);
        buffer = '';
      }
    } else if (e.key.length === 1) {
      buffer += e.key;
    }
  };
  
  window.addEventListener('keydown', handler);
  return () => window.removeEventListener('keydown', handler);
}
```

## Thermal printer (ESC/POS via Web USB)

```ts
// lib/pos/printer.ts
export async function printReceipt(order: Order) {
  // Request USB device (cần user permission lần đầu)
  const device = await navigator.usb.requestDevice({
    filters: [{ vendorId: 0x04b8 /* Epson */ }],
  });
  
  await device.open();
  await device.selectConfiguration(1);
  await device.claimInterface(0);
  
  const encoder = new TextEncoder();
  const ESC = '\x1B';
  const commands = [
    `${ESC}@`,           // Init
    `${ESC}a1`,          // Center align
    'CỬA HÀNG IN 3D\n',
    `${ESC}a0`,          // Left align
    `Order: ${order.id}\n`,
    '------------------------\n',
    ...order.items.map(i => `${i.sku}  x${i.quantity}  ${i.price}\n`),
    '------------------------\n',
    `TOTAL: ${order.total} VND\n`,
    '\n\n\n',
    `${ESC}m`,           // Partial cut
  ];
  
  for (const cmd of commands) {
    await device.transferOut(1, encoder.encode(cmd));
  }
}
```
