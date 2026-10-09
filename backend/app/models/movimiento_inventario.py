
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKeyConstraint,
    Index, Integer, Numeric, String, func
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"

    __table_args__ = (
        ForeignKeyConstraint(
            ["inventario_id", "producto_id", "empresa_id"],
            [
                "inventario.id",
                "inventario.producto_id",
                "inventario.empresa_id"
            ],
            name="fk_movimiento_inventario_empresa"
        ),
        ForeignKeyConstraint(
            ["entrega_id", "empresa_id"],
            ["entregas.id", "entregas.empresa_id"],
            name="fk_movimiento_entrega_empresa",
        ),

        ForeignKeyConstraint(
            ["recepcion_compra_id", "empresa_id"],
            ["recepciones_compra.id", "recepciones_compra.empresa_id"],
            name="fk_movimiento_recepcion_compra_empresa",
        ),
        CheckConstraint(
            "tipo_movimiento IN ('ENTRADA', 'SALIDA', 'AJUSTE')",
            name="ck_movimiento_tipo"
        ),
        CheckConstraint(
            "cantidad_delta <> 0",
            name="ck_movimiento_cantidad_no_cero"
        ),
        Index(
            "ix_movimientos_empresa_fecha",
            "empresa_id", "created_at"
        ),
        Index(
            "ix_movimientos_producto_fecha",
            "producto_id", "created_at"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    empresa_id: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    producto_id: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    inventario_id: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    tipo_movimiento: Mapped[str] = mapped_column(
        String(20), nullable=False
    )

    cantidad_delta: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False
    )

    motivo: Mapped[str] = mapped_column(
        String(255), nullable=False
    )

    referencia: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    entrega_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
)
    # FASE 09: referencia a entrada por compra; entrega_id permanece intacto.
    recepcion_compra_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
