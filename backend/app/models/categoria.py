
from sqlalchemy import (
    Boolean, ForeignKey, Integer, String, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Categoria(Base):
    __tablename__ = "categorias"

    __table_args__ = (
        UniqueConstraint(
            "empresa_id", "nombre",
            name="uq_categoria_empresa_nombre"
        ),
        UniqueConstraint(
            "id", "empresa_id",
            name="uq_categoria_id_empresa"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    empresa_id: Mapped[int] = mapped_column(
        ForeignKey("empresas.id"), nullable=False
    )

    nombre: Mapped[str] = mapped_column(
        String(120), nullable=False
    )

    descripcion: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
