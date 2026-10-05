
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, ForeignKeyConstraint,
    Index, Integer, LargeBinary, String, func
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class RegistroFacial(Base):
    __tablename__ = "registros_faciales"

    __table_args__ = (
        ForeignKeyConstraint(
            ["usuario_id", "empresa_id"],
            ["usuarios.id", "usuarios.empresa_id"],
            name="fk_registro_facial_usuario_empresa",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
        ["consentimiento_id", "usuario_id", "empresa_id"],
        [
        "consentimientos_biometricos.id",
        "consentimientos_biometricos.usuario_id",
        "consentimientos_biometricos.empresa_id",
        ],
        name="fk_registro_facial_consentimiento",
),
        Index(
            "ix_registros_faciales_usuario_id",
            "usuario_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    usuario_id: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    empresa_id: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    consentimiento_id: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    modelo: Mapped[str] = mapped_column(
        String(100), nullable=False
    )

    embedding_cifrado: Mapped[bytes] = mapped_column(
        LargeBinary, nullable=False
    )

    clave_version: Mapped[str] = mapped_column(
        String(50), nullable=False
    )

    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
