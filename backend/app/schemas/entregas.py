"""SalesIA Enterprise - FASE 08-F.4: esquemas de entregas."""
from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class EntregaConfirmar(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    observaciones: str | None = Field(default=None, max_length=500)


class EntregaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    venta_id: int
    responsable_id: int
    codigo: str
    estado: Literal["PENDIENTE", "CONFIRMADA", "CANCELADA"]
    observaciones: str | None
    fecha_confirmacion: datetime | None
    created_at: datetime
    updated_at: datetime


class MovimientoEntregaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    producto_id: int
    inventario_id: int
    entrega_id: int | None
    tipo_movimiento: Literal["ENTRADA", "SALIDA", "AJUSTE"]
    cantidad_delta: Decimal
    motivo: str
    referencia: str | None
    created_at: datetime


class EntregaConMovimientosResponse(EntregaResponse):
    movimientos: list[MovimientoEntregaResponse]
