from __future__ import annotations

import random

from app.database import SessionLocal
from app.models.catalog import Product, ProductAsset


def add_random_assets(per_product_min: int = 2, per_product_max: int = 4) -> None:
    session = SessionLocal()
    added = 0
    try:
        products = session.query(Product).all()
        for p in products:
            # Count existing assets
            existing = (
                session.query(ProductAsset)
                .filter(ProductAsset.product_id == p.product_id)
                .all()
            )
            target = random.randint(per_product_min, per_product_max)
            need = max(0, target - len(existing))
            for _ in range(need):
                seed = f"{p.product_id}-{random.randint(1000, 999999)}"
                asset = ProductAsset(
                    product_id=p.product_id,
                    asset_type="image",
                    uri=f"https://picsum.photos/seed/{seed}/600/400",
                    drm_protected=False,
                )
                session.add(asset)
                added += 1
        session.commit()
        print(f"Added {added} random image assets across {len(products)} products.")
    finally:
        session.close()


if __name__ == "__main__":
    add_random_assets()


