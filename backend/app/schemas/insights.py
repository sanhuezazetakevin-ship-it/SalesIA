from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class GenerarInsightsRequest(BaseModel):
    tipo: Literal['estadistico', 'probabilidad']
    analisis_id: int = Field(gt=0)

class CambiarEstadoInsightRequest(BaseModel):
    estado: Literal['REVISADO', 'DESCARTADO']

class InsightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    analisis_estadistico_id: int | None
    analisis_probabilidad_id: int | None
    tipo_insight: str
    prioridad: str
    titulo: str
    descripcion: str
    recomendacion: str | None
    estado: str
    datos_soporte: dict | None
    created_at: datetime
    updated_at: datetime

class InsightsListado(BaseModel):
    items: list[InsightResponse]
    limite: int
