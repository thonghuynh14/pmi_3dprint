"""Hằng số cho RBAC: permission code + role definitions.

Single source of truth dùng cho:
- `seed_initial_data` management command
- Tests (factory tạo role theo code)
- Documentation (personas.md)

Khi thêm permission mới: thêm vào `PERMISSIONS` + gán vào role tương ứng
trong `ROLE_PERMISSIONS`, sau đó chạy lại seed (idempotent).
"""

# ---------------------------------------------------------------------------
# Permission codes (20)
# ---------------------------------------------------------------------------
# Format: "<domain>:<action>"

PERMISSIONS: dict[str, str] = {
    # Product
    "product:create": "Tạo product mới",
    "product:read": "Xem danh sách + chi tiết product",
    "product:update": "Sửa product (kể cả restore)",
    "product:delete": "Soft-delete product",
    # Variant (giá bán + cost tách quyền)
    "variant:create": "Tạo variant mới (single + matrix)",
    "variant:read": "Xem variant + danh sách",
    "variant:update": "Sửa variant (kể cả restore)",
    "variant:delete": "Soft-delete variant",
    "variant:price_update": "Sửa base_price (tách khỏi update tổng quát)",
    "variant:cost_read": "Xem cost_price (chỉ Production Manager + Super Admin)",
    # Design files
    "design_file:upload": "Upload STL/GLB",
    "design_file:set_license": "Set license type cho file",
    # POC
    "poc:create": "Tạo POC version + nhập kết quả in",
    # Materials / printers
    "material:manage": "CRUD materials",
    "printer:manage": "CRUD printers",
    # Channels
    "channel:publish": "Push variant lên Shopee/Lazada/Tiki",
    "channel:credentials": "Quản lý marketplace credentials",
    "channel:price_override": "Override price theo từng kênh",
    # Orders
    "order:read": "Xem orders (mọi kênh)",
    "order:create_pos": "Tạo order POS offline",
    # Audit / System
    "audit_log:read": "Xem audit log",
    "user:manage": "Quản lý user + role",
    # Ideas
    "idea:create": "Tạo product idea (pipeline)",
    "idea:promote": "Promote idea → product",
}


# ---------------------------------------------------------------------------
# Role definitions (6) + mapping → permissions
# ---------------------------------------------------------------------------

ROLE_DEFINITIONS: dict[str, dict[str, str]] = {
    "super_admin": {
        "name": "Super Admin",
        "description": "Toàn quyền hệ thống, manage users + audit log + credentials.",
    },
    "catalog_manager": {
        "name": "Catalog Manager",
        "description": "CRUD product/variant/design file, promote idea. KHÔNG publish channel + KHÔNG xem cost.",
    },
    "production_manager": {
        "name": "Production Manager",
        "description": "CRUD POC/material/printer. Xem cost, không sửa giá bán.",
    },
    "channel_operator": {
        "name": "Channel Operator",
        "description": "Publish lên marketplace, override price per channel, xem order.",
    },
    "designer": {
        "name": "Designer",
        "description": "Upload design file, tạo idea (pipeline).",
    },
    "cashier": {
        "name": "Cashier",
        "description": "POS offline: tạo order, xem order/stock.",
    },
}


# Map role_code → list permission code
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "super_admin": list(PERMISSIONS.keys()),  # full quyền
    "catalog_manager": [
        "product:create", "product:read", "product:update", "product:delete",
        "variant:create", "variant:read", "variant:update", "variant:delete",
        "variant:price_update",
        "design_file:upload", "design_file:set_license",
        "idea:promote",
    ],
    "production_manager": [
        "product:read",
        "variant:read", "variant:cost_read",
        "poc:create",
        "material:manage", "printer:manage",
        "order:read",
    ],
    "channel_operator": [
        "product:read",
        "variant:read",
        "channel:publish", "channel:price_override",
        "order:read",
    ],
    "designer": [
        "product:read",
        "variant:read",
        "design_file:upload",
        "idea:create",
    ],
    "cashier": [
        "product:read",
        "variant:read",
        "order:read", "order:create_pos",
    ],
}
