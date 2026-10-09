"""SalesIA Enterprise - FASE 08-G.3-B.

Pruebas HTTP de seguridad usando exclusivamente la fixture db_testing.
No alterar el proyecto principal ni ejecutar contra produccion.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.database.connection import get_db
from app.core.security import decode_token
from app.models.sesion import Sesion
from app.models.usuario import Usuario
from tests.test_pago_http import preparar_venta_http


@pytest.fixture
def cliente_seguridad_http(db_testing):
    def override_get_db():
        yield db_testing

    originales = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as cliente:
            yield cliente
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(originales)


def _ruta_entrega(venta):
    return f"/api/entregas/ventas/{venta['id']}"


def test_sin_token_401_en_operaciones_empresariales(cliente_seguridad_http):
    for metodo, ruta, datos in (
        ("GET", "/api/entregas/1", None),
        ("GET", "/api/entregas/ventas/1", None),
        ("POST", "/api/entregas/ventas/1/confirmar", {}),
        ("GET", "/api/pagos/ventas/1/resumen", None),
        ("POST", "/api/pagos/ventas/1", {"monto": "1.00", "medio_pago": "YAPE"}),
    ):
        respuesta = cliente_seguridad_http.request(metodo, ruta, json=datos)
        assert respuesta.status_code == 401, (metodo, ruta, respuesta.text)


def test_token_malformado_401(cliente_seguridad_http):
    respuesta = cliente_seguridad_http.get(
        "/api/entregas/1", headers={"Authorization": "Bearer token-no-valido"}
    )
    assert respuesta.status_code == 401, respuesta.text


def test_refresh_no_puede_autorizar_endpoint(cliente_seguridad_http, db_testing):
    _, headers, venta = preparar_venta_http(cliente_seguridad_http, db_testing)
    access = headers["Authorization"].split(" ", 1)[1]
    payload = decode_token(access, expected_type="access")
    from app.core.security import create_refresh_token

    refresh = create_refresh_token(
        usuario_id=int(payload["sub"]),
        empresa_id=payload["empresa_id"],
        sesion_id=payload["sid"],
    )
    respuesta = cliente_seguridad_http.get(
        _ruta_entrega(venta), headers={"Authorization": f"Bearer {refresh}"}
    )
    assert respuesta.status_code == 401, respuesta.text


def test_sesion_revocada_401(cliente_seguridad_http, db_testing):
    _, headers, venta = preparar_venta_http(cliente_seguridad_http, db_testing)
    token = headers["Authorization"].split(" ", 1)[1]
    sid = decode_token(token, expected_type="access")["sid"]
    sesion = db_testing.scalar(select(Sesion).where(Sesion.id == sid))
    assert sesion is not None
    sesion.revocada = True
    db_testing.commit()
    respuesta = cliente_seguridad_http.get(_ruta_entrega(venta), headers=headers)
    assert respuesta.status_code == 401, respuesta.text


def test_usuario_inactivo_401(cliente_seguridad_http, db_testing):
    escenario, headers, venta = preparar_venta_http(cliente_seguridad_http, db_testing)
    token = headers["Authorization"].split(" ", 1)[1]
    user_id = int(decode_token(token, expected_type="access")["sub"])
    usuario = db_testing.scalar(select(Usuario).where(Usuario.id == user_id))
    assert usuario is not None
    usuario.activo = False
    db_testing.commit()
    respuesta = cliente_seguridad_http.get(_ruta_entrega(venta), headers=headers)
    assert respuesta.status_code == 401, respuesta.text


def test_sin_permiso_403(cliente_seguridad_http, db_testing):
    _, headers, venta = preparar_venta_http(
        cliente_seguridad_http, db_testing, permisos_extra=()
    )
    lectura = cliente_seguridad_http.get(_ruta_entrega(venta), headers=headers)
    confirmacion = cliente_seguridad_http.post(
        _ruta_entrega(venta) + "/confirmar", headers=headers, json={}
    )
    assert lectura.status_code == 403, lectura.text
    assert confirmacion.status_code == 403, confirmacion.text


def test_aislamiento_multiempresa_404(cliente_seguridad_http, db_testing):
    _, headers_a, _ = preparar_venta_http(
        cliente_seguridad_http, db_testing,
        permisos_extra=("entregas.ver", "entregas.confirmar"),
    )
    _, headers_b, venta_b = preparar_venta_http(
        cliente_seguridad_http, db_testing,
        permisos_extra=("entregas.ver", "entregas.confirmar"),
    )
    confirmado = cliente_seguridad_http.post(
        _ruta_entrega(venta_b) + "/confirmar", headers=headers_b, json={}
    )
    assert confirmado.status_code == 201, confirmado.text
    entrega_id = confirmado.json()["id"]
    assert cliente_seguridad_http.get(
        f"/api/entregas/{entrega_id}", headers=headers_a
    ).status_code == 404
    assert cliente_seguridad_http.get(
        _ruta_entrega(venta_b), headers=headers_a
    ).status_code == 404


def test_usuario_autorizado_puede_consultar_entrega(cliente_seguridad_http, db_testing):
    _, headers, venta = preparar_venta_http(
        cliente_seguridad_http, db_testing,
        permisos_extra=("entregas.ver", "entregas.confirmar"),
    )
    creado = cliente_seguridad_http.post(
        _ruta_entrega(venta) + "/confirmar", headers=headers, json={}
    )
    assert creado.status_code == 201, creado.text
    consulta = cliente_seguridad_http.get(_ruta_entrega(venta), headers=headers)
    assert consulta.status_code == 200, consulta.text
    assert consulta.json()["id"] == creado.json()["id"]
