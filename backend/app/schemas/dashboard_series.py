"""Contrato público para la serie temporal del dashboard SalesIA."""
from datetime import date
from typing import Literal
from pydantic import BaseModel, Field

class PuntoSerie(BaseModel):
    fecha: date
    cantidad_ventas: int = Field(ge=0)
    total_ventas: str

class SerieVentasResponse(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    agrupacion: Literal['dia', 'mes']
    criterio_estado: Literal['CONFIRMADA'] = 'CONFIRMADA'
    zona_horaria: Literal['UTC'] = 'UTC'
    moneda: Literal['PEN'] = 'PEN'
    puntos: list[PuntoSerie]
