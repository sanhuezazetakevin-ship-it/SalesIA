from datetime import date
from pydantic import BaseModel, Field

class PeriodoResumen(BaseModel):
    fecha_inicio: date
    fecha_fin: date

class AnalyticsResumenResponse(BaseModel):
    periodo: PeriodoResumen
    moneda: str = 'PEN'
    criterio_estado: str = 'CONFIRMADA'
    zona_horaria: str = 'UTC'
    cantidad_ventas: int = Field(ge=0)
    total_ventas: str
    ticket_promedio: str | None
    mediana_ventas: str | None
