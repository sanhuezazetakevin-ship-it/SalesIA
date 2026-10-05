
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    BigInteger,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ReporteGenerado(Base):
    __tablename__ = "reportes_generados"

    __table_args__ = (
        ForeignKeyConstraint(
            ["empresa_id"],
            ["empresas.id"],
            name="fk_reporte_empresa",
        ),

        ForeignKeyConstraint(
            ["solicitado_por_id", "empresa_id"],
            ["usuarios.id", "usuarios.empresa_id"],
            name="fk_reporte_usuario_empresa",
        ),

        CheckConstraint(
            "tipo_reporte IN ("
            "'VENTAS', 'INVENTARIO', 'CLIENTES', "
            "'RENDIMIENTO', 'ESTADISTICO', "
            "'PREDICTIVO', 'INSIGHTS', 'GENERAL'"
            ")",
            name="ck_reporte_tipo",
        ),

        CheckConstraint(
            "formato IN ('PDF', 'XLSX', 'CSV')",
            name="ck_reporte_formato",
        ),

        CheckConstraint(
            "estado IN ("
            "'PENDIENTE', 'PROCESANDO', "
            "'COMPLETADO', 'FALLIDO'"
            ")",
            name="ck_reporte_estado",
        ),

        CheckConstraint(
            "length(trim(nombre)) > 0",
            name="ck_reporte_nombre",
        ),

        CheckConstraint(
            "tamano_bytes IS NULL OR tamano_bytes >= 0",
            name="ck_reporte_tamano",
        ),

        CheckConstraint(
            "("
            "estado = 'COMPLETADO' "
            "AND ruta_archivo IS NOT NULL "
            "AND length(trim(ruta_archivo)) > 0 "
            "AND tamano_bytes IS NOT NULL "
            "AND tamano_bytes > 0 "
            "AND fecha_generacion IS NOT NULL "
            "AND mensaje_error IS NULL"
            ") OR ("
            "estado <> 'COMPLETADO' "
            "AND ruta_archivo IS NULL "
            "AND tamano_bytes IS NULL "
            "AND fecha_generacion IS NULL"
            ")",
            name="ck_reporte_resultado_estado",
        ),

        CheckConstraint(
            "estado <> 'FALLIDO' OR "
            "(mensaje_error IS NOT NULL "
            "AND length(trim(mensaje_error)) > 0)",
            name="ck_reporte_error_fallido",
        ),

        Index(
            "ix_reportes_empresa_estado",
            "empresa_id",
            "estado",
        ),

        Index(
            "ix_reportes_empresa_tipo",
            "empresa_id",
            "tipo_reporte",
        ),

        Index(
            "ix_reportes_empresa_usuario",
            "empresa_id",
            "solicitado_por_id",
        ),

        Index(
            "ix_reportes_empresa_fecha",
            "empresa_id",
            "created_at",
        ),

        Index(
            "ix_reportes_empresa_formato",
            "empresa_id",
            "formato",
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

    solicitado_por_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    nombre: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
    )

    tipo_reporte: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    formato: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="PENDIENTE",
    )

    # Filtros y parametros de generacion.
    parametros: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )

    # Clave interna del archivo en el almacenamiento.
    ruta_archivo: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    tamano_bytes: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    mensaje_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    fecha_generacion: Mapped[datetime | None] = mapped_column(
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
