"""SalesIA Enterprise - FASE 08-F.4: pruebas HTTP con DB testing aislada."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.connection import get_db
from tests.test_pago_http import preparar_venta_http
from app.models.inventario import Inventario
from app.models.reserva_stock import ReservaStock
from sqlalchemy import select
from decimal import Decimal


@pytest.fixture
def cliente_entregas_http(db_testing):
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


def escenario(cliente, db, *, permisos_extra=("entregas.ver", "entregas.confirmar")):
    return preparar_venta_http(cliente, db, permisos_extra=permisos_extra)


def test_autenticacion_entregas(cliente_entregas_http):
    assert cliente_entregas_http.post("/api/entregas/ventas/1/confirmar", json={}).status_code == 401
    assert cliente_entregas_http.get("/api/entregas/ventas/1").status_code == 401
    assert cliente_entregas_http.get("/api/entregas/1").status_code == 401


def test_confirmar_y_consultar_entrega_http(cliente_entregas_http, db_testing):
    e, headers, venta = escenario(cliente_entregas_http, db_testing)
    r = cliente_entregas_http.post(f"/api/entregas/ventas/{venta['id']}/confirmar", headers=headers,
                                   json={"observaciones": "Entrega completa Testing"})
    assert r.status_code == 201, r.text
    entrega = r.json()
    assert entrega["estado"] == "CONFIRMADA"
    assert entrega["venta_id"] == venta["id"]
    assert len(entrega["movimientos"]) == 1
    assert Decimal(str(entrega["movimientos"][0]["cantidad_delta"])) == Decimal("-2.000")
    for url in (f"/api/entregas/{entrega['id']}", f"/api/entregas/ventas/{venta['id']}"):
        respuesta = cliente_entregas_http.get(url, headers=headers)
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["id"] == entrega["id"]
    db_testing.expire_all()
    reserva = db_testing.scalar(select(ReservaStock).where(ReservaStock.empresa_id == e["empresa_id"]))
    assert reserva.estado == "CONSUMIDA"
    inventario = db_testing.scalar(select(Inventario).where(Inventario.empresa_id == e["empresa_id"]))
    assert inventario.cantidad_disponible == Decimal("8.000")


def test_entrega_duplicada_409(cliente_entregas_http, db_testing):
    _, headers, venta = escenario(cliente_entregas_http, db_testing)
    url = f"/api/entregas/ventas/{venta['id']}/confirmar"
    assert cliente_entregas_http.post(url, headers=headers, json={}).status_code == 201
    assert cliente_entregas_http.post(url, headers=headers, json={}).status_code == 409


def test_entrega_sin_permiso_403(cliente_entregas_http, db_testing):
    _, headers, venta = escenario(cliente_entregas_http, db_testing, permisos_extra=())
    assert cliente_entregas_http.post(f"/api/entregas/ventas/{venta['id']}/confirmar",
                                    headers=headers, json={}).status_code == 403
    assert cliente_entregas_http.get(f"/api/entregas/ventas/{venta['id']}", headers=headers).status_code == 403


def test_entrega_multiempresa_404(cliente_entregas_http, db_testing):
    _, headers_a, _ = escenario(cliente_entregas_http, db_testing)
    _, headers_b, venta_b = escenario(cliente_entregas_http, db_testing)
    r = cliente_entregas_http.post(f"/api/entregas/ventas/{venta_b['id']}/confirmar",
                                   headers=headers_b, json={})
    assert r.status_code == 201, r.text
    id_b = r.json()["id"]
    assert cliente_entregas_http.get(f"/api/entregas/{id_b}", headers=headers_a).status_code == 404
    assert cliente_entregas_http.get(f"/api/entregas/ventas/{venta_b['id']}", headers=headers_a).status_code == 404
    assert cliente_entregas_http.post(f"/api/entregas/ventas/{venta_b['id']}/confirmar",
                                    headers=headers_a, json={}).status_code == 404


def test_validacion_payload_422(cliente_entregas_http, db_testing):
    _, headers, venta = escenario(cliente_entregas_http, db_testing)
    url = f"/api/entregas/ventas/{venta['id']}/confirmar"
    assert cliente_entregas_http.post(url, headers=headers,
                                    json={"empresa_id": 999}).status_code == 422
    assert cliente_entregas_http.post(url, headers=headers,
                                    json={"observaciones": "x" * 501}).status_code == 422


def test_consulta_sin_entrega_404(cliente_entregas_http, db_testing):
    _, headers, venta = escenario(cliente_entregas_http, db_testing)
    assert cliente_entregas_http.get(f"/api/entregas/ventas/{venta['id']}", headers=headers).status_code == 404
