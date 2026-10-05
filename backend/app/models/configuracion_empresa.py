
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ConfiguracionEmpresa(Base):
    __tablename__ = "configuraciones_empresa"

    __table_args__ = (
        UniqueConstraint(
            "empresa_id",
            name="uq_configuracion_empresa",
        ),
        CheckConstraint(
            "length(trim(zona_horaria)) > 0",
            name="ck_configuracion_zona_horaria",
        ),
        CheckConstraint(
            "length(trim(formato_codigo_venta)) > 0",
            name="ck_configuracion_formato_venta",
        ),
        CheckConstraint(
            "permite_pagos_parciales IS TRUE "
            "AND descuento_stock_en_entrega IS TRUE "
            "AND precios_incluyen_impuestos IS TRUE",
            name="ck_configuracion_reglas_salesia",
        ),
        CheckConstraint(
            "length(trim(formato_codigo_pedido)) > 0",
            name="ck_configuracion_formato_pedido",
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
            name="fk_configuracion_empresa",
        ),
        nullable=False,
    )

    zona_horaria: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
        server_default="America/Lima",
    )

    formato_codigo_venta: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default="VEN",
    )

    formato_codigo_pedido: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default="PED",
    )

    permite_pagos_parciales: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
    )

    descuento_stock_en_entrega: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
    )

    precios_incluyen_impuestos: Mapped[bool] = mapped_column(
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
