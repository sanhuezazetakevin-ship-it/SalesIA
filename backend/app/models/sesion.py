
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, ForeignKeyConstraint,
    Index, Integer, String, func
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Sesion(Base):
    __tablename__ = "sesiones"

    __table_args__ = (
        ForeignKeyConstraint(
            ["usuario_id", "empresa_id"],
            ["usuarios.id", "usuarios.empresa_id"],
            name="fk_sesion_usuario_empresa",
            ondelete="CASCADE",
        ),
        Index("ix_sesiones_usuario_id", "usuario_id"),
        Index("ix_sesiones_empresa_id", "empresa_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(Integer, nullable=False)
    empresa_id: Mapped[int] = mapped_column(Integer, nullable=False)

    token_hash: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )

    fecha_expiracion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    revocada: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
