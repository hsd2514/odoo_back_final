from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, LargeBinary, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Category(Base):
    __tablename__ = "categories"

    category_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.category_id"), nullable=True)


class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(Integer, nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.category_id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    base_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    pricing_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    assets: Mapped[list["ProductAsset"]] = relationship(back_populates="product", cascade="all, delete-orphan")


class ProductAsset(Base):
    __tablename__ = "product_assets"

    asset_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id"), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # Either uri (remote storage) or inline data (bytea) can be used
    uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    drm_protected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Inline storage (optional)
    filename: Mapped[str | None] = mapped_column(String(255))
    content_type: Mapped[str | None] = mapped_column(String(100))
    size: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str | None] = mapped_column(String(64), unique=False, index=True)
    data: Mapped[bytes | None] = mapped_column(LargeBinary)

    product: Mapped[Product] = relationship("Product", back_populates="assets")


