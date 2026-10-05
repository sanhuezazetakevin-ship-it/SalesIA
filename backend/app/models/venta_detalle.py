
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class VentaDetalle(Base):
    __tablename__ = "venta_detalles"

    __table_args__ = (
        ForeignKeyConstraint(
            ["venta_id", "empresa_id"],
            ["ventas.id", "ventas.empresa_id"],
            name="fk_venta_detalle_venta_empresa",
        ),
        ForeignKeyConstraint(
            ["producto_id", "empresa_id"],
            ["productos.id", "productos.empresa_id"],
            name="fk_venta_detalle_producto_empresa",
        ),
        UniqueConstraint(
            "venta_id",
            "producto_id",
            name="uq_venta_detalle_producto",
        ),
        CheckConstraint(
            "cantidad > 0",
            name="ck_venta_detalle_cantidad",
        ),
        CheckConstraint(
            "precio_unitario >= 0",
            name="ck_venta_detalle_precio",
        ),
        CheckConstraint(
            "descuento >= 0",
            name="ck_venta_detalle_descuento",
        ),
        CheckConstraint(
            "subtotal >= 0 AND impuesto >= 0 AND total >= 0",
            name="ck_venta_detalle_importes",
        ),
        CheckConstraint(
            "total = subtotal + impuesto",
            name="ck_venta_detalle_total",
        ),
        CheckConstraint(
            "tasa_impuesto IS NULL OR "
            "(tasa_impuesto >= 0 AND tasa_impuesto <= 100)",
            name="ck_venta_detalle_tasa_impuesto",
        ),
        Index(
            "ix_venta_detalles_empresa_venta",
            "empresa_id",
            "venta_id",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    empresa_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    venta_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    producto_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    descripcion: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    cantidad: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        nullable=False,
    )

    # Precio comercial con impuestos incluidos.
    precio_unitario: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    descuento: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        server_default="0",
    )

    # Base imponible después del descuento.
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    impuesto: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        server_default="0",
    )

    # Importe final con impuestos incluidos.
    total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    
    # Tasa historica aplicada a la linea de venta.
    tasa_impuesto: Mapped[Decimal | None] = mapped_column(
        Numeric(7, 4),
        nullable=True,
    )
