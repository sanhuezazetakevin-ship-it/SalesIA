
from datetime import datetime

from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKey,
    ForeignKeyConstraint, Index, Integer,
    String, func
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class InvitacionUsuario(Base):
    __tablename__ = "invitaciones_usuario"

    __table_args__ = (
        ForeignKeyConstraint(
            ["invitado_por_id", "empresa_id"],
            ["usuarios.id", "usuarios.empresa_id"],
            name="fk_invitacion_autor_empresa",
        ),
        CheckConstraint(
            "estado IN ('pendiente', 'aceptada', "
            "'revocada', 'expirada')",
            name="ck_invitaciones_estado",
        ),
        Index(
            "ix_invitaciones_empresa_estado",
            "empresa_id", "estado",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    empresa_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresas.id"),
        nullable=False,
    )

    invitado_por_id: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(255), nullable=False
    )

    token_hash: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="pendiente",
    )

    fecha_expiracion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
