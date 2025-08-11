from __future__ import annotations

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services.user_service import create_user, get_user_by_email
from app.models.user import Role, UserRole
from app.models.catalog import Category, Product
from app.models.inventory import InventoryItem


def seed() -> None:
    db: Session = SessionLocal()
    try:
        # Roles
        role_names = {r.name for r in db.query(Role).all()}
        for name in ["Admin", "Seller", "Customer"]:
            if name not in role_names:
                db.add(Role(name=name))
        db.commit()

        # Admin user
        admin = get_user_by_email(db, email="admin@example.com")
        if not admin:
            admin = create_user(db, email="admin@example.com", password="admin123", full_name="Admin User")
            print("Created default admin user: admin@example.com / admin123")
        # Assign Admin role
        admin_role = db.query(Role).filter(Role.name == "Admin").first()
        if admin_role and not db.query(UserRole).filter(UserRole.user_id == admin.user_id, UserRole.role_id == admin_role.role_id).first():
            db.add(UserRole(user_id=admin.user_id, role_id=admin_role.role_id))
            db.commit()

        # Sample category/product/inventory
        cat = db.query(Category).filter(Category.name == "Default").first()
        if not cat:
            cat = Category(name="Default")
            db.add(cat)
            db.commit(); db.refresh(cat)
        prod = db.query(Product).filter(Product.title == "Sample item").first()
        if not prod:
            prod = Product(seller_id=admin.user_id, category_id=cat.category_id, title="Sample item", base_price=100, pricing_unit="day", active=True)
            db.add(prod); db.commit(); db.refresh(prod)
        inv = db.query(InventoryItem).filter(InventoryItem.product_id == prod.product_id).first()
        if not inv:
            inv = InventoryItem(product_id=prod.product_id, sku="SKU-001", serial="SN-001", qty=5, status="available")
            db.add(inv); db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()


