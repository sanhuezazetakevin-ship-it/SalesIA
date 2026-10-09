from datetime import datetime
from decimal import Decimal
from sqlalchemy import (Boolean, CheckConstraint, DateTime, ForeignKeyConstraint, Index, Integer, Numeric, String, Text, UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base

class PagoProveedor(Base):
    __tablename__ = "pagos_proveedores"
    __table_args__ = (
        ForeignKeyConstraint(["orden_id", "empresa_id"], ["ordenes_compra.id", "ordenes_compra.empresa_id"], name="fk_pago_proveedor_orden_empresa"),
        ForeignKeyConstraint(["usuario_id", "empresa_id"], ["usuarios.id", "usuarios.empresa_id"], name="fk_pago_proveedor_usuario_empresa"),
        UniqueConstraint("empresa_id", "codigo", name="uq_pago_proveedor_empresa_codigo"),
        UniqueConstraint("empresa_id", "idempotency_key", name="uq_pago_proveedor_empresa_idempotencia"),
        CheckConstraint("monto > 0", name="ck_pago_proveedor_monto"),
        CheckConstraint("estado IN ('REGISTRADO','ANULADO')", name="ck_pago_proveedor_estado"),
        Index("ix_pagos_proveedores_empresa_orden", "empresa_id", "orden_id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(Integer, nullable=False)
    orden_id: Mapped[int] = mapped_column(Integer, nullable=False)
    usuario_id: Mapped[int] = mapped_column(Integer, nullable=False)
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False)
    medio_pago: Mapped[str] = mapped_column(String(40), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, server_default="REGISTRADO")
    referencia_externa: Mapped[str | None] = mapped_column(String(120), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
