
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


class DocumentoFacturacion(Base):
    __tablename__ = "documentos_facturacion"

    __table_args__ = (
        # La venta debe pertenecer a la misma empresa.
        ForeignKeyConstraint(
            ["venta_id", "empresa_id"],
            ["ventas.id", "ventas.empresa_id"],
            name="fk_documento_venta_empresa",
        ),

        # El usuario emisor debe pertenecer a la misma empresa.
        ForeignKeyConstraint(
            ["emitido_por_id", "empresa_id"],
            ["usuarios.id", "usuarios.empresa_id"],
            name="fk_documento_usuario_empresa",
        ),
        # Numeracion unica por empresa y tipo de documento.
        UniqueConstraint(
            "empresa_id",
            "tipo_documento",
            "serie",
            "numero",
            name="uq_documento_numeracion_empresa",
        ),
        
        CheckConstraint(
            "tipo_documento IN ('FACTURA', 'BOLETA', 'OTRO')",
            name="ck_documento_tipo",
        ),

        CheckConstraint(
            "estado IN ("
            "'BORRADOR', 'EMITIDO', 'ANULADO', 'RECHAZADO'"
            ")",
            name="ck_documento_estado",
        ),
        CheckConstraint(
            "numero > 0",
            name="ck_documento_numero_positivo",
        ),
        
        CheckConstraint(
            "length(trim(serie)) > 0",
            name="ck_documento_serie",
        ),
        CheckConstraint(
            "subtotal >= 0 AND impuesto_total >= 0 AND total >= 0",
            name="ck_documento_importes",
        ),
        CheckConstraint(
            "total = subtotal + impuesto_total",
            name="ck_documento_total",
        ),
        
        CheckConstraint(
            "("
            "estado = 'BORRADOR' "
            "AND fecha_emision IS NULL"
            ") OR ("
            "estado IN ('EMITIDO', 'ANULADO', 'RECHAZADO') "
            "AND fecha_emision IS NOT NULL"
            ")",
            name="ck_documento_fecha_estado",
        ),
        CheckConstraint(
            "length(trim(receptor_nombre)) > 0",
            name="ck_documento_receptor_nombre",
        ),
        CheckConstraint(
            "length(moneda) = 3 AND moneda = upper(moneda)",
            name="ck_documento_moneda",
        ),
        Index(
            "ix_documentos_empresa_estado",
            "empresa_id",
            "estado",
        ),

        Index(
            "ix_documentos_empresa_fecha",
            "empresa_id",
            "fecha_emision",
        ),

        Index(
            "ix_documentos_empresa_venta",
            "empresa_id",
            "venta_id",
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

    emitido_por_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    tipo_documento: Mapped[str] = mapped_column(
        String(25),
        nullable=False,
    )

    serie: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    numero: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="BORRADOR",
    )

    # Datos historicos del receptor.
    receptor_nombre: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    receptor_tipo_documento: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    receptor_numero_documento: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    receptor_direccion: Mapped[str | None] = mapped_column(
        String(350),
        nullable=True,
    )

    # Moneda historica del comprobante.
    moneda: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        server_default="PEN",
    )

    # Importes historicos.
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    impuesto_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    # Datos opcionales de integracion electronica.
    codigo_externo: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    respuesta_externa: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    observaciones: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    fecha_emision: Mapped[datetime | None] = mapped_column(
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
