"""
SalesIA Enterprise
FASE 08-D.2

Contratos HTTP y de servicio para ventas.
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


EstadoVenta = Literal[
    "REGISTRADA",
    "CONFIRMADA",
    "CANCELADA",
]

EstadoPagoVenta = Literal[
    "PENDIENTE",
    "PARCIAL",
    "PAGADO",
]


class VentaDesdePedidoCreate(BaseModel):
    """
    El frontend no envia importes ni datos empresariales.

    El pedido determina:
    - empresa
    - cliente
    - detalles
    - precios
    - impuestos
    - totales
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    observaciones: str | None = Field(
        default=None,
        max_length=500,
    )


class VentaDetalleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    venta_id: int
    producto_id: int

    descripcion: str

    cantidad: Decimal
    precio_unitario: Decimal
    descuento: Decimal

    subtotal: Decimal
    impuesto: Decimal
    total: Decimal

    tasa_impuesto: Decimal | None


class VentaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int

    pedido_id: int | None
    cliente_id: int
    usuario_id: int

    codigo: str

    estado: EstadoVenta
    estado_pago: EstadoPagoVenta

    subtotal: Decimal
    impuesto_total: Decimal
    total: Decimal

    observaciones: str | None

    created_at: datetime
    updated_at: datetime


class VentaConDetallesResponse(VentaResponse):
    detalles: list[VentaDetalleResponse]


class VentaListadoResponse(BaseModel):
    total: int = Field(ge=0)
    pagina: int = Field(ge=1)
    limite: int = Field(ge=1)

    ventas: list[VentaResponse]