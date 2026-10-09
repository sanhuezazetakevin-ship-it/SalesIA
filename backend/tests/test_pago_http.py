"""SalesIA Enterprise - FASE 08-E.4: tests HTTP para pagos."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.connection import get_db
from tests.test_pedido_http import (
    preparar_empresa_pedidos_http, autenticar_pedidos_http, crear_pedido_http,
)


@pytest.fixture
def cliente_pagos_http(db_testing):
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


def preparar_venta_http(cliente, db, *, permisos_extra=("pagos.ver", "pagos.registrar", "pagos.anular")):
    permisos = (
        "pedidos.ver", "pedidos.crear", "pedidos.confirmar",
        "ventas.ver", "ventas.crear",
    ) + tuple(permisos_extra)
    escenario = preparar_empresa_pedidos_http(db, permisos=permisos)
    headers = autenticar_pedidos_http(cliente, escenario)
    pedido = crear_pedido_http(cliente, escenario, headers)
    confirmacion = cliente.post(f"/api/pedidos/{pedido['id']}/confirmar", headers=headers)
    assert confirmacion.status_code == 200, confirmacion.text
    venta = cliente.post(f"/api/ventas/desde-pedido/{pedido['id']}", headers=headers, json={})
    assert venta.status_code == 201, venta.text
    return escenario, headers, venta.json()


def test_pagos_requieren_autenticacion(cliente_pagos_http):
    assert cliente_pagos_http.post("/api/pagos/ventas/1", json={"monto": "10.00", "medio_pago": "YAPE"}).status_code == 401
    assert cliente_pagos_http.get("/api/pagos/ventas/1/resumen").status_code == 401
    assert cliente_pagos_http.post("/api/pagos/1/anular", json={"motivo": "Error de registro"}).status_code == 401


def test_registrar_pago_y_resumen_http(cliente_pagos_http, db_testing):
    _, headers, venta = preparar_venta_http(cliente_pagos_http, db_testing)
    importe = "10.00"
    respuesta = cliente_pagos_http.post(
        f"/api/pagos/ventas/{venta['id']}", headers=headers,
        json={"monto": importe, "medio_pago": "YAPE", "referencia_externa": "TEST-HTTP"},
    )
    assert respuesta.status_code == 201, respuesta.text
    pago = respuesta.json()
    assert pago["estado"] == "REGISTRADO"
    assert pago["venta_id"] == venta["id"]
    resumen = cliente_pagos_http.get(f"/api/pagos/ventas/{venta['id']}/resumen", headers=headers)
    assert resumen.status_code == 200, resumen.text
    datos = resumen.json()
    assert datos["estado_pago"] == "PARCIAL"
    assert float(datos["total_pagado"]) == 10
    assert len(datos["pagos"]) == 1


def test_pago_completo_http(cliente_pagos_http, db_testing):
    _, headers, venta = preparar_venta_http(cliente_pagos_http, db_testing)
    respuesta = cliente_pagos_http.post(
        f"/api/pagos/ventas/{venta['id']}", headers=headers,
        json={"monto": venta["total"], "medio_pago": "TRANSFERENCIA"},
    )
    assert respuesta.status_code == 201, respuesta.text
    resumen = cliente_pagos_http.get(f"/api/pagos/ventas/{venta['id']}/resumen", headers=headers)
    assert resumen.status_code == 200, resumen.text
    assert resumen.json()["estado_pago"] == "PAGADO"
    assert float(resumen.json()["saldo_pendiente"]) == 0


def test_sobrepago_rechazado_http(cliente_pagos_http, db_testing):
    _, headers, venta = preparar_venta_http(cliente_pagos_http, db_testing)
    from decimal import Decimal
    exceso = str(Decimal(str(venta["total"])) + Decimal("0.01"))
    respuesta = cliente_pagos_http.post(
        f"/api/pagos/ventas/{venta['id']}", headers=headers,
        json={"monto": exceso, "medio_pago": "EFECTIVO"},
    )
    assert respuesta.status_code == 409, respuesta.text


def test_anulacion_http(cliente_pagos_http, db_testing):
    _, headers, venta = preparar_venta_http(cliente_pagos_http, db_testing)
    creado = cliente_pagos_http.post(
        f"/api/pagos/ventas/{venta['id']}", headers=headers,
        json={"monto": "10.00", "medio_pago": "PLIN"},
    )
    assert creado.status_code == 201, creado.text
    anulado = cliente_pagos_http.post(
        f"/api/pagos/{creado.json()['id']}/anular", headers=headers,
        json={"motivo": "Pago ingresado por error"},
    )
    assert anulado.status_code == 200, anulado.text
    assert anulado.json()["estado"] == "ANULADO"
    resumen = cliente_pagos_http.get(f"/api/pagos/ventas/{venta['id']}/resumen", headers=headers)
    assert resumen.json()["estado_pago"] == "PENDIENTE"
    assert float(resumen.json()["total_pagado"]) == 0


def test_usuario_sin_permiso_http(cliente_pagos_http, db_testing):
    _, headers, venta = preparar_venta_http(cliente_pagos_http, db_testing, permisos_extra=())
    respuesta = cliente_pagos_http.post(
        f"/api/pagos/ventas/{venta['id']}", headers=headers,
        json={"monto": "10.00", "medio_pago": "YAPE"},
    )
    assert respuesta.status_code == 403, respuesta.text
    respuesta = cliente_pagos_http.get(f"/api/pagos/ventas/{venta['id']}/resumen", headers=headers)
    assert respuesta.status_code == 403, respuesta.text


def test_multiempresa_no_expone_venta_http(cliente_pagos_http, db_testing):
    _, headers_a, _ = preparar_venta_http(cliente_pagos_http, db_testing)
    _, _, venta_b = preparar_venta_http(cliente_pagos_http, db_testing)
    consulta = cliente_pagos_http.get(f"/api/pagos/ventas/{venta_b['id']}/resumen", headers=headers_a)
    assert consulta.status_code == 404, consulta.text
    intento = cliente_pagos_http.post(
        f"/api/pagos/ventas/{venta_b['id']}", headers=headers_a,
        json={"monto": "10.00", "medio_pago": "YAPE"},
    )
    assert intento.status_code == 404, intento.text


def test_payload_invalido_http(cliente_pagos_http, db_testing):
    _, headers, venta = preparar_venta_http(cliente_pagos_http, db_testing)
    for datos in (
        {"monto": "-1.00", "medio_pago": "YAPE"},
        {"monto": "1.001", "medio_pago": "YAPE"},
        {"monto": "1.00", "medio_pago": "NO_EXISTE"},
        {"monto": "1.00", "medio_pago": "YAPE", "empresa_id": 99},
    ):
        respuesta = cliente_pagos_http.post(f"/api/pagos/ventas/{venta['id']}", headers=headers, json=datos)
        assert respuesta.status_code == 422, respuesta.text


# FASE 08-E.6 — Pruebas de idempotencia en HTTP
def test_http_reintento_idempotente(cliente_pagos_http, db_testing):
    _, headers, venta = preparar_venta_http(cliente_pagos_http, db_testing)
    headers = {**headers, "Idempotency-Key": "reintento-http-00000001"}
    ruta = f"/api/pagos/ventas/{venta['id']}"
    datos = {"monto": "10.00", "medio_pago": "YAPE"}
    primera = cliente_pagos_http.post(ruta, headers=headers, json=datos)
    segunda = cliente_pagos_http.post(ruta, headers=headers, json=datos)
    assert primera.status_code == 201, primera.text
    assert segunda.status_code == 201, segunda.text
    assert primera.json()["id"] == segunda.json()["id"]
    resumen = cliente_pagos_http.get(ruta + "/resumen", headers=headers)
    assert len(resumen.json()["pagos"]) == 1


def test_http_clave_reutilizada_payload_distinto(cliente_pagos_http, db_testing):
    _, headers, venta = preparar_venta_http(cliente_pagos_http, db_testing)
    headers = {**headers, "Idempotency-Key": "reutilizacion-http-0001"}
    ruta = f"/api/pagos/ventas/{venta['id']}"
    primera = cliente_pagos_http.post(ruta, headers=headers,
                                       json={"monto": "10.00", "medio_pago": "YAPE"})
    segunda = cliente_pagos_http.post(ruta, headers=headers,
                                       json={"monto": "15.00", "medio_pago": "YAPE"})
    assert primera.status_code == 201, primera.text
    assert segunda.status_code == 409, segunda.text


def test_http_clave_invalida(cliente_pagos_http, db_testing):
    _, headers, venta = preparar_venta_http(cliente_pagos_http, db_testing)
    headers = {**headers, "Idempotency-Key": "corta"}
    respuesta = cliente_pagos_http.post(f"/api/pagos/ventas/{venta['id']}",
                                        headers=headers,
                                        json={"monto": "5.00", "medio_pago": "YAPE"})
    assert respuesta.status_code == 400, respuesta.text
