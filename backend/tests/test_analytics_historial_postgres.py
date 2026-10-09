"""MVP-01-F.2: sólo db_testing con rollback externo, nunca DATABASE_URL.

Requiere módulos existentes del backend y fixtures de las pruebas Analytics.
No hace TRUNCATE ni elimina registros ajenos.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.analisis_estadistico import AnalisisEstadistico
from app.models.analisis_probabilidad import AnalisisProbabilidad
from app.services.analytics_historial_service import (
    AnalyticsHistorialError, guardar_estadistico, guardar_probabilidad,
    listar_historial, obtener_historial,
)
from tests.test_analytics_resumen_integracion import escenario
from tests.test_pedido_service import _escenario_confirmacion

D1 = date(2026, 10, 1)
D2 = date(2026, 10, 31)


def estadistico(db, e, nombre='Análisis de ventas', resultados=None):
    return guardar_estadistico(
        db, usuario_id=e['usuario_id'], nombre=nombre,
        fecha_inicio=D1, fecha_fin=D2,
        resultados={'media': Decimal('25.50')} if resultados is None else resultados,
    )


def probabilidad(db, e, resultados=None):
    return guardar_probabilidad(
        db, usuario_id=e['usuario_id'], fecha_inicio=D1, fecha_fin=D2,
        umbral_importe='100.00',
        resultados={'probabilidad_pagado': '0.5000',
                    'bayes_importe_alto_dado_pagado': None}
                   if resultados is None else resultados,
    )


def test_estadistico_inserta_y_recupera(db_testing):
    e = escenario(db_testing)
    registro = estadistico(db_testing, e)
    db_testing.commit()  # commit del SAVEPOINT; transacción externa sigue reversible
    encontrado = db_testing.scalar(select(AnalisisEstadistico).where(
        AnalisisEstadistico.id == registro.id))
    assert encontrado is not None
    assert encontrado.empresa_id == e['empresa_id']
    assert encontrado.estado == 'COMPLETADO'
    assert encontrado.fecha_calculo is not None
    assert encontrado.resultados['contenido']['media'] == '25.50'
    assert encontrado.resultados['usuario_ejecutor_id'] == e['usuario_id']


def test_probabilidad_inserta_y_recupera(db_testing):
    e = escenario(db_testing)
    registro = probabilidad(db_testing, e)
    db_testing.commit()
    encontrado = db_testing.scalar(select(AnalisisProbabilidad).where(
        AnalisisProbabilidad.id == registro.id))
    assert encontrado is not None
    assert encontrado.empresa_id == e['empresa_id']
    assert encontrado.estado == 'COMPLETADO'
    assert encontrado.probabilidad == Decimal('0.500000')
    assert encontrado.datos_entrada['usuario_ejecutor_id'] == e['usuario_id']
    assert encontrado.resultados['bayes_importe_alto_dado_pagado'] is None


def test_probabilidad_indefinida_se_guarda_como_null(db_testing):
    e = escenario(db_testing)
    registro = probabilidad(db_testing, e, {'probabilidad_pagado': None})
    db_testing.flush()
    assert registro.probabilidad is None
    assert registro.resultados['probabilidad_pagado'] is None


def test_historial_filtra_por_empresa(db_testing):
    a, b = escenario(db_testing), escenario(db_testing)
    x = estadistico(db_testing, a, nombre='A')
    y = estadistico(db_testing, b, nombre='B')
    px = probabilidad(db_testing, a)
    py = probabilidad(db_testing, b)
    db_testing.flush()
    assert x.id in [r.id for r in listar_historial(db_testing, usuario_id=a['usuario_id'])]
    assert y.id not in [r.id for r in listar_historial(db_testing, usuario_id=a['usuario_id'])]
    ids = [r.id for r in listar_historial(db_testing, usuario_id=a['usuario_id'], tipo='probabilidad')]
    assert px.id in ids and py.id not in ids


def test_obtener_historial_no_revela_registro_ajeno(db_testing):
    a, b = escenario(db_testing), escenario(db_testing)
    xa = estadistico(db_testing, a)
    xb = estadistico(db_testing, b)
    pb = probabilidad(db_testing, b)
    assert obtener_historial(db_testing, usuario_id=a['usuario_id'],
                             tipo='estadistico', analisis_id=xa.id).id == xa.id
    assert obtener_historial(db_testing, usuario_id=a['usuario_id'],
                             tipo='estadistico', analisis_id=xb.id) is None
    assert obtener_historial(db_testing, usuario_id=a['usuario_id'],
                             tipo='probabilidad', analisis_id=pb.id) is None


def test_listado_limite(db_testing):
    e = escenario(db_testing)
    for i in range(3):
        estadistico(db_testing, e, nombre=f'Análisis {i}')
    registros = listar_historial(db_testing, usuario_id=e['usuario_id'], limite=2)
    assert len(registros) == 2
    assert registros[0].id > registros[1].id


def test_sin_permiso_no_puede_guardar_ni_consultar(db_testing):
    e = _escenario_confirmacion(db_testing, permisos=('pedidos.crear',))
    with pytest.raises(AnalyticsHistorialError, match='No autorizado'):
        estadistico(db_testing, e)
    with pytest.raises(AnalyticsHistorialError, match='No autorizado'):
        probabilidad(db_testing, e)
    with pytest.raises(AnalyticsHistorialError, match='No autorizado'):
        listar_historial(db_testing, usuario_id=e['usuario_id'])


def test_constrains_estado_resultados_en_testing(db_testing):
    """La BD, además del servicio, debe impedir COMPLETADO sin resultado."""
    from datetime import datetime, timezone
    from sqlalchemy.exc import IntegrityError

    e = escenario(db_testing)
    with pytest.raises(IntegrityError):
        with db_testing.begin_nested():
            db_testing.add(AnalisisEstadistico(
                empresa_id=e['empresa_id'], nombre='Inválido', tipo_analisis='VENTAS',
                estado='COMPLETADO', fecha_inicio=datetime(2026, 10, 1, tzinfo=timezone.utc),
                fecha_fin=datetime(2026, 10, 31, tzinfo=timezone.utc),
                resultados=None, fecha_calculo=None,
            ))
            db_testing.flush()
    # El SAVEPOINT del caso inválido se revierte; la sesión debe seguir útil.
    assert estadistico(db_testing, e).id is not None
