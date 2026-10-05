
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey,
    ForeignKeyConstraint, Index, Integer, Numeric,
    String, UniqueConstraint, func
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Producto(Base):
    __tablename__ = "productos"

    __table_args__ = (
        UniqueConstraint(
            "empresa_id", "sku",
            name="uq_producto_empresa_sku"
        ),
        UniqueConstraint(
            "id", "empresa_id",
            name="uq_producto_id_empresa"
        ),
        ForeignKeyConstraint(
            ["categoria_id", "empresa_id"],
            ["categorias.id", "categorias.empresa_id"],
            name="fk_producto_categoria_empresa"
        ),
        CheckConstraint(
            "precio_venta >= 0",
            name="ck_producto_precio_venta"
        ),
        CheckConstraint(
            "costo_referencia >= 0",
            name="ck_producto_costo_referencia"
        ),
        CheckConstraint(
            "tipo_item IN ('PRODUCTO', 'SERVICIO', 'INSUMO', 'MISCELANEO')",
            name="ck_producto_tipo_item"
        ),
        Index(
            "ix_productos_empresa_nombre",
            "empresa_id", "nombre"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    empresa_id: Mapped[int] = mapped_column(
        ForeignKey("empresas.id"), nullable=False
    )

    categoria_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    sku: Mapped[str] = mapped_column(
        String(80), nullable=False
    )

    nombre: Mapped[str] = mapped_column(
        String(200), nullable=False
    )

    descripcion: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )

    tipo_item: Mapped[str] = mapped_column(
        String(20), nullable=False
    )

    precio_venta: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )

    costo_referencia: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False,
        server_default="0"
    )

    controla_stock: Mapped[bool] = mapped_column(
        Boolean, nullable=False,
        server_default="true"
    )

    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False,
        server_default="true"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
