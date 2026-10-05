
"""
SalesIA Enterprise — FASE 08-C.1

Contratos empresariales para pedidos.

El cliente no puede imponer:
- empresa_id
- usuario_id
- precios unitarios
- subtotal
- impuesto
- total
- estado del pedido

Estos valores son responsabilidad del backend.
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


EstadoPedido = Literal[
    "BORRADOR",
    "CONFIRMADO",
    "COMPLETADO",
    "CANCELADO",
]


class PedidoDetalleCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    producto_id: int = Field(gt=0)

    cantidad: Decimal = Field(
        gt=Decimal("0"),
        max_digits=14,
        decimal_places=3,
        allow_inf_nan=False,
    )

    descuento: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0"),
        max_digits=14,
        decimal_places=2,
        allow_inf_nan=False,
    )


class PedidoCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    cliente_id: int = Field(gt=0)

    detalles: list[PedidoDetalleCreate] = Field(
        min_length=1,
        max_length=100,
    )

    observaciones: str | None = Field(
        default=None,
        max_length=500,
    )

    @field_validator("observaciones")
    @classmethod
    def validar_observaciones(cls, valor):
        if valor is not None and not valor.strip():
            raise ValueError(
                "Las observaciones no pueden estar vacias."
            )
        return valor

    @model_validator(mode="after")
    def validar_productos_repetidos(self):
        identificadores = [
            detalle.producto_id
            for detalle in self.detalles
        ]

        if len(identificadores) != len(set(identificadores)):
            raise ValueError(
                "Un producto no puede repetirse en el pedido."
            )

        return self


class PedidoDetalleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    pedido_id: int
    producto_id: int

    descripcion: str

    cantidad: Decimal
    precio_unitario: Decimal
    descuento: Decimal

    subtotal: Decimal
    impuesto: Decimal
    total: Decimal


class PedidoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    cliente_id: int
    usuario_id: int

    codigo: str
    estado: EstadoPedido

    subtotal: Decimal
    impuesto_total: Decimal
    total: Decimal

    observaciones: str | None

    created_at: datetime
    updated_at: datetime


class PedidoConDetallesResponse(PedidoResponse):
    detalles: list[PedidoDetalleResponse]


class PedidoListadoResponse(BaseModel):
    total: int = Field(ge=0)
    pagina: int = Field(ge=1)
    limite: int = Field(ge=1)
    pedidos: list[PedidoResponse]
