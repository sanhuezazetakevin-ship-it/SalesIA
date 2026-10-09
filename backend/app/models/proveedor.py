from datetime import datetime
from decimal import Decimal
from sqlalchemy import (Boolean, CheckConstraint, DateTime, ForeignKeyConstraint, Index, Integer, Numeric, String, Text, UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base

class Proveedor(Base):
    __tablename__ = "proveedores"
    __table_args__ = (
        ForeignKeyConstraint(["empresa_id"], ["empresas.id"], name="fk_proveedor_empresa"),
        UniqueConstraint("id", "empresa_id", name="uq_proveedor_id_empresa"),
        UniqueConstraint("empresa_id", "tipo_documento", "numero_documento", name="uq_proveedor_empresa_documento"),
        CheckConstraint("length(trim(razon_social)) > 0", name="ck_proveedor_razon_social"),
        Index("ix_proveedores_empresa_nombre", "empresa_id", "razon_social"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo_documento: Mapped[str | None] = mapped_column(String(20), nullable=True)
    numero_documento: Mapped[str | None] = mapped_column(String(30), nullable=True)
    razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(40), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
