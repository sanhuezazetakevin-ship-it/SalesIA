"""SalesIA FASE 08-G.4: metadata OpenAPI; no cambia rutas ni comportamiento HTTP."""
from copy import deepcopy
from fastapi.openapi.utils import get_openapi

# Matriz documental: revisar periódicamente contra los servicios RBAC reales.
PERMISOS = {
    ("post", "/api/invitaciones"): "usuarios.crear",
    ("get", "/api/usuarios/pendientes"): "usuarios.autorizar",
    ("post", "/api/usuarios/{usuario_id}/aprobar"): "usuarios.autorizar",
    ("get", "/api/roles"): "roles.ver",
    ("get", "/api/roles/{rol_id}/permisos"): "roles.ver",
    ("post", "/api/roles/asignaciones"): "roles.asignar",
    ("delete", "/api/roles/asignaciones"): "roles.revocar",
    ("post", "/api/clientes"): "clientes.crear",
    ("get", "/api/clientes"): "clientes.ver",
    ("get", "/api/clientes/{cliente_id}"): "clientes.ver",
    ("patch", "/api/clientes/{cliente_id}"): "clientes.editar",
    ("delete", "/api/clientes/{cliente_id}"): "clientes.editar",
    ("post", "/api/categorias"): "categorias.crear",
    ("get", "/api/categorias"): "categorias.ver",
    ("get", "/api/categorias/{categoria_id}"): "categorias.ver",
    ("patch", "/api/categorias/{categoria_id}"): "categorias.editar",
    ("delete", "/api/categorias/{categoria_id}"): "categorias.editar",
    ("post", "/api/productos"): "productos.crear",
    ("get", "/api/productos"): "productos.ver",
    ("get", "/api/productos/{producto_id}"): "productos.ver",
    ("patch", "/api/productos/{producto_id}"): "productos.editar",
    ("delete", "/api/productos/{producto_id}"): "productos.editar",
    ("post", "/api/pedidos"): "pedidos.crear",
    ("get", "/api/pedidos"): "pedidos.ver",
    ("get", "/api/pedidos/{pedido_id}"): "pedidos.ver",
    ("post", "/api/pedidos/{pedido_id}/confirmar"): "pedidos.confirmar",
    ("post", "/api/pedidos/{pedido_id}/cancelar"): "pedidos.cancelar",
    ("post", "/api/ventas/desde-pedido/{pedido_id}"): "ventas.crear",
    ("get", "/api/ventas"): "ventas.ver",
    ("get", "/api/ventas/{venta_id}"): "ventas.ver",
    ("post", "/api/pagos/ventas/{venta_id}"): "pagos.registrar",
    ("get", "/api/pagos/ventas/{venta_id}/resumen"): "pagos.ver",
    ("post", "/api/pagos/{pago_id}/anular"): "pagos.anular",
    ("post", "/api/entregas/ventas/{venta_id}/confirmar"): "entregas.confirmar",
    ("get", "/api/entregas/ventas/{venta_id}"): "entregas.ver",
    ("get", "/api/entregas/{entrega_id}"): "entregas.ver",
}

# Respuestas documentadas: no implican que todo controlador las emita realmente.
ERRORES = {
    "401": "Credenciales ausentes, inválidas o sesión vencida/revocada.",
    "403": "Usuario autenticado sin permiso suficiente.",
    "404": "Recurso inexistente o no visible en la empresa actual.",
    "409": "Conflicto de estado o duplicidad de operación.",
}

RUTAS_CON_RECURSO = {
    ("get", "/api/roles/{rol_id}/permisos"),
    ("post", "/api/usuarios/{usuario_id}/aprobar"),
    ("get", "/api/clientes/{cliente_id}"),
    ("patch", "/api/clientes/{cliente_id}"),
    ("delete", "/api/clientes/{cliente_id}"),
    ("get", "/api/categorias/{categoria_id}"),
    ("patch", "/api/categorias/{categoria_id}"),
    ("delete", "/api/categorias/{categoria_id}"),
    ("get", "/api/productos/{producto_id}"),
    ("patch", "/api/productos/{producto_id}"),
    ("delete", "/api/productos/{producto_id}"),
    ("get", "/api/pedidos/{pedido_id}"),
    ("post", "/api/pedidos/{pedido_id}/confirmar"),
    ("post", "/api/pedidos/{pedido_id}/cancelar"),
    ("post", "/api/ventas/desde-pedido/{pedido_id}"),
    ("get", "/api/ventas/{venta_id}"),
    ("post", "/api/pagos/ventas/{venta_id}"),
    ("get", "/api/pagos/ventas/{venta_id}/resumen"),
    ("post", "/api/pagos/{pago_id}/anular"),
    ("post", "/api/entregas/ventas/{venta_id}/confirmar"),
    ("get", "/api/entregas/ventas/{venta_id}"),
    ("get", "/api/entregas/{entrega_id}"),
}
RUTAS_CON_CONFLICTO = {
    ("post", "/api/pedidos/{pedido_id}/confirmar"),
    ("post", "/api/pedidos/{pedido_id}/cancelar"),
    ("post", "/api/ventas/desde-pedido/{pedido_id}"),
    ("post", "/api/pagos/ventas/{venta_id}"),
    ("post", "/api/pagos/{pago_id}/anular"),
    ("post", "/api/entregas/ventas/{venta_id}/confirmar"),
}


def enriquecer_esquema(esquema: dict) -> dict:
    """Devuelve copia enriquecida, sin mutar el OpenAPI original."""
    resultado = deepcopy(esquema)
    for ruta, metodos in resultado.get("paths", {}).items():
        for metodo, operacion in metodos.items():
            if metodo.lower() not in {"get", "post", "patch", "put", "delete"}:
                continue
            clave = (metodo.lower(), ruta)
            respuestas = operacion.setdefault("responses", {})
            if operacion.get("security"):
                for codigo in ("401", "403"):
                    respuestas.setdefault(codigo, {"description": ERRORES[codigo]})
            if clave in RUTAS_CON_RECURSO:
                respuestas.setdefault("404", {"description": ERRORES["404"]})
            if clave in RUTAS_CON_CONFLICTO:
                respuestas.setdefault("409", {"description": ERRORES["409"]})
            permiso = PERMISOS.get(clave)
            if permiso:
                operacion["x-required-permission"] = permiso
                operacion["x-permission-documentation-status"] = "pendiente_validacion_en_rutas"
    return resultado


def instalar_openapi_contratos(app):
    """Instalar DESPUÉS de registrar routers. Idempotente."""
    if getattr(app.state, "salesia_openapi_instalado", False):
        return
    def custom_openapi():
        if app.openapi_schema is None:
            original = get_openapi(
                title=app.title,
                version=app.version,
                description=app.description,
                routes=app.routes,
                openapi_version=app.openapi_version,
            )
            app.openapi_schema = enriquecer_esquema(original)
        return app.openapi_schema
    app.openapi_schema = None
    app.openapi = custom_openapi
    app.state.salesia_openapi_instalado = True
