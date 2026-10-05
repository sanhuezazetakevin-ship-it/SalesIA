
from sqlalchemy import Integer, String

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Permiso(Base):
    __tablename__ = "permisos"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    codigo: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )

    descripcion: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    roles = relationship(
        "Rol",
        secondary="roles_permisos",
        back_populates="permisos"
    )
