
from datetime import datetime

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey,
    Index, Integer, String, UniqueConstraint, func
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Cliente(Base):
    __tablename__ = "clientes"

    __table_args__ = (
        UniqueConstraint(
            "empresa_id", "tipo_documento", "numero_documento",
            name="uq_cliente_documento_empresa"
        ),
        UniqueConstraint(
            "id", "empresa_id",
            name="uq_cliente_id_empresa"
        ),
        CheckConstraint(
            "tipo_documento IN ('DNI', 'RUC', 'CE', 'PASAPORTE')",
            name="ck_cliente_tipo_documento"
        ),
        Index("ix_clientes_empresa_nombre", "empresa_id", "nombre"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    empresa_id: Mapped[int] = mapped_column(
        ForeignKey("empresas.id"), nullable=False
    )

    nombre: Mapped[str] = mapped_column(String(200), nullable=False)

    tipo_documento: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )

    numero_documento: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )

    email: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    telefono: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )

    direccion: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
