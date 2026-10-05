
"""
SalesIA Enterprise
FASE 05-A.5-C

Pruebas HTTP del contexto multiempresa.
No utiliza PostgreSQL.
"""

from types import SimpleNamespace

import pytest

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_current_user,
    get_current_empresa_id,
)


@pytest.fixture
def entorno_multiempresa():
    app = FastAPI()

    @app.get("/test/mi-empresa")
    def consultar_mi_empresa(
        empresa_id: int = Depends(get_current_empresa_id),
    ):
        return {"empresa_id": empresa_id}

    @app.get("/test/empresas/{empresa_solicitada}")
    def consultar_empresa(
        empresa_solicitada: int,
        empresa_id: int = Depends(get_current_empresa_id),
    ):
        if empresa_solicitada != empresa_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No autorizado para esta empresa.",
            )

        return {"empresa_id": empresa_id}

    with TestClient(app) as client:
        yield app, client

    app.dependency_overrides.clear()


def autenticar_como(app, usuario_id: int, empresa_id: int):
    """
    Simula un usuario cuya identidad ya fue validada.

    La dependencia multiempresa original permanece activa.
    """

    app.dependency_overrides[get_current_user] = lambda: (
        SimpleNamespace(
            id=usuario_id,
            empresa_id=empresa_id,
            activo=True,
        )
    )


def test_usuario_empresa_a(entorno_multiempresa):
    app, client = entorno_multiempresa

    autenticar_como(app, usuario_id=10, empresa_id=1)

    response = client.get("/test/mi-empresa")

    assert response.status_code == 200
    assert response.json() == {"empresa_id": 1}


def test_usuario_empresa_b(entorno_multiempresa):
    app, client = entorno_multiempresa

    autenticar_como(app, usuario_id=20, empresa_id=2)

    response = client.get("/test/mi-empresa")

    assert response.status_code == 200
    assert response.json() == {"empresa_id": 2}


def test_empresa_ajena_retorna_403(entorno_multiempresa):
    app, client = entorno_multiempresa

    autenticar_como(app, usuario_id=10, empresa_id=1)

    response = client.get("/test/empresas/2")

    assert response.status_code == 403


def test_empresa_propia_permitida(entorno_multiempresa):
    app, client = entorno_multiempresa

    autenticar_como(app, usuario_id=10, empresa_id=1)

    response = client.get("/test/empresas/1")

    assert response.status_code == 200
    assert response.json() == {"empresa_id": 1}


def test_parametro_cliente_no_cambia_empresa(entorno_multiempresa):
    app, client = entorno_multiempresa

    autenticar_como(app, usuario_id=10, empresa_id=1)

    response = client.get("/test/mi-empresa?empresa_id=2")

    assert response.status_code == 200
    assert response.json() == {"empresa_id": 1}


def test_sin_autenticacion_retorna_401(entorno_multiempresa):
    _, client = entorno_multiempresa

    response = client.get("/test/mi-empresa")

    assert response.status_code == 401
