
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, ForeignKeyConstraint,
    Index, Integer, String, func,UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ConsentimientoBiometrico(Base):
    __tablename__ = "consentimientos_biometricos"

    __table_args__ = (
        ForeignKeyConstraint(
            ["usuario_id", "empresa_id"],
            ["usuarios.id", "usuarios.empresa_id"],
            name="fk_consentimiento_usuario_empresa",
            ondelete="CASCADE",
        ),
        Index(
            "ix_consentimientos_usuario_id",
            "usuario_id",
        ),
        UniqueConstraint(
            "id",
            "usuario_id",
            "empresa_id",
        name="uq_consentimiento_usuario_empresa",
),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    usuario_id: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    empresa_id: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    version_texto: Mapped[str] = mapped_column(
        String(30), nullable=False
    )

    aceptado: Mapped[bool] = mapped_column(
        Boolean, nullable=False
    )

    fecha_consentimiento: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    fecha_revocacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
