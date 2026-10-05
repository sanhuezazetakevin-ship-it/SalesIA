
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
    func,
)

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Empresa(Base):
    __tablename__ = "empresas"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    razon_social: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )

    ruc: Mapped[str] = mapped_column(
        String(11),
        unique=True,
        nullable=False
    )

    moneda_base: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        server_default="PEN"
    )

    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    usuarios = relationship(
        "Usuario",
        back_populates="empresa"
    )

    roles = relationship(
        "Rol",
        back_populates="empresa"
    )
