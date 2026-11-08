import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, Numeric, String, Text, Uuid
from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(255), index=True, nullable=False)
    brand = Column(String(100), index=True, nullable=False)
    category = Column(String(100), index=True, nullable=False)
    variant = Column(String(100), nullable=True)
    unit_of_measurement = Column(String(50), nullable=False)  # "kg", "pack", "litre", "bottle"
    price_aed = Column(Numeric(10, 2), nullable=False)
    stock_quantity = Column(Float, default=0.0, nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)
    image_url = Column(String(500), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
