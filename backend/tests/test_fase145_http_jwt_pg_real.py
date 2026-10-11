"""FASE 14.5 — JWT real + RBAC real + PostgreSQL aislado.

Los datos se crean bajo la fixture db_testing (rollback exterior). No requiere
cuentas reales, secretos impresos ni desactivar dependencias de autenticación.
"""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.dependencies import get_current_user, get_current_active_user
from app.api.routes.notificaciones145 import router as notificaciones_router
from app.core.security import create_access_token
from app.database.connection import get_db
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.permiso import Permiso
from app.models.sesion import Sesion
from app.models.notificacion_empresarial import NotificacionEmpresarial


def _identidad(db, empresa_id, con_permiso):
    sufijo = uuid4().hex
    rol = Rol(empresa_id=empresa_id, nombre='TEST_' + sufijo[:18])
    u = Usuario(empresa_id=empresa_id, nombre='Prueba HTTP real',
                email=f'fase145-{sufijo}@example.invalid',
                password_hash='NO_ES_UN_PASSWORD_REAL', activo=True)
    db.add_all([rol, u])
    db.flush()
    u.roles.append(rol)
    if con_permiso:
        permiso = db.scalar(select(Permiso).where(Permiso.codigo == 'ventas.ver'))
        if permiso is None:
            permiso = Permiso(codigo='ventas.ver', descripcion='Prueba')
            db.add(permiso)
            db.flush()
        rol.permisos.append(permiso)
    db.flush()
    sesion = Sesion(usuario_id=u.id, empresa_id=empresa_id,
                    token_hash=sha256(uuid4().bytes).hexdigest(),
                    fecha_expiracion=datetime.now(timezone.utc) + timedelta(hours=1),
                    revocada=False)
    db.add(sesion)
    db.flush()
    token = create_access_token(usuario_id=u.id, empresa_id=empresa_id, sesion_id=sesion.id)
    return u, sesion, token


def _empresa(db):
    e = Empresa(razon_social='Testing JWT Fase14.5', ruc=str(uuid4().int % 10**11).zfill(11))
    db.add(e)
    db.flush()
    return e


@pytest.fixture
def escenario(db_testing):
    a, b = _empresa(db_testing), _empresa(db_testing)
    usuario_a, sesion_a, token_a = _identidad(db_testing, a.id, True)
    _, _, token_sin_permiso = _identidad(db_testing, a.id, False)
    _, _, token_b = _identidad(db_testing, b.id, True)
    alerta_a = NotificacionEmpresarial(empresa_id=a.id, clave='jwt:' + uuid4().hex,
        codigo='STOCK_BAJO', titulo='Solo A', descripcion='Prueba A', nivel='ADVERTENCIA')
    alerta_b = NotificacionEmpresarial(empresa_id=b.id, clave='jwt:' + uuid4().hex,
        codigo='STOCK_BAJO', titulo='Solo B', descripcion='Prueba B', nivel='ADVERTENCIA')
    db_testing.add_all([alerta_a, alerta_b])
    db_testing.flush()
    app = FastAPI()
    app.include_router(notificaciones_router)
    # Se sustituye SOLO la conexión: JWT, RBAC y sesiones siguen siendo reales.
    assert get_current_user not in app.dependency_overrides
    assert get_current_active_user not in app.dependency_overrides
    app.dependency_overrides[get_db] = lambda: db_testing
    with TestClient(app) as client:
        yield client, db_testing, sesion_a, token_a, token_sin_permiso, token_b, alerta_a.id, alerta_b.id
    app.dependency_overrides.clear()


def _headers(token):
    return {'Authorization': f'Bearer {token}'}


def test_anonimo_y_token_invalido_rechazados(escenario):
    client, *_ = escenario
    ruta = '/api/mejoras/notificaciones-persistentes'
    assert client.get(ruta).status_code == 401
    assert client.get(ruta, headers=_headers('no-es-jwt')).status_code == 401


def test_jwt_real_y_rbac_real(escenario):
    client, _, _, token_a, token_sin_permiso, _, id_a, id_b = escenario
    ruta = '/api/mejoras/notificaciones-persistentes'
    ok = client.get(ruta, headers=_headers(token_a))
    assert ok.status_code == 200, ok.text
    ids = {n['id'] for n in ok.json()['items']}
    assert id_a in ids and id_b not in ids
    denegado = client.get(ruta, headers=_headers(token_sin_permiso))
    assert denegado.status_code == 403, denegado.text


def test_aislamiento_http_entre_empresas(escenario):
    client, _, _, token_a, _, token_b, id_a, id_b = escenario
    base = '/api/mejoras/notificaciones-persistentes'
    assert client.patch(f'{base}/{id_b}/leida', headers=_headers(token_a)).status_code == 404
    assert client.patch(f'{base}/{id_a}/leida', headers=_headers(token_b)).status_code == 404
    respuesta_b = client.get(base, headers=_headers(token_b))
    assert respuesta_b.status_code == 200, respuesta_b.text
    ids_b = {n['id'] for n in respuesta_b.json()['items']}
    assert id_b in ids_b and id_a not in ids_b


def test_revocacion_invalida_jwt_vigente(escenario):
    client, db, sesion, token_a, *_ = escenario
    base = '/api/mejoras/notificaciones-persistentes'
    assert client.get(base, headers=_headers(token_a)).status_code == 200
    sesion.revocada = True
    db.flush()
    assert client.get(base, headers=_headers(token_a)).status_code == 401


# FASE 14.5 — comprobaciones adicionales de seguridad y latencia autenticada.

def test_parametros_invalidos_autenticado(escenario):
    client, _, _, token_a, *_ = escenario
    base = '/api/mejoras/notificaciones-persistentes'
    for limite in ('0', '101', 'invalido'):
        response = client.get(f'{base}?limite={limite}', headers=_headers(token_a))
        assert response.status_code == 422, (limite, response.status_code, response.text)


def test_respuesta_no_expone_token_ni_hash(escenario):
    client, db, _, token_a, *_ = escenario
    response = client.get('/api/mejoras/notificaciones-persistentes', headers=_headers(token_a))
    assert response.status_code == 200, response.text
    contenido = response.text.lower()
    assert token_a not in response.text
    assert 'password_hash' not in contenido
    assert 'token_hash' not in contenido
    assert 'jwt_secret' not in contenido
    assert 'database_url' not in contenido


def test_repeticion_listado_no_duplica_alertas(escenario):
    client, _, _, token_a, _, _, id_a, _ = escenario
    base = '/api/mejoras/notificaciones-persistentes'
    respuestas = [client.get(base, headers=_headers(token_a)) for _ in range(3)]
    assert all(r.status_code == 200 for r in respuestas)
    listas = [[x['id'] for x in r.json()['items']] for r in respuestas]
    assert all(id_a in ids for ids in listas)
    assert listas[0] == listas[1] == listas[2]
    assert len(listas[0]) == len(set(listas[0]))


def test_linea_base_latencia_autenticada(escenario):
    """Medición informativa, sin SLA ficticio; ejecutar pytest con -s para ver ms.

    Mide TestClient + JWT + permisos + consulta a PostgreSQL de testing.
    No representa carga simultánea, red real ni producción.
    """
    from statistics import median
    from time import perf_counter
    client, _, _, token_a, *_ = escenario
    ruta = '/api/mejoras/notificaciones-persistentes?limite=20'
    headers = _headers(token_a)
    # Calentamiento fuera de las muestras.
    previo = client.get(ruta, headers=headers)
    assert previo.status_code == 200, previo.text
    muestras = []
    for _ in range(12):
        inicio = perf_counter()
        response = client.get(ruta, headers=headers)
        muestras.append((perf_counter() - inicio) * 1000)
        assert response.status_code == 200, response.text
    ordenadas = sorted(muestras)
    p95 = ordenadas[max(0, int((len(ordenadas) * 0.95 + 0.999999)) - 1)]
    print(f'\nFASE14.5 HTTP autenticado: n={len(muestras)}, mediana={median(muestras):.2f} ms, p95_aprox={p95:.2f} ms, max={max(muestras):.2f} ms')
