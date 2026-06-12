"""Seed dev DB: 20 permissions + 6 roles + 6 user (1 per role) + sample catalog.

Idempotent — chạy lại safe, dùng get_or_create + idempotent service calls
được wrap try/except cho catalog (đụng sku_root unique).

Usage:
    python manage.py seed_initial_data
    python manage.py seed_initial_data --skip-catalog   # chỉ seed RBAC

Output:
    smoke / smokepass           → super_admin
    catalog_manager_test / testpass
    production_manager_test / testpass
    channel_operator_test / testpass
    designer_test / testpass
    cashier_test / testpass
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.constants import (
    PERMISSIONS,
    ROLE_DEFINITIONS,
    ROLE_PERMISSIONS,
)
from apps.accounts.models import Permission, Role, User


class Command(BaseCommand):
    help = "Seed roles, permissions, smoke user + sample catalog (dev only)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-catalog",
            action="store_true",
            help="Chỉ seed RBAC, không tạo product/variant sample.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding RBAC..."))
        perms_map = self._seed_permissions()
        roles_map = self._seed_roles(perms_map)
        self._seed_users(roles_map)

        if not options["skip_catalog"]:
            self.stdout.write(self.style.MIGRATE_HEADING("Seeding sample catalog..."))
            self._seed_catalog(actor=User.objects.get(username="smoke"))

        self.stdout.write(self.style.SUCCESS("[OK] Done."))

    # ------------------------------------------------------------------ steps

    def _seed_permissions(self) -> dict[str, Permission]:
        """Tạo / update 20 permissions. Idempotent qua code unique."""
        out: dict[str, Permission] = {}
        for code, description in PERMISSIONS.items():
            perm, created = Permission.objects.get_or_create(
                code=code, defaults={"description": description}
            )
            if not created and perm.description != description:
                perm.description = description
                perm.save(update_fields=["description"])
            out[code] = perm
        self.stdout.write(f"  -Permissions: {len(out)} (total in DB: {Permission.objects.count()})")
        return out

    def _seed_roles(
        self, perms_map: dict[str, Permission]
    ) -> dict[str, Role]:
        out: dict[str, Role] = {}
        for code, meta in ROLE_DEFINITIONS.items():
            role, _ = Role.objects.get_or_create(
                code=code,
                defaults={"name": meta["name"], "description": meta["description"]},
            )
            # Refresh name/description nếu đổi
            updates = []
            if role.name != meta["name"]:
                role.name = meta["name"]
                updates.append("name")
            if role.description != meta["description"]:
                role.description = meta["description"]
                updates.append("description")
            if updates:
                role.save(update_fields=updates)

            wanted = {perms_map[c] for c in ROLE_PERMISSIONS[code]}
            role.permissions.set(wanted)
            out[code] = role
            self.stdout.write(
                f"  -Role {code}: {len(ROLE_PERMISSIONS[code])} permissions"
            )
        return out

    def _seed_users(self, roles_map: dict[str, Role]) -> None:
        """Tạo smoke + 5 test user (1 per non-super role)."""
        # smoke = super_admin
        smoke, created = User.objects.get_or_create(
            username="smoke",
            defaults={
                "email": "smoke@dev.local",
                "full_name": "Smoke Tester",
                "is_staff": True,
                "is_superuser": True,
                "role": roles_map["super_admin"],
            },
        )
        if created:
            smoke.set_password("smokepass")
            smoke.save()
            self.stdout.write("  -Created superuser smoke / smokepass")
        else:
            # Đảm bảo role gắn đúng (idempotent)
            if smoke.role_id != roles_map["super_admin"].id:
                smoke.role = roles_map["super_admin"]
                smoke.save(update_fields=["role"])

        # 5 test user
        for role_code in [
            "catalog_manager",
            "production_manager",
            "channel_operator",
            "designer",
            "cashier",
        ]:
            username = f"{role_code}_test"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@dev.local",
                    "full_name": f"Test {role_code.replace('_', ' ').title()}",
                    "is_active": True,
                    "role": roles_map[role_code],
                },
            )
            if created:
                user.set_password("testpass")
                user.save()
                self.stdout.write(f"  -Created {username} / testpass")
            else:
                if user.role_id != roles_map[role_code].id:
                    user.role = roles_map[role_code]
                    user.save(update_fields=["role"])

    def _seed_catalog(self, *, actor: User) -> None:
        """Tạo 3 product + 6 variant (matrix 2 material × 3 color × 1 size).

        Idempotent: skip nếu sku_root đã tồn tại (DuplicateSkuRootError
        bắt riêng).
        """
        from apps.catalog.exceptions import DuplicateSkuRootError, DuplicateSlugError
        from apps.catalog.services.products import product_create
        from apps.skus.services.variants import variant_bulk_create_matrix

        sample_products = [
            {
                "name": "Dragon Figurine",
                "sku_root": "DRAGON",
                "short_description": "Tượng rồng decorate 3D printed",
                "tags": ["figure", "fantasy"],
            },
            {
                "name": "Phone Stand",
                "sku_root": "PHSTND",
                "short_description": "Đế đỡ điện thoại đa năng",
                "tags": ["accessory", "office"],
            },
            {
                "name": "Cable Organizer",
                "sku_root": "CABORG",
                "short_description": "Khay tổ chức dây cáp",
                "tags": ["accessory", "office"],
            },
        ]

        materials = [
            {"name": "PLA", "code3": "PLA"},
            {"name": "PETG", "code3": "PET"},
        ]
        colors = [
            {"name": "Red", "code3": "RED"},
            {"name": "Black", "code3": "BLK"},
            {"name": "White", "code3": "WHT"},
        ]
        sizes = ["M"]

        for data in sample_products:
            try:
                product = product_create(actor=actor, **data)
            except (DuplicateSkuRootError, DuplicateSlugError):
                from apps.catalog.models import Product
                product = Product.objects.get(sku_root=data["sku_root"].upper())
                self.stdout.write(
                    f"  -Product {product.sku_root} already exists, skip create"
                )
                continue

            try:
                variants = variant_bulk_create_matrix(
                    actor=actor,
                    product_id=product.id,
                    materials=materials,
                    colors=colors,
                    sizes=sizes,
                    base_price=Decimal("150000"),
                    cost_price=Decimal("40000"),
                )
                self.stdout.write(
                    f"  -Product {product.sku_root}: {len(variants)} variants"
                )
            except Exception as e:  # noqa: BLE001  — seed best-effort, surface error
                self.stdout.write(
                    self.style.WARNING(
                        f"  [WARN]Variant matrix cho {product.sku_root} fail: {e}"
                    )
                )
