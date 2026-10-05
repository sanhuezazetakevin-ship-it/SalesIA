
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


class Pedido(Base):
    __tablename__ = "pedidos"

    __table_args__ = (
        ForeignKeyConstraint(
            ["cliente_id", "empresa_id"],
            ["clientes.id", "clientes.empresa_id"],
            name="fk_pedido_cliente_empresa",
        ),
        ForeignKeyConstraint(
            ["usuario_id", "empresa_id"],
            ["usuarios.id", "usuarios.empresa_id"],
            name="fk_pedido_usuario_empresa",
        ),
        UniqueConstraint(
            "id",
            "empresa_id",
            name="uq_pedido_id_empresa",
        ),
        UniqueConstraint(
            "empresa_id",
            "codigo",
            name="uq_pedido_codigo_empresa",
        ),
        CheckConstraint(
            "estado IN ("
            "'BORRADOR', 'CONFIRMADO', "
            "'COMPLETADO', 'CANCELADO'"
            ")",
            name="ck_pedido_estado",
        ),
        CheckConstraint(
            "subtotal >= 0 AND total >= 0 AND impuesto_total >= 0",
            name="ck_pedido_importes",
        ),
        CheckConstraint(
            "total = subtotal + impuesto_total",
            name="ck_pedido_total",
        ),
        Index(
            "ix_pedidos_empresa_fecha",
            "empresa_id",
            "created_at",
        ),
        Index(
            "ix_pedidos_empresa_estado",
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
        server_default="BORRADOR",
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
