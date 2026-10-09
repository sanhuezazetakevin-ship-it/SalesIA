from datetime import datetime
from decimal import Decimal
from sqlalchemy import (Boolean, CheckConstraint, DateTime, ForeignKeyConstraint, Index, Integer, Numeric, String, Text, UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base

class RecepcionCompraDetalle(Base):
    __tablename__ = "recepcion_compra_detalles"
    __table_args__ = (
        ForeignKeyConstraint(["recepcion_id", "orden_id", "empresa_id"], ["recepciones_compra.id", "recepciones_compra.orden_id", "recepciones_compra.empresa_id"], name="fk_recepcion_detalle_recepcion_orden_empresa"),
        ForeignKeyConstraint(["orden_detalle_id", "orden_id", "empresa_id"], ["orden_compra_detalles.id", "orden_compra_detalles.orden_id", "orden_compra_detalles.empresa_id"], name="fk_recepcion_detalle_linea_orden_empresa"),
        CheckConstraint("cantidad_recibida > 0", name="ck_recepcion_detalle_cantidad"),
        UniqueConstraint("recepcion_id", "orden_detalle_id", name="uq_recepcion_detalle_linea"),
        Index("ix_recepcion_detalle_empresa_orden", "empresa_id", "orden_id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(Integer, nullable=False)
    orden_id: Mapped[int] = mapped_column(Integer, nullable=False)
    recepcion_id: Mapped[int] = mapped_column(Integer, nullable=False)
    orden_detalle_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cantidad_recibida: Mapped[Decimal] = mapped_column(Numeric(14,3), nullable=False)
