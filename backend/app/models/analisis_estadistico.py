
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


class AnalisisEstadistico(Base):
    __tablename__ = "analisis_estadisticos"

    __table_args__ = (
        ForeignKeyConstraint(
            ["empresa_id"],
            ["empresas.id"],
            name="fk_analisis_estadistico_empresa",
        ),

        CheckConstraint(
            "tipo_analisis IN ("
            "'VENTAS', 'INVENTARIO', 'CLIENTES', "
            "'RENDIMIENTO', 'GENERAL'"
            ")",
            name="ck_analisis_estadistico_tipo",
        ),

        CheckConstraint(
            "estado IN ('PENDIENTE', 'COMPLETADO', 'FALLIDO')",
            name="ck_analisis_estadistico_estado",
        ),

        CheckConstraint(
            "fecha_fin >= fecha_inicio",
            name="ck_analisis_estadistico_periodo",
        ),

        CheckConstraint(
            "length(trim(nombre)) > 0",
            name="ck_analisis_estadistico_nombre",
        ),

        CheckConstraint(
            "(estado = 'COMPLETADO' AND fecha_calculo IS NOT NULL "
            "AND resultados IS NOT NULL) "
            "OR "
            "(estado <> 'COMPLETADO' AND fecha_calculo IS NULL "
            "AND resultados IS NULL)",
            name="ck_analisis_estadistico_resultado_estado",
        ),
        
        UniqueConstraint(
            "id",
            "empresa_id",
            name="uq_analisis_estadistico_id_empresa",
        ),

        Index(
            "ix_analisis_est_empresa_tipo",
            "empresa_id",
            "tipo_analisis",
        ),

        Index(
            "ix_analisis_est_empresa_estado",
            "empresa_id",
            "estado",
        ),

        Index(
            "ix_analisis_est_empresa_periodo",
            "empresa_id",
            "fecha_inicio",
            "fecha_fin",
        ),

        Index(
            "ix_analisis_est_empresa_fecha",
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

    nombre: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    tipo_analisis: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="PENDIENTE",
    )

    fecha_inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    fecha_fin: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Resultados calculados por el backend.
    resultados: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )

    # Version del algoritmo utilizado.
    version_calculo: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default="1.0",
    )

    # Informacion sobre un fallo de procesamiento.
    mensaje_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    fecha_calculo: Mapped[datetime | None] = mapped_column(
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
