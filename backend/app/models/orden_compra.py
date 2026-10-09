from datetime import datetime
from decimal import Decimal
from sqlalchemy import (Boolean, CheckConstraint, DateTime, ForeignKeyConstraint, Index, Integer, Numeric, String, Text, UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base

class OrdenCompra(Base):
    __tablename__ = "ordenes_compra"
    __table_args__ = (
        ForeignKeyConstraint(["empresa_id"], ["empresas.id"], name="fk_orden_compra_empresa"),
        ForeignKeyConstraint(["proveedor_id", "empresa_id"], ["proveedores.id", "proveedores.empresa_id"], name="fk_orden_compra_proveedor_empresa"),
        ForeignKeyConstraint(["usuario_id", "empresa_id"], ["usuarios.id", "usuarios.empresa_id"], name="fk_orden_compra_usuario_empresa"),
        UniqueConstraint("empresa_id", "codigo", name="uq_orden_compra_empresa_codigo"),
        UniqueConstraint("id", "empresa_id", name="uq_orden_compra_id_empresa"),
        CheckConstraint("estado IN ('BORRADOR','CONFIRMADA','PARCIALMENTE_RECIBIDA','RECIBIDA','CANCELADA')", name="ck_orden_compra_estado"),
        CheckConstraint("estado_pago IN ('PENDIENTE','PARCIAL','PAGADO')", name="ck_orden_compra_estado_pago"),
        CheckConstraint("subtotal >= 0 AND impuesto_total >= 0 AND total >= 0", name="ck_orden_compra_importes"),
        Index("ix_ordenes_compra_empresa_estado_fecha", "empresa_id", "estado", "created_at"),
        Index("ix_ordenes_compra_empresa_proveedor", "empresa_id", "proveedor_id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(Integer, nullable=False)
    proveedor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    usuario_id: Mapped[int] = mapped_column(Integer, nullable=False)
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, server_default="BORRADOR")
    estado_pago: Mapped[str] = mapped_column(String(20), nullable=False, server_default="PENDIENTE")
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, server_default="PEN")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False, server_default="0")
    impuesto_total: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False, server_default="0")
    total: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
