
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
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from sqlalchemy.dialects.postgresql import JSONB

from app.database.base import Base


class Auditoria(Base):
    __tablename__ = "auditoria"

    __table_args__ = (
        ForeignKeyConstraint(
            ["empresa_id"],
            ["empresas.id"],
            name="fk_auditoria_empresa",
        ),

        ForeignKeyConstraint(
            ["usuario_id", "empresa_id"],
            ["usuarios.id", "usuarios.empresa_id"],
            name="fk_auditoria_usuario_empresa",
        ),

        CheckConstraint(
            "accion IN ("
            "'CREAR', 'ACTUALIZAR', 'ELIMINAR', "
            "'CONFIRMAR', 'CANCELAR', 'ANULAR', "
            "'CONSULTAR', 'OTRO'"
            ")",
            name="ck_auditoria_accion",
        ),

        CheckConstraint(
            "length(trim(entidad)) > 0",
            name="ck_auditoria_entidad",
        ),

        CheckConstraint(
            "entidad_id IS NULL OR entidad_id > 0",
            name="ck_auditoria_entidad_id",
        ),

        Index(
            "ix_auditoria_empresa_fecha",
            "empresa_id",
            "created_at",
        ),

        Index(
            "ix_auditoria_empresa_entidad",
            "empresa_id",
            "entidad",
            "entidad_id",
        ),

        Index(
            "ix_auditoria_empresa_usuario",
            "empresa_id",
            "usuario_id",
        ),

        Index(
            "ix_auditoria_empresa_accion",
            "empresa_id",
            "accion",
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

    # Puede ser NULL para eventos automaticos del sistema.
    usuario_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    accion: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    entidad: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    entidad_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    descripcion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    datos_anteriores: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )

    datos_nuevos: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )

    origen: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default="SISTEMA",
    )

    direccion_ip: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
