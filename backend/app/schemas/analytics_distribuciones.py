from datetime import date
from typing import Literal
from pydantic import BaseModel, Field

class PeriodoDistribucion(BaseModel):
    fecha_inicio: date
    fecha_fin: date

class FilaDistribucion(BaseModel):
    categoria: str | None = None
    desde: str | None = None
    hasta: str | None = None
    frecuencia_absoluta: int = Field(ge=0)
    frecuencia_relativa: str

class AnalyticsDistribucionesResponse(BaseModel):
    periodo: PeriodoDistribucion
    variable: Literal['importe_venta','estado_pago']
    tipo_variable: Literal['cuantitativa_continua','cualitativa_nominal']
    criterio_estado: str
    zona_horaria: str
    total_observaciones: int = Field(ge=0)
    distribucion: list[FilaDistribucion]
