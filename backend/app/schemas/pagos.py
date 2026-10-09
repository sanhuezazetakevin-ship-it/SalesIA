"""SalesIA Enterprise - FASE 08-E. Contratos del modulo de pagos."""
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MedioPago = Literal["EFECTIVO", "TARJETA", "TRANSFERENCIA", "YAPE", "PLIN", "OTRO"]
EstadoPago = Literal["REGISTRADO", "ANULADO"]


class PagoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    monto: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    medio_pago: MedioPago
    referencia_externa: str | None = Field(default=None, max_length=120)
    observaciones: str | None = Field(default=None, max_length=500)


class PagoAnular(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    motivo: str = Field(min_length=3, max_length=500)


class PagoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    venta_id: int
    registrado_por_id: int
    codigo: str
    monto: Decimal
    medio_pago: MedioPago
    estado: EstadoPago
    referencia_externa: str | None
    observaciones: str | None
    created_at: datetime


class ResumenPagosResponse(BaseModel):
    venta_id: int
    total_venta: Decimal
    total_pagado: Decimal
    saldo_pendiente: Decimal
    estado_pago: Literal["PENDIENTE", "PARCIAL", "PAGADO"]
    pagos: list[PagoResponse]
