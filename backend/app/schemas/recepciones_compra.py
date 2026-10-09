"""Contratos API de recepciones. Cantidades decimales exactas."""
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

class RecepcionLineaCrear(BaseModel):
    model_config = ConfigDict(extra='forbid')
    orden_detalle_id: int = Field(gt=0)
    cantidad_recibida: Decimal = Field(gt=0, max_digits=14, decimal_places=3)

class RecepcionCrear(BaseModel):
    model_config = ConfigDict(extra='forbid')
    orden_id: int = Field(gt=0)
    detalles: list[RecepcionLineaCrear] = Field(min_length=1, max_length=200)
    codigo: str | None = Field(default=None, min_length=1, max_length=50)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=120)

class RecepcionLineaRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    orden_detalle_id: int
    cantidad_recibida: Decimal

class RecepcionRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    orden_id: int
    usuario_id: int
    codigo: str
    idempotency_key: str | None
    estado: str
    created_at: datetime
    confirmed_at: datetime
    detalles: list[RecepcionLineaRespuesta]

class RecepcionPagina(BaseModel):
    items: list[RecepcionRespuesta]
    total: int
    pagina: int
    limite: int
