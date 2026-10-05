
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


class PedidoDetalle(Base):
    __tablename__ = "pedido_detalles"

    __table_args__ = (
        ForeignKeyConstraint(
            ["pedido_id", "empresa_id"],
            ["pedidos.id", "pedidos.empresa_id"],
            name="fk_pedido_detalle_pedido_empresa",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["producto_id", "empresa_id"],
            ["productos.id", "productos.empresa_id"],
            name="fk_pedido_detalle_producto_empresa",
        ),
        UniqueConstraint(
            "pedido_id",
            "producto_id",
            name="uq_pedido_detalle_producto",
        ),
        UniqueConstraint(
            "pedido_id",
            "producto_id",
            "empresa_id",
            name="uq_pedido_detalle_pedido_producto_empresa",
        ),

        CheckConstraint(
            "cantidad > 0",
            name="ck_pedido_detalle_cantidad",
        ),
        CheckConstraint(
            "precio_unitario >= 0",
            name="ck_pedido_detalle_precio",
        ),
        CheckConstraint(
            "descuento >= 0",
            name="ck_pedido_detalle_descuento",
        ),
        CheckConstraint(
            "subtotal >= 0 AND impuesto >= 0 AND total >= 0",
            name="ck_pedido_detalle_importes",
        ),
        CheckConstraint(
            "total = subtotal + impuesto",
            name="ck_pedido_detalle_total",
        ),
        CheckConstraint(
            "tasa_impuesto IS NULL OR "
            "(tasa_impuesto >= 0 AND tasa_impuesto <= 100)",
            name="ck_pedido_detalle_tasa_impuesto",
        ),
        Index(
            "ix_pedido_detalles_empresa_pedido",
            "empresa_id",
            "pedido_id",
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

    pedido_id: Mapped[int] = mapped_column(
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

    precio_unitario: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    descuento: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        server_default="0",
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    impuesto: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        server_default="0",
    )

    total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    tasa_impuesto: Mapped[Decimal | None] = mapped_column(
        Numeric(7, 4),
        nullable=True,
    )