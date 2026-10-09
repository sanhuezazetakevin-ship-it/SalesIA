"""Esquema de salida de probabilidades descriptivas (sin predicción ML)."""
from datetime import date
from pydantic import BaseModel, Field


class PeriodoProbabilidades(BaseModel):
    fecha_inicio: date
    fecha_fin: date


class ConteosProbabilidades(BaseModel):
    importe_alto: int = Field(ge=0)
    pagado: int = Field(ge=0)
    importe_alto_y_pagado: int = Field(ge=0)


class EstadoPagoProbabilidad(BaseModel):
    estado: str
    frecuencia_absoluta: int = Field(ge=0)
    probabilidad: str | None


class AnalyticsProbabilidadesResponse(BaseModel):
    periodo: PeriodoProbabilidades
    criterio_estado: str
    zona_horaria: str
    moneda: str
    total_observaciones: int = Field(ge=0)
    umbral_importe_alto: str
    criterio_importe_alto: str
    conteos: ConteosProbabilidades
    variable_aleatoria_estado_pago: list[EstadoPagoProbabilidad]
    probabilidad_pagado: str | None
    probabilidad_importe_alto: str | None
    probabilidad_conjunta_alto_y_pagado: str | None
    probabilidad_pagado_dado_alto: str | None
    bayes_importe_alto_dado_pagado: str | None
