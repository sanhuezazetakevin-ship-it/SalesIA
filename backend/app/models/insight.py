
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Insight(Base):
    __tablename__ = "insights"

    __table_args__ = (
        ForeignKeyConstraint(
            ["empresa_id"],
            ["empresas.id"],
            name="fk_insight_empresa",
        ),

        ForeignKeyConstraint(
            ["analisis_estadistico_id", "empresa_id"],
            [
                "analisis_estadisticos.id",
                "analisis_estadisticos.empresa_id",
            ],
            name="fk_insight_analisis_estadistico_empresa",
        ),

        ForeignKeyConstraint(
            ["analisis_probabilidad_id", "empresa_id"],
            [
                "analisis_probabilidad.id",
                "analisis_probabilidad.empresa_id",
            ],
            name="fk_insight_analisis_probabilidad_empresa",
        ),

        CheckConstraint(
            "("
            "analisis_estadistico_id IS NOT NULL "
            "AND analisis_probabilidad_id IS NULL"
            ") OR ("
            "analisis_estadistico_id IS NULL "
            "AND analisis_probabilidad_id IS NOT NULL"
            ")",
            name="ck_insight_origen_exclusivo",
        ),

        CheckConstraint(
            "tipo_insight IN ("
            "'VENTAS', 'INVENTARIO', 'CLIENTES', "
            "'RENDIMIENTO', 'PREDICCION', 'GENERAL'"
            ")",
            name="ck_insight_tipo",
        ),

        CheckConstraint(
            "prioridad IN ('BAJA', 'MEDIA', 'ALTA', 'CRITICA')",
            name="ck_insight_prioridad",
        ),

        CheckConstraint(
            "estado IN ('NUEVO', 'REVISADO', 'DESCARTADO')",
            name="ck_insight_estado",
        ),

        CheckConstraint(
            "length(trim(titulo)) > 0 "
            "AND length(trim(descripcion)) > 0",
            name="ck_insight_contenido",
        ),

        Index(
            "ix_insights_empresa_estado",
            "empresa_id",
            "estado",
        ),

        Index(
            "ix_insights_empresa_prioridad",
            "empresa_id",
            "prioridad",
        ),

        Index(
            "ix_insights_empresa_tipo",
            "empresa_id",
            "tipo_insight",
        ),

        Index(
            "ix_insights_empresa_fecha",
            "empresa_id",
            "created_at",
        ),

        Index(
            "ix_insights_empresa_analisis_est",
            "empresa_id",
            "analisis_estadistico_id",
        ),

        Index(
            "ix_insights_empresa_analisis_prob",
            "empresa_id",
            "analisis_probabilidad_id",
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

    analisis_estadistico_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    analisis_probabilidad_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    tipo_insight: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    prioridad: Mapped[str] = mapped_column(
        String(15),
        nullable=False,
        server_default="MEDIA",
    )

    titulo: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
    )

    descripcion: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    recomendacion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="NUEVO",
    )

    datos_soporte: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
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
