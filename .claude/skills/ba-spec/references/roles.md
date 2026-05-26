# Roles & Permissions Matrix

## 6 Roles chính

### 1. Super Admin
- Toàn quyền hệ thống
- Quản lý users, roles, settings
- Xem audit log đầy đủ
- Configure marketplace credentials, API keys

### 2. Catalog Manager
- CRUD products, categories, attributes, media
- CRUD variants, generate SKU
- Upload design files, manage versions, set license
- KHÔNG được xem cost price (trừ khi có permission đặc biệt)
- KHÔNG được publish lên marketplace (cần Channel Operator)

### 3. Production Manager
- Xem catalog (read-only) + xem cost price đầy đủ
- CRUD POC versions, nhập kết quả in thực tế
- CRUD materials, printers
- CRUD BOM
- Xem báo cáo vật liệu tiêu hao
- KHÔNG được sửa giá bán

### 4. Channel Operator
- Xem catalog (read-only)
- Publish/unpublish variant lên Shopee/Lazada/Tiki
- Sửa giá theo kênh (price_override)
- Sửa stock buffer theo kênh
- Xem order từ các kênh
- Reconcile inventory

### 5. Designer
- CRUD product_ideas (pipeline)
- Upload design files (versioning)
- Promote idea → product (cần approve từ Catalog Manager)
- Xem catalog (read-only)

### 6. Cashier (POS)
- Truy cập POS app
- Scan barcode, tạo order, in tem
- Xem stock (read-only)
- KHÔNG được sửa giá hay tạo SP mới

## Permissions matrix (chi tiết)

| Permission | SuperAdmin | Catalog | Production | Channel | Designer | Cashier |
|---|---|---|---|---|---|---|
| `product:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `product:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `product:update` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `product:delete` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `variant:price_read` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| `variant:price_update` | ✅ | ✅ | ❌ | ❌* | ❌ | ❌ |
| `variant:cost_read` | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| `design_file:upload` | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| `design_file:set_license` | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| `poc:create` | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| `material:manage` | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| `printer:manage` | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| `channel:publish` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| `channel:credentials` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `channel:price_override` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| `order:read` | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ |
| `order:create_pos` | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `audit_log:read` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `user:manage` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `idea:create` | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| `idea:promote` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |

*Channel Operator có thể override price theo kênh nhưng không sửa base price.

## Persona profiles (cho UX/spec)

### Persona: Anh Hùng - Catalog Manager
- 28 tuổi, từng làm e-commerce ở Tiki
- Tech-savvy, dùng Excel mạnh
- Pain: tạo 50 variants mỗi tuần, hiện đang dùng Sheet + copy paste lên Shopee
- Goal: giảm thời gian từ idea → live trên kênh xuống < 30 phút/SKU

### Persona: Chị Lan - Production Manager
- 35 tuổi, kỹ sư cơ khí
- Quản lý xưởng 10 máy in 3D (Bambu X1C, Prusa MK4, Elegoo Saturn)
- Pain: track filament tồn kho bằng giấy, hay quên định lượng
- Goal: biết chính xác cần mua bao nhiêu kg PLA Red cho batch order tuần này

### Persona: Em Minh - Channel Operator
- 24 tuổi, fresher
- Trách nhiệm sync sản phẩm lên Shopee/Lazada/Tiki hằng ngày
- Pain: bị overselling 2-3 lần/tháng, Shopee xuống rating
- Goal: stock các kênh luôn đồng bộ, không bao giờ phải cancel order

### Persona: Anh Tuấn - Designer
- 30 tuổi, 3D artist tự do
- Dùng Blender, ZBrush, Fusion 360
- Pain: không có nơi lưu version sketch + reference + POC notes ở 1 chỗ
- Goal: pipeline rõ ràng từ idea → ship, biết design nào đang bán chạy

### Persona: Chị Hoa - Cashier
- 40 tuổi, chủ shop offline phố cổ
- Không tech-savvy
- Pain: khách đông phải tính tay, hay nhầm SKU
- Goal: scan barcode → bill ra trong 5 giây, in tem dán hộp
