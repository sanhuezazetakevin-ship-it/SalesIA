
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Impuesto(Base):
    __tablename__ = "impuestos"

    __table_args__ = (
        UniqueConstraint(
            "empresa_id",
            "codigo",
            name="uq_impuesto_empresa_codigo",
        ),
        CheckConstraint(
            "tasa >= 0 AND tasa <= 100",
            name="ck_impuesto_tasa",
        ),
        CheckConstraint(
            "length(trim(codigo)) > 0 "
            "AND length(trim(nombre)) > 0",
            name="ck_impuesto_identificacion",
        ),

        Index(
            "ix_impuestos_empresa_activo",
            "empresa_id",
            "activo",
        ),
        CheckConstraint(
            "incluido_en_precio IS TRUE",
            name="ck_impuesto_incluido_en_precio",
        ),

    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    empresa_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "empresas.id",
            name="fk_impuesto_empresa",
        ),
        nullable=False,
    )

    codigo: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    nombre: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    tasa: Mapped[Decimal] = mapped_column(
        Numeric(7, 4),
        nullable=False,
    )

    incluido_en_precio: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
    )

    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
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
