
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKeyConstraint,
    Integer, Numeric, UniqueConstraint, func
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Inventario(Base):
    __tablename__ = "inventario"

    __table_args__ = (
        ForeignKeyConstraint(
            ["producto_id", "empresa_id"],
            ["productos.id", "productos.empresa_id"],
            name="fk_inventario_producto_empresa"
        ),
        UniqueConstraint(
            "producto_id", "empresa_id",
            name="uq_inventario_producto_empresa"
        ),
        UniqueConstraint(
            "id", "producto_id", "empresa_id",
            name="uq_inventario_id_producto_empresa"
        ),
        CheckConstraint(
            "cantidad_disponible >= 0",
            name="ck_inventario_cantidad_no_negativa"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    empresa_id: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    producto_id: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    cantidad_disponible: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        nullable=False,
        server_default="0"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
