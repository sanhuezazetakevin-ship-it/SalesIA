
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


class Venta(Base):
    __tablename__ = "ventas"

    __table_args__ = (
        ForeignKeyConstraint(
            ["pedido_id", "empresa_id"],
            ["pedidos.id", "pedidos.empresa_id"],
            name="fk_venta_pedido_empresa",
        ),
        ForeignKeyConstraint(
            ["cliente_id", "empresa_id"],
            ["clientes.id", "clientes.empresa_id"],
            name="fk_venta_cliente_empresa",
        ),
        ForeignKeyConstraint(
            ["usuario_id", "empresa_id"],
            ["usuarios.id", "usuarios.empresa_id"],
            name="fk_venta_usuario_empresa",
        ),
        UniqueConstraint(
            "empresa_id",
            "codigo",
            name="uq_venta_codigo_empresa",
        ),
        UniqueConstraint(
            "id",
            "empresa_id",
            name="uq_venta_id_empresa",
        ),
        UniqueConstraint(
            "pedido_id",
            name="uq_venta_pedido",
        ),
        CheckConstraint(
            "estado IN ('REGISTRADA', 'CONFIRMADA', 'CANCELADA')",
            name="ck_venta_estado",
        ),
        CheckConstraint(
            "estado_pago IN ('PENDIENTE', 'PARCIAL', 'PAGADO')",
            name="ck_venta_estado_pago",
        ),
        CheckConstraint(
            "subtotal >= 0 AND impuesto_total >= 0 AND total >= 0",
            name="ck_venta_importes",
        ),
        CheckConstraint(
            "total = subtotal + impuesto_total",
            name="ck_venta_total",
        ),
        Index(
            "ix_ventas_empresa_fecha",
            "empresa_id",
            "created_at",
        ),
        Index(
            "ix_ventas_empresa_estado",
            "empresa_id",
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

    # Nullable para permitir ventas directas sin pedido previo.
    pedido_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    cliente_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    usuario_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    codigo: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="REGISTRADA",
    )

    estado_pago: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="PENDIENTE",
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        server_default="0",
    )

    impuesto_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        server_default="0",
    )

    total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        server_default="0",
    )

    observaciones: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
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
