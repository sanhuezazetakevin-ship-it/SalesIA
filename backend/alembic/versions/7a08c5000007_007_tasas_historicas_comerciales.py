
"""
007_tasas_historicas_comerciales

Conserva la tasa tributaria aplicada por detalle comercial.

Revision ID: 7a08c5000007
Revises: c728eec2618a

Migracion aditiva. No modifica importes ni reconstruye
tasas historicas desconocidas.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7a08c5000007"

down_revision: Union[str, Sequence[str], None] = (
    "c728eec2618a"
)

branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pedido_detalles",
        sa.Column(
            "tasa_impuesto",
            sa.Numeric(precision=7, scale=4),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        "ck_pedido_detalle_tasa_impuesto",
        "pedido_detalles",
        "tasa_impuesto IS NULL OR "
        "(tasa_impuesto >= 0 AND tasa_impuesto <= 100)",
    )

    op.add_column(
        "venta_detalles",
        sa.Column(
            "tasa_impuesto",
            sa.Numeric(precision=7, scale=4),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        "ck_venta_detalle_tasa_impuesto",
        "venta_detalles",
        "tasa_impuesto IS NULL OR "
        "(tasa_impuesto >= 0 AND tasa_impuesto <= 100)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_venta_detalle_tasa_impuesto",
        "venta_detalles",
        type_="check",
    )

    op.drop_column(
        "venta_detalles",
        "tasa_impuesto",
    )

    op.drop_constraint(
        "ck_pedido_detalle_tasa_impuesto",
        "pedido_detalles",
        type_="check",
    )

    op.drop_column(
        "pedido_detalles",
        "tasa_impuesto",
    )
