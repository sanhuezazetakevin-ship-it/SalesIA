"""Verifica documentación OpenAPI sin acceder a PostgreSQL."""
from app.main import app
from app.core.openapi_contracts import PERMISOS, enriquecer_esquema


def test_todos_los_endpoints_esperados_estan_en_openapi():
    esquema = app.openapi()
    for metodo, ruta in PERMISOS:
        assert ruta in esquema["paths"], ruta
        assert metodo in esquema["paths"][ruta], (metodo, ruta)


def test_documentacion_de_autenticacion_y_permisos():
    esquema = app.openapi()
    for (metodo, ruta), permiso in PERMISOS.items():
        operacion = esquema["paths"][ruta][metodo]
        assert operacion.get("security"), (metodo, ruta)
        assert operacion["x-required-permission"] == permiso
        assert {"401", "403"}.issubset(operacion["responses"])


def test_conflictos_y_no_encontrados_documentados():
    esquema = app.openapi()
    assert "409" in esquema["paths"]["/api/entregas/ventas/{venta_id}/confirmar"]["post"]["responses"]
    assert "404" in esquema["paths"]["/api/entregas/{entrega_id}"]["get"]["responses"]


def test_documentacion_idempotente_y_sin_modificar_esquema_fuente():
    esquema = app.openapi()
    assert app.openapi() is esquema
    assert enriquecer_esquema(esquema) == esquema
