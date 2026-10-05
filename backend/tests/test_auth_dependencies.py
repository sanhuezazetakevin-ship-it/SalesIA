
"""
SalesIA Enterprise
FASE 05-A.5-B

Pruebas HTTP de dependencias de autenticación.
No utiliza PostgreSQL ni modifica datos persistentes.
"""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_current_user,
    get_current_active_user,
)
from app.database.connection import get_db
from app.services.session_service import SesionInvalidaError


@pytest.fixture
def entorno_auth(monkeypatch):
    app = FastAPI()

    db_ficticia = Mock()
    validar_mock = Mock()

    # Sustituimos la función consultada por get_current_user.
    monkeypatch.setattr(
        "app.api.dependencies.validar_sesion",
        validar_mock,
    )

    def obtener_db_ficticia():
        yield db_ficticia

    app.dependency_overrides[get_db] = obtener_db_ficticia

    @app.get("/test/auth")
    def ruta_autenticada(
        usuario=Depends(get_current_user),
    ):
        return {
            "usuario_id": usuario.id,
            "empresa_id": usuario.empresa_id,
        }

    @app.get("/test/active")
    def ruta_activa(
        usuario=Depends(get_current_active_user),
    ):
        return {
            "usuario_id": usuario.id,
            "activo": usuario.activo,
        }

    with TestClient(app) as client:
        yield client, validar_mock, db_ficticia

    app.dependency_overrides.clear()


def test_sin_token_retorna_401(entorno_auth):
    client, validar_mock, _ = entorno_auth

    response = client.get("/test/auth")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    validar_mock.assert_not_called()


def test_token_invalido_retorna_401(entorno_auth):
    client, validar_mock, _ = entorno_auth

    validar_mock.side_effect = SesionInvalidaError(
        "Token inválido."
    )

    response = client.get(
        "/test/auth",
        headers={"Authorization": "Bearer token-invalido"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_sesion_revocada_retorna_401(entorno_auth):
    client, validar_mock, _ = entorno_auth

    validar_mock.side_effect = SesionInvalidaError(
        "La sesión fue revocada."
    )

    response = client.get(
        "/test/auth",
        headers={"Authorization": "Bearer token-revocado"},
    )

    assert response.status_code == 401


def test_usuario_autenticado_retorna_200(entorno_auth):
    client, validar_mock, db_ficticia = entorno_auth

    validar_mock.return_value = SimpleNamespace(
        id=25,
        empresa_id=8,
        activo=True,
    )

    response = client.get(
        "/test/auth",
        headers={"Authorization": "Bearer token-valido"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "usuario_id": 25,
        "empresa_id": 8,
    }

    validar_mock.assert_called_once_with(
        db_ficticia,
        access_token="token-valido",
    )


def test_usuario_inactivo_retorna_403(entorno_auth):
    client, validar_mock, _ = entorno_auth

    validar_mock.return_value = SimpleNamespace(
        id=25,
        empresa_id=8,
        activo=False,
    )

    response = client.get(
        "/test/active",
        headers={"Authorization": "Bearer token-valido"},
    )

    assert response.status_code == 403


def test_usuario_activo_retorna_200(entorno_auth):
    client, validar_mock, _ = entorno_auth

    validar_mock.return_value = SimpleNamespace(
        id=25,
        empresa_id=8,
        activo=True,
    )

    response = client.get(
        "/test/active",
        headers={"Authorization": "Bearer token-valido"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "usuario_id": 25,
        "activo": True,
    }
