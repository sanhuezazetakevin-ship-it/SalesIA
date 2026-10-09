"""Checks del contrato HTTP, sin conectar con base principal ni Testing."""
from decimal import Decimal
from fastapi import FastAPI
from pydantic import ValidationError
import pytest
from app.api.routes.analytics_historial import router
from app.schemas.analytics_historial import CrearEstadisticoRequest, CrearProbabilidadRequest


def test_cuatro_operaciones_registradas():
    app = FastAPI()
    app.include_router(router)
    paths = app.openapi()['paths']
    raiz = '/api/analytics/historial'
    assert 'post' in paths[raiz + '/estadisticos']
    assert 'post' in paths[raiz + '/probabilidades']
    assert 'get' in paths[raiz]
    assert 'get' in paths[raiz + '/{tipo}/{analisis_id}']


def test_no_acepta_resultados_desde_frontend():
    modelo = CrearEstadisticoRequest.model_validate({'nombre': 'Enero',
        'fecha_inicio': '2026-01-01', 'fecha_fin': '2026-01-31',
        'resultados': {'inventado': True}})
    assert 'resultados' not in modelo.model_dump()


@pytest.mark.parametrize('umbral', ['-1', 'Infinity', 'NaN'])
def test_umbral_invalido(umbral):
    with pytest.raises(ValidationError):
        CrearProbabilidadRequest.model_validate({'fecha_inicio':'2026-01-01',
            'fecha_fin':'2026-01-31', 'umbral_importe':umbral})


def test_umbral_decimal():
    dato = CrearProbabilidadRequest.model_validate({'fecha_inicio':'2026-01-01',
        'fecha_fin':'2026-01-31', 'umbral_importe':'100.25'})
    assert dato.umbral_importe == Decimal('100.25')
