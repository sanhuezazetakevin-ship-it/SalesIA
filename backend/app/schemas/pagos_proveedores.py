"""Contratos HTTP SalesIA fase 09-E.4. Montos monetarios exactos."""
from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class PagoProveedorCrear(BaseModel):
    model_config = ConfigDict(extra='forbid')
    orden_id: int = Field(gt=0)
    monto: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    medio_pago: str = Field(min_length=1, max_length=40)
    codigo: str | None = Field(default=None, min_length=1, max_length=50)
    referencia_externa: str | None = Field(default=None, min_length=1, max_length=120)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=120)

class PagoProveedorRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    orden_id: int
    usuario_id: int
    codigo: str
    monto: Decimal
    medio_pago: str
    estado: Literal['REGISTRADO', 'ANULADO']
    referencia_externa: str | None
    idempotency_key: str | None
    created_at: datetime

class PagoProveedorPagina(BaseModel):
    items: list[PagoProveedorRespuesta]
    total: int
    pagina: int
    limite: int
