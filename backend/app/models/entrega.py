
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Entrega(Base):
    __tablename__ = "entregas"

    __table_args__ = (
        ForeignKeyConstraint(
            ["venta_id", "empresa_id"],
            ["ventas.id", "ventas.empresa_id"],
            name="fk_entrega_venta_empresa",
        ),
        ForeignKeyConstraint(
            ["responsable_id", "empresa_id"],
            ["usuarios.id", "usuarios.empresa_id"],
            name="fk_entrega_responsable_empresa",
        ),
        UniqueConstraint(
            "venta_id",
            name="uq_entrega_venta",
        ),
        UniqueConstraint(
            "empresa_id",
            "codigo",
            name="uq_entrega_codigo_empresa",
        ),
        UniqueConstraint(
            "id",
            "empresa_id",
            name="uq_entrega_id_empresa",
        ),
        CheckConstraint(
            "estado IN ('PENDIENTE', 'CONFIRMADA', 'CANCELADA')",
            name="ck_entrega_estado",
        ),
        CheckConstraint(
            "(estado = 'CONFIRMADA' AND fecha_confirmacion IS NOT NULL) "
            "OR "
            "(estado <> 'CONFIRMADA' AND fecha_confirmacion IS NULL)",
            name="ck_entrega_confirmacion_fecha",
        ),
        
        Index(
            "ix_entregas_empresa_estado",
            "empresa_id",
            "estado",
        ),
        Index(
            "ix_entregas_empresa_fecha",
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

    responsable_id: Mapped[int] = mapped_column(
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
        server_default="PENDIENTE",
    )

    observaciones: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    fecha_confirmacion: Mapped[datetime | None] = mapped_column(
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
