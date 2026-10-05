
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import UniqueConstraint
from app.database.base import Base


class AnalisisProbabilidad(Base):
    __tablename__ = "analisis_probabilidad"

    __table_args__ = (
        ForeignKeyConstraint(
            ["empresa_id"],
            ["empresas.id"],
            name="fk_analisis_probabilidad_empresa",
        ),

        CheckConstraint(
            "tipo_analisis IN ("
            "'COMPRA', 'DESABASTECIMIENTO', "
            "'RECURRENCIA_CLIENTE', 'PROYECCION_VENTAS', 'OTRO'"
            ")",
            name="ck_analisis_probabilidad_tipo",
        ),

        CheckConstraint(
            "estado IN ('PENDIENTE', 'COMPLETADO', 'FALLIDO')",
            name="ck_analisis_probabilidad_estado",
        ),

        CheckConstraint(
            "probabilidad IS NULL OR "
            "(probabilidad >= 0 AND probabilidad <= 1)",
            name="ck_analisis_probabilidad_rango",
        ),

        CheckConstraint(
            "entidad_id IS NULL OR entidad_id > 0",
            name="ck_analisis_probabilidad_entidad_id",
        ),

        CheckConstraint(
            "length(trim(modelo_nombre)) > 0 "
            "AND length(trim(modelo_version)) > 0",
            name="ck_analisis_probabilidad_modelo",
        ),

        CheckConstraint(
            "("
            "estado = 'COMPLETADO' "
            "AND fecha_prediccion IS NOT NULL "
            "AND resultados IS NOT NULL "
            "AND resultado_predicho IS NOT NULL"
            ") OR ("
            "estado <> 'COMPLETADO' "
            "AND fecha_prediccion IS NULL "
            "AND resultados IS NULL "
            "AND resultado_predicho IS NULL "
            "AND probabilidad IS NULL"
            ")",
            name="ck_analisis_probabilidad_resultado_estado",
        ),
        
        UniqueConstraint(
            "id",
            "empresa_id",
            name="uq_analisis_probabilidad_id_empresa",
        ),

        Index(
            "ix_analisis_prob_empresa_tipo",
            "empresa_id",
            "tipo_analisis",
        ),

        Index(
            "ix_analisis_prob_empresa_estado",
            "empresa_id",
            "estado",
        ),

        Index(
            "ix_analisis_prob_empresa_entidad",
            "empresa_id",
            "entidad",
            "entidad_id",
        ),

        Index(
            "ix_analisis_prob_empresa_fecha",
            "empresa_id",
            "created_at",
        ),

        Index(
            "ix_analisis_prob_empresa_modelo",
            "empresa_id",
            "modelo_nombre",
            "modelo_version",
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

    tipo_analisis: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    # Entidad empresarial evaluada.
    entidad: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    entidad_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    modelo_nombre: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    modelo_version: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="PENDIENTE",
    )

    # Probabilidad expresada entre 0 y 1.
    probabilidad: Mapped[Decimal | None] = mapped_column(
        Numeric(7, 6),
        nullable=True,
    )

    resultado_predicho: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    # Variables de entrada previamente filtradas.
    datos_entrada: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )

    # Salida estructurada del modelo.
    resultados: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )

    mensaje_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    fecha_prediccion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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
