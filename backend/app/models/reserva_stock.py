
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ReservaStock(Base):
    __tablename__ = "reservas_stock"

    __table_args__ = (
        ForeignKeyConstraint(
            ["pedido_id", "empresa_id"],
            ["pedidos.id", "pedidos.empresa_id"],
            name="fk_reserva_pedido_empresa",
        ),
        ForeignKeyConstraint(
            ["inventario_id", "producto_id", "empresa_id"],
            [
                "inventario.id",
                "inventario.producto_id",
                "inventario.empresa_id",
            ],
            name="fk_reserva_inventario_empresa",
        ),
        
        ForeignKeyConstraint(
            ["pedido_id", "producto_id", "empresa_id"],
            [
                "pedido_detalles.pedido_id",
                "pedido_detalles.producto_id",
                "pedido_detalles.empresa_id",
            ],
            name="fk_reserva_detalle_pedido_empresa",
        ),

        UniqueConstraint(
            "pedido_id",
            "producto_id",
            name="uq_reserva_pedido_producto",
        ),
        CheckConstraint(
            "cantidad_reservada > 0",
            name="ck_reserva_cantidad_positiva",
        ),
        CheckConstraint(
            "estado IN ('ACTIVA', 'LIBERADA', 'CONSUMIDA')",
            name="ck_reserva_estado",
        ),
        Index(
            "ix_reservas_empresa_estado",
            "empresa_id",
            "estado",
        ),
        Index(
            "ix_reservas_inventario_estado",
            "inventario_id",
            "estado",
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

    inventario_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    cantidad_reservada: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        nullable=False,
    )

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="ACTIVA",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
