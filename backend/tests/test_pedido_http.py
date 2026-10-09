"""
SalesIA Enterprise
FASE 08-C.10.1

Pruebas HTTP empresariales de pedidos.

- JWT real y sesion persistida.
- RBAC.
- Aislamiento multiempresa.
- PostgreSQL Testing.
- Creacion, consulta, confirmacion y cancelacion.
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.database.connection import get_db
from app.core.security import hash_password

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.permiso import Permiso
from app.models.cliente import Cliente
from app.models.producto import Producto
from app.models.impuesto import Impuesto
from app.models.inventario import Inventario
from app.models.pedido import Pedido
from app.models.reserva_stock import ReservaStock

from app.models.asociaciones import (
    usuarios_roles,
    roles_permisos,
)


PASSWORD_PEDIDOS_HTTP = "ClavePedidosHTTP#2026"

PERMISOS_PEDIDOS = (
    "pedidos.ver",
    "pedidos.crear",
    "pedidos.confirmar",
    "pedidos.cancelar",
)


@pytest.fixture
def cliente_pedidos_http(db_testing):
    """
    Todas las solicitudes HTTP utilizan exclusivamente
    PostgreSQL Testing.
    """

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


def preparar_empresa_pedidos_http(
    db,
    *,
    permisos=PERMISOS_PEDIDOS,
):
    identificador = uuid4().hex

    empresa = Empresa(
        razon_social=f"Pedidos HTTP {identificador[:12]}",
        ruc=str(
            uuid4().int % 10**11
        ).zfill(11),
        moneda_base="PEN",
        activo=True,
    )

    db.add(empresa)
    db.flush()

    rol = Rol(
        empresa_id=empresa.id,
        nombre=f"PEDIDOS_HTTP_{identificador[:8]}",
        descripcion="Rol temporal HTTP de pedidos",
    )

    db.add(rol)
    db.flush()

    for codigo in permisos:
        permiso = db.scalar(
            select(Permiso).where(
                Permiso.codigo == codigo
            )
        )

        if permiso is None:
            permiso = Permiso(
                codigo=codigo,
                descripcion=f"Permiso temporal: {codigo}",
            )
            db.add(permiso)
            db.flush()

        db.execute(
            roles_permisos.insert().values(
                rol_id=rol.id,
                permiso_id=permiso.id,
            )
        )

    usuario = Usuario(
        empresa_id=empresa.id,
        nombre="Operador Pedidos HTTP",
        email=(
            f"pedidos-http-{identificador}"
            "@example.com"
        ),
        password_hash=hash_password(
            PASSWORD_PEDIDOS_HTTP
        ),
        activo=True,
    )

    db.add(usuario)
    db.flush()

    db.execute(
        usuarios_roles.insert().values(
            usuario_id=usuario.id,
            rol_id=rol.id,
            empresa_id=empresa.id,
        )
    )

    cliente = Cliente(
        empresa_id=empresa.id,
        nombre="Cliente Pedidos HTTP",
        tipo_documento="DNI",
        numero_documento=str(
            uuid4().int % 10**8
        ).zfill(8),
        activo=True,
    )

    producto = Producto(
        empresa_id=empresa.id,
        categoria_id=None,
        sku=f"PED-HTTP-{identificador[:10]}",
        nombre="Producto Pedidos HTTP",
        descripcion="Producto para pruebas HTTP",
        tipo_item="PRODUCTO",
        precio_venta=Decimal("118.00"),
        costo_referencia=Decimal("70.00"),
        controla_stock=True,
        activo=True,
    )

    db.add_all([cliente, producto])
    db.flush()

    impuesto = Impuesto(
        empresa_id=empresa.id,
        codigo="IGV",
        nombre="IGV HTTP",
        tasa=Decimal("18.0000"),
        incluido_en_precio=True,
        activo=True,
    )

    db.add(impuesto)
    db.flush()

    inventario = Inventario(
        empresa_id=empresa.id,
        producto_id=producto.id,
        cantidad_disponible=Decimal("10.000"),
    )

    db.add(inventario)

    db.commit()

    return {
        "empresa_id": empresa.id,
        "usuario": usuario,
        "cliente_id": cliente.id,
        "producto_id": producto.id,
        "inventario_id": inventario.id,
    }


def autenticar_pedidos_http(
    cliente,
    escenario,
):
    respuesta = cliente.post(
        "/api/auth/login",
        json={
            "email": escenario["usuario"].email,
            "password": PASSWORD_PEDIDOS_HTTP,
        },
    )

    assert respuesta.status_code == 200, respuesta.text

    token = respuesta.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}",
    }


def datos_pedido_http(escenario, cantidad="2.000"):
    return {
        "cliente_id": escenario["cliente_id"],
        "detalles": [
            {
                "producto_id": escenario["producto_id"],
                "cantidad": cantidad,
                "descuento": "0.00",
            }
        ],
        "observaciones": "Pedido HTTP Testing",
    }


def crear_pedido_http(
    cliente,
    escenario,
    headers,
    *,
    cantidad="2.000",
):
    respuesta = cliente.post(
        "/api/pedidos",
        headers=headers,
        json=datos_pedido_http(
            escenario,
            cantidad=cantidad,
        ),
    )

    assert respuesta.status_code == 201, respuesta.text

    return respuesta.json()


# ==========================================================
# AUTENTICACION
# ==========================================================


@pytest.mark.parametrize(
    "metodo,ruta",
    [
        ("GET", "/api/pedidos"),
        ("GET", "/api/pedidos/1"),
        ("POST", "/api/pedidos/1/confirmar"),
        ("POST", "/api/pedidos/1/cancelar"),
    ],
)
def test_pedidos_requieren_autenticacion(
    cliente_pedidos_http,
    metodo,
    ruta,
):
    respuesta = cliente_pedidos_http.request(
        metodo,
        ruta,
    )

    assert respuesta.status_code == 401


def test_crear_pedido_requiere_autenticacion(
    cliente_pedidos_http,
):
    respuesta = cliente_pedidos_http.post(
        "/api/pedidos",
        json={
            "cliente_id": 1,
            "detalles": [
                {
                    "producto_id": 1,
                    "cantidad": "1.000",
                }
            ],
        },
    )

    assert respuesta.status_code == 401


# ==========================================================
# CREACION
# ==========================================================


def test_crear_pedido_http(
    cliente_pedidos_http,
    db_testing,
):
    escenario = preparar_empresa_pedidos_http(
        db_testing
    )

    headers = autenticar_pedidos_http(
        cliente_pedidos_http,
        escenario,
    )

    respuesta = cliente_pedidos_http.post(
        "/api/pedidos",
        headers=headers,
        json=datos_pedido_http(escenario),
    )

    assert respuesta.status_code == 201, respuesta.text

    datos = respuesta.json()

    assert datos["estado"] == "BORRADOR"
    assert datos["empresa_id"] == escenario["empresa_id"]
    assert datos["cliente_id"] == escenario["cliente_id"]

    assert len(datos["detalles"]) == 1

    detalle = datos["detalles"][0]

    assert (
        detalle["producto_id"]
        == escenario["producto_id"]
    )

    assert detalle["tasa_impuesto"] == "18.0000"


def test_frontend_no_puede_imponer_empresa(
    cliente_pedidos_http,
    db_testing,
):
    escenario = preparar_empresa_pedidos_http(
        db_testing
    )

    headers = autenticar_pedidos_http(
        cliente_pedidos_http,
        escenario,
    )

    datos = datos_pedido_http(escenario)
    datos["empresa_id"] = 999999

    respuesta = cliente_pedidos_http.post(
        "/api/pedidos",
        headers=headers,
        json=datos,
    )

    assert respuesta.status_code == 422


def test_frontend_no_puede_imponer_estado(
    cliente_pedidos_http,
    db_testing,
):
    escenario = preparar_empresa_pedidos_http(
        db_testing
    )

    headers = autenticar_pedidos_http(
        cliente_pedidos_http,
        escenario,
    )

    datos = datos_pedido_http(escenario)
    datos["estado"] = "CONFIRMADO"

    respuesta = cliente_pedidos_http.post(
        "/api/pedidos",
        headers=headers,
        json=datos,
    )

    assert respuesta.status_code == 422


# ==========================================================
# CONSULTA Y LISTADO
# ==========================================================


def test_listar_pedidos_http(
    cliente_pedidos_http,
    db_testing,
):
    escenario = preparar_empresa_pedidos_http(
        db_testing
    )

    headers = autenticar_pedidos_http(
        cliente_pedidos_http,
        escenario,
    )

    pedido = crear_pedido_http(
        cliente_pedidos_http,
        escenario,
        headers,
    )

    respuesta = cliente_pedidos_http.get(
        "/api/pedidos",
        headers=headers,
    )

    assert respuesta.status_code == 200, respuesta.text

    datos = respuesta.json()

    assert datos["total"] == 1
    assert datos["pagina"] == 1
    assert datos["pedidos"][0]["id"] == pedido["id"]


def test_obtener_pedido_http(
    cliente_pedidos_http,
    db_testing,
):
    escenario = preparar_empresa_pedidos_http(
        db_testing
    )

    headers = autenticar_pedidos_http(
        cliente_pedidos_http,
        escenario,
    )

    pedido = crear_pedido_http(
        cliente_pedidos_http,
        escenario,
        headers,
    )

    respuesta = cliente_pedidos_http.get(
        f"/api/pedidos/{pedido['id']}",
        headers=headers,
    )

    assert respuesta.status_code == 200, respuesta.text

    datos = respuesta.json()

    assert datos["id"] == pedido["id"]
    assert datos["estado"] == "BORRADOR"
    assert len(datos["detalles"]) == 1


# ==========================================================
# CONFIRMACION
# ==========================================================


def test_confirmar_pedido_http(
    cliente_pedidos_http,
    db_testing,
):
    escenario = preparar_empresa_pedidos_http(
        db_testing
    )

    headers = autenticar_pedidos_http(
        cliente_pedidos_http,
        escenario,
    )

    pedido = crear_pedido_http(
        cliente_pedidos_http,
        escenario,
        headers,
    )

    respuesta = cliente_pedidos_http.post(
        f"/api/pedidos/{pedido['id']}/confirmar",
        headers=headers,
    )

    assert respuesta.status_code == 200, respuesta.text

    assert respuesta.json()["estado"] == "CONFIRMADO"

    reserva = db_testing.scalar(
        select(ReservaStock).where(
            ReservaStock.pedido_id == pedido["id"],
            ReservaStock.estado == "ACTIVA",
        )
    )

    assert reserva is not None

    db_testing.expire_all()

    inventario = db_testing.get(
        Inventario,
        escenario["inventario_id"],
    )

    assert (
        inventario.cantidad_disponible
        == Decimal("10.000")
    )


def test_confirmacion_stock_insuficiente_devuelve_409(
    cliente_pedidos_http,
    db_testing,
):
    escenario = preparar_empresa_pedidos_http(
        db_testing
    )

    headers = autenticar_pedidos_http(
        cliente_pedidos_http,
        escenario,
    )

    pedido = crear_pedido_http(
        cliente_pedidos_http,
        escenario,
        headers,
        cantidad="11.000",
    )

    respuesta = cliente_pedidos_http.post(
        f"/api/pedidos/{pedido['id']}/confirmar",
        headers=headers,
    )

    assert respuesta.status_code == 409

    db_testing.expire_all()

    pedido_db = db_testing.get(
        Pedido,
        pedido["id"],
    )

    assert pedido_db.estado == "BORRADOR"


# ==========================================================
# CANCELACION
# ==========================================================


def test_cancelar_borrador_http(
    cliente_pedidos_http,
    db_testing,
):
    escenario = preparar_empresa_pedidos_http(
        db_testing
    )

    headers = autenticar_pedidos_http(
        cliente_pedidos_http,
        escenario,
    )

    pedido = crear_pedido_http(
        cliente_pedidos_http,
        escenario,
        headers,
    )

    respuesta = cliente_pedidos_http.post(
        f"/api/pedidos/{pedido['id']}/cancelar",
        headers=headers,
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado"] == "CANCELADO"


def test_cancelar_confirmado_libera_reserva_http(
    cliente_pedidos_http,
    db_testing,
):
    escenario = preparar_empresa_pedidos_http(
        db_testing
    )

    headers = autenticar_pedidos_http(
        cliente_pedidos_http,
        escenario,
    )

    pedido = crear_pedido_http(
        cliente_pedidos_http,
        escenario,
        headers,
    )

    confirmacion = cliente_pedidos_http.post(
        f"/api/pedidos/{pedido['id']}/confirmar",
        headers=headers,
    )

    assert confirmacion.status_code == 200

    cancelacion = cliente_pedidos_http.post(
        f"/api/pedidos/{pedido['id']}/cancelar",
        headers=headers,
    )

    assert cancelacion.status_code == 200
    assert cancelacion.json()["estado"] == "CANCELADO"

    db_testing.expire_all()

    reserva = db_testing.scalar(
        select(ReservaStock).where(
            ReservaStock.pedido_id == pedido["id"],
        )
    )

    assert reserva is not None
    assert reserva.estado == "LIBERADA"

    inventario = db_testing.get(
        Inventario,
        escenario["inventario_id"],
    )

    assert (
        inventario.cantidad_disponible
        == Decimal("10.000")
    )


def test_cancelar_dos_veces_devuelve_409(
    cliente_pedidos_http,
    db_testing,
):
    escenario = preparar_empresa_pedidos_http(
        db_testing
    )

    headers = autenticar_pedidos_http(
        cliente_pedidos_http,
        escenario,
    )

    pedido = crear_pedido_http(
        cliente_pedidos_http,
        escenario,
        headers,
    )

    primera = cliente_pedidos_http.post(
        f"/api/pedidos/{pedido['id']}/cancelar",
        headers=headers,
    )

    assert primera.status_code == 200

    segunda = cliente_pedidos_http.post(
        f"/api/pedidos/{pedido['id']}/cancelar",
        headers=headers,
    )

    assert segunda.status_code == 409


# ==========================================================
# RBAC
# ==========================================================


def test_usuario_sin_permiso_crear_recibe_403(
    cliente_pedidos_http,
    db_testing,
):
    escenario = preparar_empresa_pedidos_http(
        db_testing,
        permisos=("pedidos.ver",),
    )

    headers = autenticar_pedidos_http(
        cliente_pedidos_http,
        escenario,
    )

    respuesta = cliente_pedidos_http.post(
        "/api/pedidos",
        headers=headers,
        json=datos_pedido_http(escenario),
    )

    assert respuesta.status_code == 403


# ==========================================================
# MULTIEMPRESA
# ==========================================================


def test_pedido_de_otra_empresa_no_es_visible(
    cliente_pedidos_http,
    db_testing,
):
    empresa_a = preparar_empresa_pedidos_http(
        db_testing
    )

    empresa_b = preparar_empresa_pedidos_http(
        db_testing
    )

    headers_a = autenticar_pedidos_http(
        cliente_pedidos_http,
        empresa_a,
    )

    headers_b = autenticar_pedidos_http(
        cliente_pedidos_http,
        empresa_b,
    )

    pedido_b = crear_pedido_http(
        cliente_pedidos_http,
        empresa_b,
        headers_b,
    )

    consulta = cliente_pedidos_http.get(
        f"/api/pedidos/{pedido_b['id']}",
        headers=headers_a,
    )

    assert consulta.status_code == 404

    listado = cliente_pedidos_http.get(
        "/api/pedidos",
        headers=headers_a,
    )

    assert listado.status_code == 200
    assert listado.json()["total"] == 0


# ==========================================================
# VALIDACION HTTP
# ==========================================================


def test_pedidos_http_validaciones_422(
    cliente_pedidos_http,
    db_testing,
):
    escenario = preparar_empresa_pedidos_http(
        db_testing
    )

    headers = autenticar_pedidos_http(
        cliente_pedidos_http,
        escenario,
    )

    respuesta = cliente_pedidos_http.get(
        "/api/pedidos",
        headers=headers,
        params={
            "limite": 101,
        },
    )

    assert respuesta.status_code == 422

    respuesta = cliente_pedidos_http.post(
        "/api/pedidos",
        headers=headers,
        json={
            "cliente_id": escenario["cliente_id"],
            "detalles": [],
        },
    )

    assert respuesta.status_code == 422