
from datetime import datetime

from sqlalchemy import (
    DateTime, ForeignKeyConstraint, Index,
    Integer, String, func
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class EventoAuth(Base):
    __tablename__ = "eventos_auth"

    __table_args__ = (
        
ForeignKeyConstraint(
    ["usuario_id", "empresa_id"],
    ["usuarios.id", "usuarios.empresa_id"],
    name="fk_evento_auth_usuario_empresa",
),

        Index("ix_eventos_auth_created_at", "created_at"),
        Index("ix_eventos_auth_empresa_id", "empresa_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    usuario_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    empresa_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    tipo_evento: Mapped[str] = mapped_column(
        String(80), nullable=False
    )

    resultado: Mapped[str] = mapped_column(
        String(30), nullable=False
    )

    detalle: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
