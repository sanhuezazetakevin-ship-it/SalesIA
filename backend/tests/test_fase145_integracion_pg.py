"""FASE 14.5: integración PostgreSQL de TESTING. No modifica la BD principal.

Utiliza la fixture db_testing existente (transacción con SAVEPOINT revertida).
Las identidades simuladas solo se utilizan para aislar la lógica de negocio por tenant;
NO constituyen pruebas de autenticación JWT real.
"""
from types import SimpleNamespace
from uuid import uuid4
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.empresa import Empresa
from app.models.notificacion_empresarial import NotificacionEmpresarial
from app.api.dependencies import get_current_active_user
from app.database.connection import get_db
from app.api.routes.notificaciones145 import router
from app.services import notificaciones145_service as service


def _nueva_empresa(db):
    # Evitar conflictos con RUC de empresas existentes; rollback al terminar.
    for _ in range(5):
        ruc = str(uuid4().int % (10**11)).zfill(11)
        if db.scalar(select(Empresa.id).where(Empresa.ruc == ruc)) is None:
            e = Empresa(razon_social='Pruebas aislamiento fase145', ruc=ruc)
            db.add(e)
            db.flush()
            return e
    pytest.fail('No se pudo reservar un RUC único para pruebas')


@pytest.fixture
def empresas_testing(db_testing):
    a, b = _nueva_empresa(db_testing), _nueva_empresa(db_testing)
    db_testing.flush()
    return a.id, b.id


@pytest.fixture
def cliente_http(db_testing, empresas_testing, monkeypatch):
    """HTTP real + dependencias simuladas; PostgreSQL de testing real."""
    empresa_a, empresa_b = empresas_testing
    identidades = {910001: empresa_a, 910002: empresa_b}

    def obtener_empresa(db, usuario_id, permiso='ventas.ver'):
        assert db is db_testing
        assert permiso == 'ventas.ver'
        return identidades[usuario_id]

    monkeypatch.setattr(service, '_empresa', obtener_empresa)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db_testing
    app.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace(id=910001, activo=True)
    with TestClient(app) as client:
        yield client, app, identidades
    app.dependency_overrides.clear()


def _insertar(db, empresa_id, clave):
    n = NotificacionEmpresarial(
        empresa_id=empresa_id, clave=clave, codigo='STOCK_BAJO',
        titulo='Alerta de prueba', descripcion='Stock bajo, ejemplo', nivel='ADVERTENCIA',
    )
    db.add(n)
    db.flush()
    return n


def test_bd_testing_aislamiento_lectura_y_escritura(cliente_http, db_testing, empresas_testing):
    client, app, ids = cliente_http
    empresa_a, empresa_b = empresas_testing
    alerta_a = _insertar(db_testing, empresa_a, 'fase145:a')
    alerta_b = _insertar(db_testing, empresa_b, 'fase145:b')
    resp_a = client.get('/api/mejoras/notificaciones-persistentes')
    assert resp_a.status_code == 200, resp_a.text
    codigos_a = {n['id'] for n in resp_a.json()['items']}
    assert alerta_a.id in codigos_a and alerta_b.id not in codigos_a

    # Empresa A no puede modificar la notificación B: respuesta indistinguible de un ID inexistente.
    resp_ajena = client.patch(f'/api/mejoras/notificaciones-persistentes/{alerta_b.id}/leida')
    assert resp_ajena.status_code == 404, resp_ajena.text
    db_testing.refresh(alerta_b)
    assert alerta_b.leida is False

    # Leer una notificación propia y persistirlo.
    resp_prop = client.patch(f'/api/mejoras/notificaciones-persistentes/{alerta_a.id}/leida')
    assert resp_prop.status_code == 200, resp_prop.text
    assert resp_prop.json()['leida'] is True
    db_testing.refresh(alerta_a)
    assert alerta_a.leida is True

    # Otra empresa ve su información, no la de A.
    app.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace(id=910002, activo=True)
    resp_b = client.get('/api/mejoras/notificaciones-persistentes?solo_no_leidas=true')
    assert resp_b.status_code == 200, resp_b.text
    codigos_b = {n['id'] for n in resp_b.json()['items']}
    assert alerta_b.id in codigos_b and alerta_a.id not in codigos_b


def test_bd_testing_restriccion_clave_por_empresa(db_testing, empresas_testing):
    empresa_a, empresa_b = empresas_testing
    _insertar(db_testing, empresa_a, 'fase145:misma-clave')
    _insertar(db_testing, empresa_b, 'fase145:misma-clave')
    db_testing.flush()
    assert db_testing.scalar(select(NotificacionEmpresarial.id).where(
        NotificacionEmpresarial.empresa_id == empresa_a,
        NotificacionEmpresarial.clave == 'fase145:misma-clave')) is not None
    assert db_testing.scalar(select(NotificacionEmpresarial.id).where(
        NotificacionEmpresarial.empresa_id == empresa_b,
        NotificacionEmpresarial.clave == 'fase145:misma-clave')) is not None


def test_http_ruta_requiere_credenciales_sin_override():
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        resp = client.get('/api/mejoras/notificaciones-persistentes')
    assert resp.status_code == 401, resp.text


def test_http_rechaza_limite_invalido(cliente_http):
    client, _, _ = cliente_http
    resp = client.get('/api/mejoras/notificaciones-persistentes?limite=101')
    assert resp.status_code == 422, resp.text
