from __future__ import annotations

from app.database import SessionLocal
from app.models.catalog import Product, ProductAsset


def main() -> None:
    s = SessionLocal()
    created = 0
    try:
        products = s.query(Product).all()
        for p in products:
            exists = (
                s.query(ProductAsset)
                .filter(ProductAsset.product_id == p.product_id)
                .first()
            )
            if exists:
                continue
            asset = ProductAsset(
                product_id=p.product_id,
                asset_type="image",
                uri=f"https://picsum.photos/seed/{p.product_id}/600/400",
                drm_protected=False,
            )
            s.add(asset)
            created += 1
        s.commit()
        print(f"Added {created} placeholder images.")
    finally:
        s.close()


if __name__ == "__main__":
    main()


