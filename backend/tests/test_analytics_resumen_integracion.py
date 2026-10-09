"""MVP-01-C: integración HTTP + JWT firmado + PostgreSQL Testing.

Nunca usa DATABASE_URL: todas las escrituras de prueba pasan por db_testing
(transacción externa con rollback del tests/conftest.py existente).
"""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.database.connection import get_db
from app.core.security import create_access_token
from app.models.sesion import Sesion
from app.models.venta import Venta
from tests.test_venta_service import preparar_venta
from tests.test_pedido_service import _escenario_confirmacion

URL = '/api/analytics/resumen'
PARAMS = {'fecha_inicio': '2026-10-01', 'fecha_fin': '2026-10-31'}


@pytest.fixture
def cliente_analytics(db_testing):
    previos = app.dependency_overrides.copy()
    def solo_testing():
        yield db_testing
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = solo_testing
    try:
        with TestClient(app) as cliente:
            yield cliente
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previos)


def autenticar(db, e):
    sesion = Sesion(
        usuario_id=e['usuario_id'], empresa_id=e['empresa_id'],
        token_hash=uuid4().hex + uuid4().hex,
        fecha_expiracion=datetime(2027, 1, 1, tzinfo=timezone.utc),
        revocada=False,
    )
    db.add(sesion)
    db.commit()
    token = create_access_token(usuario_id=e['usuario_id'],
                                empresa_id=e['empresa_id'], sesion_id=sesion.id)
    return {'Authorization': 'Bearer ' + token}


def datos_venta(db, e, *, total, estado='CONFIRMADA', fecha='2026-10-10T12:00:00+00:00'):
    # Se preparan cliente/usuario reales a través del helper ya probado.
    # El pedido_id es opcional en el modelo, lo que permite datos analíticos mínimos.
    from app.models.cliente import Cliente
    cliente_id = db.scalar(select(Cliente.id).where(Cliente.empresa_id == e['empresa_id']).limit(1))
    assert cliente_id is not None
    valor = Decimal(total)
    venta = Venta(
        empresa_id=e['empresa_id'], cliente_id=cliente_id,
        usuario_id=e['usuario_id'], pedido_id=None,
        codigo='AN-' + uuid4().hex[:28], estado=estado,
        estado_pago='PENDIENTE', subtotal=valor,
        impuesto_total=Decimal('0.00'), total=valor,
        created_at=datetime.fromisoformat(fecha),
    )
    db.add(venta)
    db.commit()
    return venta


def escenario(db):
    e, _ = preparar_venta(db)
    return e


def test_sin_jwt_rechazado(cliente_analytics):
    respuesta = cliente_analytics.get(URL, params=PARAMS)
    assert respuesta.status_code == 401, respuesta.text


def test_jwt_real_resumen_vacio(cliente_analytics, db_testing):
    e = escenario(db_testing)
    respuesta = cliente_analytics.get(URL, params=PARAMS, headers=autenticar(db_testing, e))
    assert respuesta.status_code == 200, respuesta.text
    body = respuesta.json()
    assert body['cantidad_ventas'] == 0
    assert body['total_ventas'] == '0.00'
    assert body['ticket_promedio'] is None
    assert body['mediana_ventas'] is None


def test_calculo_integracion_y_estados(cliente_analytics, db_testing):
    e = escenario(db_testing)
    datos_venta(db_testing, e, total='10.00')
    datos_venta(db_testing, e, total='20.00')
    datos_venta(db_testing, e, total='60.00')
    datos_venta(db_testing, e, total='999.00', estado='CANCELADA')
    datos_venta(db_testing, e, total='888.00', estado='REGISTRADA')
    respuesta = cliente_analytics.get(URL, params=PARAMS, headers=autenticar(db_testing, e))
    assert respuesta.status_code == 200, respuesta.text
    body = respuesta.json()
    assert body['cantidad_ventas'] == 3
    assert body['total_ventas'] == '90.00'
    assert body['ticket_promedio'] == '30.00'
    assert body['mediana_ventas'] == '20.00'
    assert body['criterio_estado'] == 'CONFIRMADA'
    assert body['zona_horaria'] == 'UTC'


def test_limites_periodo_inclusivo(cliente_analytics, db_testing):
    e = escenario(db_testing)
    datos_venta(db_testing, e, total='10.00', fecha='2026-10-01T00:00:00+00:00')
    datos_venta(db_testing, e, total='20.00', fecha='2026-10-31T23:59:59+00:00')
    datos_venta(db_testing, e, total='30.00', fecha='2026-11-01T00:00:00+00:00')
    respuesta = cliente_analytics.get(URL, params=PARAMS, headers=autenticar(db_testing, e))
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()['total_ventas'] == '30.00'


def test_aislamiento_multiempresa(cliente_analytics, db_testing):
    a = escenario(db_testing)
    b = escenario(db_testing)
    datos_venta(db_testing, a, total='15.00')
    datos_venta(db_testing, b, total='90.00')
    respuesta = cliente_analytics.get(URL, params=PARAMS, headers=autenticar(db_testing, a))
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()['total_ventas'] == '15.00'
    assert respuesta.json()['cantidad_ventas'] == 1


def test_sin_permiso_ventas_ver(cliente_analytics, db_testing):
    e = _escenario_confirmacion(db_testing, permisos=('pedidos.crear',))
    respuesta = cliente_analytics.get(URL, params=PARAMS, headers=autenticar(db_testing, e))
    assert respuesta.status_code == 403, respuesta.text


def test_periodo_invalido(cliente_analytics, db_testing):
    e = escenario(db_testing)
    respuesta = cliente_analytics.get(URL, params={
        'fecha_inicio': '2026-11-01', 'fecha_fin': '2026-10-01'},
        headers=autenticar(db_testing, e))
    assert respuesta.status_code == 422, respuesta.text
