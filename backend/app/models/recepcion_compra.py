from datetime import datetime
from decimal import Decimal
from sqlalchemy import (Boolean, CheckConstraint, DateTime, ForeignKeyConstraint, Index, Integer, Numeric, String, Text, UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base

class RecepcionCompra(Base):
    __tablename__ = "recepciones_compra"
    __table_args__ = (
        ForeignKeyConstraint(["orden_id", "empresa_id"], ["ordenes_compra.id", "ordenes_compra.empresa_id"], name="fk_recepcion_compra_orden_empresa"),
        ForeignKeyConstraint(["usuario_id", "empresa_id"], ["usuarios.id", "usuarios.empresa_id"], name="fk_recepcion_compra_usuario_empresa"),
        UniqueConstraint("id", "orden_id", "empresa_id", name="uq_recepcion_id_orden_empresa"),
        UniqueConstraint("id", "empresa_id", name="uq_recepcion_id_empresa"),
        UniqueConstraint("empresa_id", "codigo", name="uq_recepcion_empresa_codigo"),
        UniqueConstraint("empresa_id", "idempotency_key", name="uq_recepcion_empresa_idempotencia"),
        CheckConstraint("estado = 'CONFIRMADA'", name="ck_recepcion_estado"),
        Index("ix_recepciones_empresa_orden", "empresa_id", "orden_id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(Integer, nullable=False)
    orden_id: Mapped[int] = mapped_column(Integer, nullable=False)
    usuario_id: Mapped[int] = mapped_column(Integer, nullable=False)
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, server_default="CONFIRMADA")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
