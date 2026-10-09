"""
SalesIA Enterprise
FASE 08-D.12

Pruebas HTTP empresariales de ventas.
"""

import pytest

from fastapi.testclient import TestClient

from app.main import app
from app.database.connection import get_db

from app.models.pedido import Pedido
from app.models.venta import Venta
from app.models.reserva_stock import ReservaStock
from app.models.inventario import Inventario

from app.services.pedido_service import (
    confirmar_pedido,
)

from tests.test_pedido_http import (
    preparar_empresa_pedidos_http,
    autenticar_pedidos_http,
    crear_pedido_http,
)

from tests.test_pedido_service import contar


@pytest.fixture
def cliente_ventas_http(db_testing):
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


def preparar_escenario_venta_http(
    cliente,
    db,
):
    escenario = preparar_empresa_pedidos_http(
        db,
        permisos=(
            "pedidos.ver",
            "pedidos.crear",
            "pedidos.confirmar",
            "ventas.ver",
            "ventas.crear",
        ),
    )

    headers = autenticar_pedidos_http(
        cliente,
        escenario,
    )

    pedido = crear_pedido_http(
        cliente,
        escenario,
        headers,
    )

    confirmacion = cliente.post(
        f"/api/pedidos/{pedido['id']}/confirmar",
        headers=headers,
    )

    assert confirmacion.status_code == 200, confirmacion.text

    return escenario, headers, pedido


def test_ventas_requieren_autenticacion(
    cliente_ventas_http,
):
    assert cliente_ventas_http.get(
        "/api/ventas"
    ).status_code == 401

    assert cliente_ventas_http.get(
        "/api/ventas/1"
    ).status_code == 401

    assert cliente_ventas_http.post(
        "/api/ventas/desde-pedido/1",
        json={},
    ).status_code == 401


def test_crear_venta_desde_pedido_http(
    cliente_ventas_http,
    db_testing,
):
    escenario, headers, pedido = (
        preparar_escenario_venta_http(
            cliente_ventas_http,
            db_testing,
        )
    )

    respuesta = cliente_ventas_http.post(
        f"/api/ventas/desde-pedido/{pedido['id']}",
        headers=headers,
        json={
            "observaciones": "Venta HTTP Testing",
        },
    )

    assert respuesta.status_code == 201, respuesta.text

    datos = respuesta.json()

    assert datos["pedido_id"] == pedido["id"]
    assert datos["estado"] == "REGISTRADA"
    assert datos["estado_pago"] == "PENDIENTE"

    assert len(datos["detalles"]) == 1

    db_testing.expire_all()

    pedido_db = db_testing.get(
        Pedido,
        pedido["id"],
    )

    assert pedido_db.estado == "COMPLETADO"


def test_venta_no_consume_reserva_http(
    cliente_ventas_http,
    db_testing,
):
    escenario, headers, pedido = (
        preparar_escenario_venta_http(
            cliente_ventas_http,
            db_testing,
        )
    )

    respuesta = cliente_ventas_http.post(
        f"/api/ventas/desde-pedido/{pedido['id']}",
        headers=headers,
        json={},
    )

    assert respuesta.status_code == 201

    db_testing.expire_all()

    reserva = db_testing.query(
        ReservaStock
    ).filter(
        ReservaStock.pedido_id == pedido["id"]
    ).first()

    assert reserva is not None
    assert reserva.estado == "ACTIVA"

    inventario = db_testing.get(
        Inventario,
        escenario["inventario_id"],
    )

    assert str(
        inventario.cantidad_disponible
    ) == "10.000"


def test_no_permite_doble_venta_http(
    cliente_ventas_http,
    db_testing,
):
    escenario, headers, pedido = (
        preparar_escenario_venta_http(
            cliente_ventas_http,
            db_testing,
        )
    )

    primera = cliente_ventas_http.post(
        f"/api/ventas/desde-pedido/{pedido['id']}",
        headers=headers,
        json={},
    )

    assert primera.status_code == 201

    segunda = cliente_ventas_http.post(
        f"/api/ventas/desde-pedido/{pedido['id']}",
        headers=headers,
        json={},
    )

    assert segunda.status_code == 409

    assert contar(
        db_testing,
        Venta,
        escenario["empresa_id"],
    ) == 1


def test_listar_ventas_http(
    cliente_ventas_http,
    db_testing,
):
    escenario, headers, pedido = (
        preparar_escenario_venta_http(
            cliente_ventas_http,
            db_testing,
        )
    )

    creada = cliente_ventas_http.post(
        f"/api/ventas/desde-pedido/{pedido['id']}",
        headers=headers,
        json={},
    )

    assert creada.status_code == 201

    respuesta = cliente_ventas_http.get(
        "/api/ventas",
        headers=headers,
    )

    assert respuesta.status_code == 200

    datos = respuesta.json()

    assert datos["total"] == 1
    assert datos["ventas"][0]["id"] == creada.json()["id"]


def test_obtener_venta_http(
    cliente_ventas_http,
    db_testing,
):
    escenario, headers, pedido = (
        preparar_escenario_venta_http(
            cliente_ventas_http,
            db_testing,
        )
    )

    creada = cliente_ventas_http.post(
        f"/api/ventas/desde-pedido/{pedido['id']}",
        headers=headers,
        json={},
    )

    venta_id = creada.json()["id"]

    respuesta = cliente_ventas_http.get(
        f"/api/ventas/{venta_id}",
        headers=headers,
    )

    assert respuesta.status_code == 200

    datos = respuesta.json()

    assert datos["id"] == venta_id
    assert len(datos["detalles"]) == 1


def test_usuario_sin_permiso_ventas_recibe_403(
    cliente_ventas_http,
    db_testing,
):
    escenario = preparar_empresa_pedidos_http(
        db_testing,
        permisos=(
            "pedidos.crear",
            "pedidos.confirmar",
        ),
    )

    headers = autenticar_pedidos_http(
        cliente_ventas_http,
        escenario,
    )

    pedido = crear_pedido_http(
        cliente_ventas_http,
        escenario,
        headers,
    )

    confirmar_pedido(
        db_testing,
        usuario_id=escenario["usuario"].id,
        pedido_id=pedido["id"],
    )

    respuesta = cliente_ventas_http.post(
        f"/api/ventas/desde-pedido/{pedido['id']}",
        headers=headers,
        json={},
    )

    assert respuesta.status_code == 403


def test_venta_otra_empresa_no_visible_http(
    cliente_ventas_http,
    db_testing,
):
    escenario_a, headers_a, _ = (
        preparar_escenario_venta_http(
            cliente_ventas_http,
            db_testing,
        )
    )

    escenario_b, headers_b, pedido_b = (
        preparar_escenario_venta_http(
            cliente_ventas_http,
            db_testing,
        )
    )

    creada_b = cliente_ventas_http.post(
        f"/api/ventas/desde-pedido/{pedido_b['id']}",
        headers=headers_b,
        json={},
    )

    assert creada_b.status_code == 201

    venta_b_id = creada_b.json()["id"]

    consulta = cliente_ventas_http.get(
        f"/api/ventas/{venta_b_id}",
        headers=headers_a,
    )

    assert consulta.status_code == 404

    listado = cliente_ventas_http.get(
        "/api/ventas",
        headers=headers_a,
    )

    assert listado.status_code == 200
    assert listado.json()["total"] == 0


def test_ventas_validacion_422(
    cliente_ventas_http,
    db_testing,
):
    escenario, headers, pedido = (
        preparar_escenario_venta_http(
            cliente_ventas_http,
            db_testing,
        )
    )

    respuesta = cliente_ventas_http.get(
        "/api/ventas",
        headers=headers,
        params={
            "limite": 101,
        },
    )

    assert respuesta.status_code == 422

    respuesta = cliente_ventas_http.post(
        f"/api/ventas/desde-pedido/{pedido['id']}",
        headers=headers,
        json={
            "empresa_id": 999999,
        },
    )

    assert respuesta.status_code == 422