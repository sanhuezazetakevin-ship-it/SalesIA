
"""
SalesIA Enterprise
FASE 05-D.3

Pruebas HTTP de autenticación con PostgreSQL Testing.

La dependencia get_db se sustituye por db_testing.
No se realizan solicitudes contra DATABASE_URL.
"""

import uuid

import pytest

from fastapi.testclient import TestClient

from app.main import app
from app.database.connection import get_db

from app.core.security import hash_password

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.rol import Rol


PASSWORD_TEST = "ClaveSeguraHTTP#2026"


@pytest.fixture
def cliente_http(db_testing):
    """
    Sustituye la dependencia de base de datos
    exclusivamente durante cada prueba.
    """

    def override_get_db():
        yield db_testing

    # Conservar overrides preexistentes para restaurarlos.
    overrides_originales = app.dependency_overrides.copy()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as cliente:
            yield cliente
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(
            overrides_originales
        )


@pytest.fixture
def usuario_http(db_testing):
    identificador = uuid.uuid4().hex

    empresa = Empresa(
        razon_social=f"Empresa HTTP {identificador[:12]}",
        ruc=str(
            uuid.uuid4().int % 10**11
        ).zfill(11),
        moneda_base="PEN",
        activo=True,
    )

    db_testing.add(empresa)
    db_testing.flush()

    rol = Rol(
        empresa_id=empresa.id,
        nombre="Usuario HTTP Testing",
        descripcion="Rol de pruebas HTTP",
    )

    db_testing.add(rol)
    db_testing.flush()

    usuario = Usuario(
        empresa_id=empresa.id,
        nombre="Usuario HTTP",
        email=f"http-{identificador}@example.com",
        password_hash=hash_password(PASSWORD_TEST),
        activo=True,
    )

    db_testing.add(usuario)
    db_testing.flush()

    usuario.roles.append(rol)
    db_testing.flush()

    return empresa, usuario


def test_login_http_exitoso(
    cliente_http,
    usuario_http,
):
    empresa, usuario = usuario_http

    respuesta = cliente_http.post(
        "/api/auth/login",
        json={
            "email": usuario.email,
            "password": PASSWORD_TEST,
        },
    )

    assert respuesta.status_code == 200, respuesta.text

    datos = respuesta.json()

    assert datos["access_token"]
    assert datos["refresh_token"]
    assert datos["token_type"] == "bearer"
    assert datos["usuario"]["id"] == usuario.id
    assert datos["usuario"]["empresa_id"] == empresa.id


def test_login_http_rechaza_password_incorrecta(
    cliente_http,
    usuario_http,
):
    empresa, usuario = usuario_http

    respuesta = cliente_http.post(
        "/api/auth/login",
        json={
            "email": usuario.email,
            "password": "Incorrecta#123",
        },
    )

    assert respuesta.status_code == 401


def test_login_http_rechaza_empresa_id_externo(
    cliente_http,
    usuario_http,
):
    empresa, usuario = usuario_http

    respuesta = cliente_http.post(
        "/api/auth/login",
        json={
            "email": usuario.email,
            "password": PASSWORD_TEST,
            "empresa_id": empresa.id,
        },
    )

    # LoginRequest tiene extra="forbid".
    assert respuesta.status_code == 422


def test_me_http_requiere_autenticacion(
    cliente_http,
):
    respuesta = cliente_http.get(
        "/api/auth/me"
    )

    assert respuesta.status_code == 401


def test_flujo_http_completo(
    cliente_http,
    usuario_http,
):
    empresa, usuario = usuario_http

    # 1. Login.
    login = cliente_http.post(
        "/api/auth/login",
        json={
            "email": usuario.email,
            "password": PASSWORD_TEST,
        },
    )

    assert login.status_code == 200, login.text

    tokens = login.json()

    headers = {
        "Authorization": (
            f"Bearer {tokens['access_token']}"
        )
    }

    # 2. Consultar usuario autenticado.
    me = cliente_http.get(
        "/api/auth/me",
        headers=headers,
    )

    assert me.status_code == 200, me.text
    assert me.json()["id"] == usuario.id
    assert me.json()["empresa_id"] == empresa.id

    # 3. Renovar sesión.
    refresh = cliente_http.post(
        "/api/auth/refresh",
        json={
            "refresh_token": tokens["refresh_token"],
        },
    )

    assert refresh.status_code == 200, refresh.text

    nuevos_tokens = refresh.json()

    assert nuevos_tokens["access_token"]
    assert nuevos_tokens["refresh_token"]
    assert (
        nuevos_tokens["refresh_token"]
        != tokens["refresh_token"]
    )

    # 4. El refresh anterior no puede reutilizarse.
    refresh_anterior = cliente_http.post(
        "/api/auth/refresh",
        json={
            "refresh_token": tokens["refresh_token"],
        },
    )

    assert refresh_anterior.status_code == 401

    # 5. Cerrar sesión.
    nuevos_headers = {
        "Authorization": (
            f"Bearer {nuevos_tokens['access_token']}"
        )
    }

    logout = cliente_http.post(
        "/api/auth/logout",
        headers=nuevos_headers,
    )

    assert logout.status_code == 200, logout.text

    # 6. La sesión revocada no permite acceder.
    me_revocado = cliente_http.get(
        "/api/auth/me",
        headers=nuevos_headers,
    )

    assert me_revocado.status_code == 401

    # 7. Tampoco permite renovar tokens.
    refresh_revocado = cliente_http.post(
        "/api/auth/refresh",
        json={
            "refresh_token": nuevos_tokens["refresh_token"],
        },
    )

    assert refresh_revocado.status_code == 401
