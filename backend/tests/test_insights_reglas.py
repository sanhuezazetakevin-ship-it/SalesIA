import pytest
from app.services.insights_service import generar_reglas, InsightsError


def test_insight_sin_ventas():
    resultado = generar_reglas('estadistico', {'contenido': {
        'cantidad_ventas': 0, 'total_ventas': '0.00',
        'ticket_promedio': None, 'mediana_ventas': None}})
    assert resultado[0]['datos_soporte']['regla'] == 'SIN_VENTAS'


def test_insight_ticket_con_evidencia():
    resultado = generar_reglas('estadistico', {'contenido': {
        'cantidad_ventas': 2, 'total_ventas': '300.00',
        'ticket_promedio': '150.00', 'mediana_ventas': '150.00'}})
    assert resultado[0]['datos_soporte']['media'] == '150.00'
    assert resultado[0]['prioridad'] == 'BAJA'


def test_insight_frecuencia_pagado():
    resultado = generar_reglas('probabilidad', {
        'total_observaciones': 10, 'conteos': {'pagado': 2}, 'probabilidad_pagado': '0.2000'})
    assert resultado[0]['prioridad'] == 'MEDIA'
    assert resultado[0]['datos_soporte']['ventas_pagadas'] == 2


def test_insight_probabilidad_muestra_vacia():
    r = generar_reglas('probabilidad', {
        'total_observaciones': 0, 'conteos': {'pagado': 0}, 'probabilidad_pagado': None})
    assert r[0]['datos_soporte']['regla'] == 'MUESTRA_VACIA'


@pytest.mark.parametrize('tipo,datos', [
    ('estadistico', {'contenido': {'cantidad_ventas': -1, 'total_ventas': '10'}}),
    ('estadistico', {'contenido': {'cantidad_ventas': 1, 'total_ventas': 'NaN'}}),
    ('probabilidad', {'total_observaciones': 3, 'conteos': {'pagado': 4}, 'probabilidad_pagado': '1.1'}),
    ('probabilidad', {'total_observaciones': 1, 'conteos': {'pagado': 1}, 'probabilidad_pagado': 'Infinity'}),
    ('probabilidad', {'total_observaciones': 0, 'conteos': {'pagado': 0}, 'probabilidad_pagado': '0.0'}),
])
def test_rechazo_datos_inconsistentes(tipo, datos):
    with pytest.raises(InsightsError):
        generar_reglas(tipo, datos)


def test_no_inventar_resultados():
    with pytest.raises(InsightsError):
        generar_reglas('estadistico', {})
