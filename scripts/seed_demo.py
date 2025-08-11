from __future__ import annotations

import random
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import Role, User, UserRole
from app.models.catalog import Category, Product, ProductAsset
from app.models.inventory import InventoryItem
from app.models.promotions import Promotion
from app.models.loyalty import LoyaltyAccount
from app.models.rentals import RentalOrder, RentalItem, Schedule
from app.models.billing import Invoice, Payment
from app.services.user_service import create_user, get_user_by_email


PRICING_UNITS = ["hour", "day", "week", "month"]


def compute_duration_units(start_ts: datetime, end_ts: datetime, unit: str) -> int:
    total_hours = (end_ts - start_ts).total_seconds() / 3600
    if unit == "hour":
        return int((total_hours + 0.999))
    if unit == "day":
        return int(((total_hours / 24) + 0.999))
    if unit == "week":
        return int(((total_hours / (24 * 7)) + 0.999))
    if unit == "month":
        return int((((total_hours / 24) / 30) + 0.999))
    return int((total_hours + 0.999))


def seed_roles_and_users(db: Session):
    role_by_name: dict[str, Role] = {r.name: r for r in db.query(Role).all()}
    for name in ["Admin", "Seller", "Customer"]:
        if name not in role_by_name:
            r = Role(name=name)
            db.add(r)
            db.flush()
            role_by_name[name] = r
    db.commit()

    def ensure_user(email: str, password: str, full_name: str) -> User:
        u = get_user_by_email(db, email=email)
        if not u:
            u = create_user(db, email=email, password=password, full_name=full_name)
        return u

    admin = ensure_user("admin@example.com", "admin123", "Admin User")
    sellers = [
        ensure_user("seller1@example.com", "seller123", "Seller One"),
        ensure_user("seller2@example.com", "seller123", "Seller Two"),
    ]
    customers = [
        ensure_user(f"cust{i}@example.com", "pass123", f"Customer {i}") for i in range(1, 6)
    ]

    def ensure_role(user: User, role: Role):
        if not db.query(UserRole).filter(UserRole.user_id == user.user_id, UserRole.role_id == role.role_id).first():
            db.add(UserRole(user_id=user.user_id, role_id=role.role_id))

    for u in [admin]:
        ensure_role(u, role_by_name["Admin"])
    for u in sellers:
        ensure_role(u, role_by_name["Seller"])
    for u in customers:
        ensure_role(u, role_by_name["Customer"])
    db.commit()

    return admin, sellers, customers


def seed_catalog_and_inventory(db: Session, sellers: list[User]):
    categories = [
        ("Sofas", None),
        ("Chairs", None),
        ("Tables", None),
        ("Beds", None),
    ]
    existing = {c.name: c for c in db.query(Category).all()}
    cats: list[Category] = []
    for name, parent in categories:
        if name in existing:
            cats.append(existing[name])
        else:
            c = Category(name=name, parent_id=None)
            db.add(c)
            db.flush()
            cats.append(c)
    db.commit()

    products: list[Product] = []
    for c in cats:
        for i in range(1, 4):
            title = f"{c.name[:-1]} {i}"
            p = (
                db.query(Product)
                .filter(Product.title == title, Product.category_id == c.category_id)
                .first()
            )
            if not p:
                p = Product(
                    seller_id=random.choice(sellers).user_id,
                    category_id=c.category_id,
                    title=title,
                    base_price=random.choice([50, 80, 100, 150, 200]),
                    pricing_unit=random.choice(PRICING_UNITS),
                    active=True,
                )
                db.add(p)
                db.flush()
                db.add(
                    ProductAsset(
                        product_id=p.product_id,
                        asset_type="image",
                        uri=f"https://picsum.photos/seed/{p.title.replace(' ', '_')}/600/400",
                        drm_protected=False,
                    )
                )
            products.append(p)
    db.commit()

    for p in products:
        # create a few inventory items per product
        for j in range(2):
            if not db.query(InventoryItem).filter(InventoryItem.product_id == p.product_id, InventoryItem.sku == f"SKU-{p.product_id}-{j}").first():
                db.add(
                    InventoryItem(
                        product_id=p.product_id,
                        sku=f"SKU-{p.product_id}-{j}",
                        serial=f"SN-{p.product_id}-{j}",
                        qty=1,
                        status="available",
                    )
                )
    db.commit()

    return products


def seed_promotions_loyalty(db: Session, customers: list[User]):
    if not db.query(Promotion).filter(Promotion.code == "WELCOME10").first():
        db.add(Promotion(code="WELCOME10", discount_type="percentage", value=10, valid_from=datetime.utcnow().date(), valid_to=(datetime.utcnow() + timedelta(days=90)).date()))
    for u in customers:
        if not db.query(LoyaltyAccount).filter(LoyaltyAccount.user_id == u.user_id).first():
            db.add(LoyaltyAccount(user_id=u.user_id, points_balance=random.randint(0, 200)))
    db.commit()


def seed_rentals_and_billing(db: Session, customers: list[User], sellers: list[User], products: list[Product]):
    now = datetime.utcnow()
    for idx, cust in enumerate(customers, start=1):
        start = now + timedelta(days=idx)
        end = start + timedelta(days=random.choice([1, 2, 3, 7]))
        order = RentalOrder(customer_id=cust.user_id, seller_id=random.choice(sellers).user_id, status="booked", total_amount=0, start_ts=start, end_ts=end)
        db.add(order)
        db.flush()
        # add 1-2 items
        for _ in range(random.choice([1, 2])):
            product = random.choice(products)
            unit_price = float(product.base_price)
            duration = compute_duration_units(start, end, product.pricing_unit)
            item = RentalItem(rental_id=order.rental_id, product_id=product.product_id, inventory_item_id=None, qty=random.choice([1, 2]), unit_price=unit_price, rental_period=f"{start.isoformat()},{end.isoformat()}")
            db.add(item)
            order.total_amount = float(order.total_amount) + (item.qty * unit_price * duration)
        # schedule pickup
        db.add(Schedule(rental_id=order.rental_id, type="pickup", scheduled_for=start))
        # half of orders paid
        db.flush()
        if idx % 2 == 0:
            inv = Invoice(rental_id=order.rental_id, amount_due=order.total_amount, amount_paid=order.total_amount, status="paid")
            db.add(inv)
            db.flush()
            db.add(Payment(rental_id=order.rental_id, invoice_id=inv.invoice_id, amount=order.total_amount, gateway="mock"))
            order.status = "completed"
        db.commit()


def seed_demo() -> None:
    db: Session = SessionLocal()
    try:
        admin, sellers, customers = seed_roles_and_users(db)
        products = seed_catalog_and_inventory(db, sellers)
        seed_promotions_loyalty(db, customers)
        seed_rentals_and_billing(db, customers, sellers, products)
        print("Seeded demo data: roles/users, catalog, inventory, promotions/loyalty, rentals/invoices/payments")
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo()


