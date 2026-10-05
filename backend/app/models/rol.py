
from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Rol(Base):
    __tablename__ = "roles"

    __table_args__ = (
        UniqueConstraint(
            "empresa_id",
            "nombre",
            name="uq_rol_empresa_nombre"
        ),
        UniqueConstraint(
            "id",
            "empresa_id",
            name="uq_rol_empresa"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    empresa_id: Mapped[int] = mapped_column(
        ForeignKey("empresas.id"),
        nullable=False
    )

    nombre: Mapped[str] = mapped_column(
        String(80),
        nullable=False
    )

    descripcion: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    empresa = relationship(
        "Empresa",
        back_populates="roles"
    )

    usuarios = relationship(
        "Usuario",
        secondary="usuarios_roles",
        back_populates="roles"
    )

    permisos = relationship(
        "Permiso",
        secondary="roles_permisos",
        back_populates="roles"
    )
