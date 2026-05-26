# Glossary - Thuật ngữ dự án

## 3D Printing

| Term | Định nghĩa |
|---|---|
| **FDM** | Fused Deposition Modeling - in nóng chảy filament (phổ biến, rẻ) |
| **SLA / MSLA / DLP** | Resin printing - in bằng nhựa lỏng UV |
| **SLS** | Selective Laser Sintering - in bột nhựa, công nghiệp |
| **MJF** | Multi Jet Fusion - HP, công nghiệp |
| **PLA** | Polylactic Acid - filament phổ biến, dễ in, không bền nhiệt |
| **PLA+** | PLA biến tính, bền hơn PLA thường |
| **ABS** | Acrylonitrile Butadiene Styrene - bền nhiệt, cần enclosure |
| **PETG** | Polyethylene Terephthalate Glycol - cân bằng giữa PLA và ABS |
| **TPU** | Thermoplastic Polyurethane - mềm, dẻo (làm ốp lưng, đệm) |
| **ASA** | Tương tự ABS nhưng chịu UV tốt hơn (outdoor) |
| **Resin** | Nhựa UV lỏng dùng cho SLA/MSLA |
| **Nozzle** | Đầu phun của máy FDM (0.2mm, 0.4mm chuẩn, 0.6/0.8mm) |
| **Layer height** | Độ dày mỗi lớp in (0.08-0.32mm FDM, 25-100μm SLA) |
| **Infill** | % ruột đặc bên trong sản phẩm (10-100%) |
| **Build plate / Bed** | Mặt phẳng nơi in |
| **Build volume** | Thể tích máy có thể in được (vd 256×256×256mm) |
| **Slicer** | Phần mềm cắt 3D model thành G-code (Cura, PrusaSlicer, Bambu Studio) |
| **G-code** | File chỉ thị di chuyển cho máy in |
| **Support** | Cấu trúc đỡ overhang, gỡ bỏ sau khi in xong |
| **AMS** | Automatic Material System - hệ thống đổi màu tự động (Bambu) |
| **Post-processing** | Xử lý sau in: gỡ support, mài, sơn |
| **Curing** | Hóa cứng UV cho sản phẩm resin |
| **STL** | Format file 3D phổ biến, chỉ chứa geometry (triangles) |
| **OBJ** | Format 3D có color/texture |
| **3MF** | Format hiện đại thay thế STL, hỗ trợ multi-material |
| **STEP** | Format CAD chính xác (engineering) |
| **GLB / glTF** | Format cho web 3D viewer |

## E-commerce / Multi-channel

| Term | Định nghĩa |
|---|---|
| **SKU** | Stock Keeping Unit - mã quản lý kho cho 1 biến thể cụ thể |
| **SPU** | Standard Product Unit (Lazada) - sản phẩm "chuẩn", chứa nhiều product |
| **Variant** | Biến thể của 1 sản phẩm (vd: size M màu đỏ) |
| **Master SKU** | SKU nội bộ, là single source of truth |
| **Channel SKU / Seller SKU** | SKU bạn đặt khi đăng lên 1 kênh cụ thể |
| **Item ID** | ID do sàn cấp cho sản phẩm (Shopee item_id, Tiki product_id) |
| **Tier variation** | Cấu trúc variant trên Shopee (2 levels tối đa) |
| **Option attribute** | Thuộc tính tạo variant trên Tiki (≤ 2) |
| **Overselling** | Bán quá tồn kho, phải cancel order |
| **Safety stock** | Buffer % để chống overselling |
| **Reconcile** | Đối soát stock giữa các kênh và hệ thống |
| **Webhook** | API callback từ sàn báo event (order, stock change) |
| **POS** | Point of Sale - bán hàng tại quầy offline |

## PIM / Software

| Term | Định nghĩa |
|---|---|
| **PIM** | Product Information Management - quản lý thông tin sản phẩm |
| **DAM** | Digital Asset Management - quản lý media |
| **BOM** | Bill of Materials - danh sách nguyên liệu cấu thành 1 SP |
| **EAV** | Entity-Attribute-Value - pattern lưu attributes động (legacy) |
| **JSONB** | JSON Binary - kiểu dữ liệu Postgres để lưu attributes động |
| **Family / Family variant** | Khái niệm Akeneo - định nghĩa attribute set + variant axes |
| **Audit log** | Log mọi thay đổi để truy vết |
| **RBAC** | Role-Based Access Control |
| **Idempotent** | Gọi nhiều lần kết quả như gọi 1 lần (quan trọng cho webhook) |
| **Soft delete** | Đánh dấu deleted_at thay vì xóa thật |

## Marketplace specifics

| Term | Định nghĩa |
|---|---|
| **Shopee Open Platform** | API của Shopee, dùng partner_id + HMAC sign |
| **Lazada Open Platform** | API của Lazada, OAuth + signed request |
| **Tiki Open API** | API của Tiki, OAuth 2.0 chuẩn |
| **Push Mechanism** | Hệ thống webhook của Shopee |
| **Sandbox** | Môi trường test, không ảnh hưởng customer thật |
| **Rate limit** | Giới hạn số request/giây/giờ |
| **Access token** | Token truy cập API, có TTL |
| **Refresh token** | Token để lấy access token mới khi hết hạn |

## License (Creative Commons)

| Term | Cho phép commercial? | Yêu cầu credit? | Cho phép modify? |
|---|---|---|---|
| **CC0** | ✅ | ❌ | ✅ |
| **CC BY** | ✅ | ✅ | ✅ |
| **CC BY-SA** | ✅ | ✅ | ✅ (ShareAlike) |
| **CC BY-ND** | ✅ | ✅ | ❌ |
| **CC BY-NC** | ❌ | ✅ | ✅ |
| **CC BY-NC-SA** | ❌ | ✅ | ✅ (ShareAlike) |
| **CC BY-NC-ND** | ❌ | ✅ | ❌ |
| **All Rights Reserved** | Theo hợp đồng | Theo hợp đồng | Theo hợp đồng |
