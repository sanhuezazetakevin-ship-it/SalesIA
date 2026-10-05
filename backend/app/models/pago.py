
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


class Pago(Base):
    __tablename__ = "pagos"

    __table_args__ = (
        ForeignKeyConstraint(
            ["venta_id", "empresa_id"],
            ["ventas.id", "ventas.empresa_id"],
            name="fk_pago_venta_empresa",
        ),
        ForeignKeyConstraint(
            ["registrado_por_id", "empresa_id"],
            ["usuarios.id", "usuarios.empresa_id"],
            name="fk_pago_usuario_empresa",
        ),
        UniqueConstraint(
            "empresa_id",
            "codigo",
            name="uq_pago_codigo_empresa",
        ),
        CheckConstraint(
            "monto > 0",
            name="ck_pago_monto_positivo",
        ),
        CheckConstraint(
            "medio_pago IN ("
            "'EFECTIVO', 'TARJETA', 'TRANSFERENCIA', "
            "'YAPE', 'PLIN', 'OTRO'"
            ")",
            name="ck_pago_medio",
        ),
        CheckConstraint(
            "estado IN ('REGISTRADO', 'ANULADO')",
            name="ck_pago_estado",
        ),
        Index(
            "ix_pagos_empresa_venta",
            "empresa_id",
            "venta_id",
        ),
        Index(
            "ix_pagos_empresa_fecha",
            "empresa_id",
            "created_at",
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

    registrado_por_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    codigo: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    monto: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    medio_pago: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="REGISTRADO",
    )

    referencia_externa: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
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
