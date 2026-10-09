from datetime import datetime
from decimal import Decimal
from sqlalchemy import (Boolean, CheckConstraint, DateTime, ForeignKeyConstraint, Index, Integer, Numeric, String, Text, UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base

class OrdenCompraDetalle(Base):
    __tablename__ = "orden_compra_detalles"
    __table_args__ = (
        ForeignKeyConstraint(["orden_id", "empresa_id"], ["ordenes_compra.id", "ordenes_compra.empresa_id"], name="fk_orden_compra_detalle_orden_empresa"),
        ForeignKeyConstraint(["producto_id", "empresa_id"], ["productos.id", "productos.empresa_id"], name="fk_orden_compra_detalle_producto_empresa"),
        UniqueConstraint("id", "orden_id", "empresa_id", name="uq_orden_detalle_id_orden_empresa"),
        UniqueConstraint("orden_id", "producto_id", name="uq_orden_detalle_producto"),
        CheckConstraint("cantidad_solicitada > 0", name="ck_orden_detalle_cantidad"),
        CheckConstraint("precio_unitario >= 0 AND impuesto >= 0 AND subtotal >= 0 AND total >= 0", name="ck_orden_detalle_importes"),
        Index("ix_orden_detalle_empresa_producto", "empresa_id", "producto_id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(Integer, nullable=False)
    orden_id: Mapped[int] = mapped_column(Integer, nullable=False)
    producto_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cantidad_solicitada: Mapped[Decimal] = mapped_column(Numeric(14,3), nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False)
    impuesto: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False, server_default="0")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False)
    controla_stock_snapshot: Mapped[bool] = mapped_column(Boolean, nullable=False)
