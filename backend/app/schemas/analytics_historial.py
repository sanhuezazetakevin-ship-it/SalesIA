"""Contrato HTTP del historial analítico."""
from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field

class PeriodoAnalisis(BaseModel):
    fecha_inicio: date
    fecha_fin: date

class CrearEstadisticoRequest(PeriodoAnalisis):
    nombre: str = Field(min_length=1, max_length=150)

class CrearProbabilidadRequest(PeriodoAnalisis):
    umbral_importe: Decimal = Field(default=Decimal('100.00'), ge=0, allow_inf_nan=False)

class AnalisisGuardado(BaseModel):
    id: int
    tipo: Literal['estadistico', 'probabilidad']
    empresa_id: int
    estado: str
    resultados: dict
    created_at: str | None = None

class HistorialListado(BaseModel):
    tipo: Literal['estadistico', 'probabilidad']
    items: list[dict]
    limite: int
