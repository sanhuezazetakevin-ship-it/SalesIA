
"""
SalesIA Enterprise — FASE 07-E
Pruebas HTTP de Categorias y Productos.

JWT real, sesion persistida, RBAC y aislamiento multiempresa.
Todas las escrituras utilizan db_testing (TEST_DATABASE_URL).
"""

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
from app.models.categoria import Categoria
from app.models.producto import Producto
from app.models.auditoria import Auditoria
from app.models.asociaciones import usuarios_roles, roles_permisos


PASSWORD = "ClaveCatalogoHTTP#2026"

PERMISOS = (
    "categorias.ver",
    "categorias.crear",
    "categorias.editar",
    "productos.ver",
    "productos.crear",
    "productos.editar",
)


@pytest.fixture
def cliente_catalogo_http(db_testing):
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


def preparar_empresa(db, *, permisos=PERMISOS):
    identificador = uuid4().hex

    empresa = Empresa(
        razon_social=f"Catalogo HTTP {identificador[:12]}",
        ruc=str(uuid4().int % 10**11).zfill(11),
        moneda_base="PEN",
        activo=True,
    )
    db.add(empresa)
    db.flush()

    rol = Rol(
        empresa_id=empresa.id,
        nombre=f"CAT_HTTP_{identificador[:8]}",
        descripcion="Rol temporal de catalogo",
    )
    db.add(rol)
    db.flush()

    for codigo in permisos:
        permiso = db.scalar(
            select(Permiso).where(Permiso.codigo == codigo)
        )

        if permiso is None:
            permiso = Permiso(
                codigo=codigo,
                descripcion=f"Permiso temporal {codigo}",
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
        nombre="Operador Catalogo HTTP",
        email=f"catalogo-http-{identificador}@example.com",
        password_hash=hash_password(PASSWORD),
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

    db.commit()

    return {
        "empresa_id": empresa.id,
        "usuario_id": usuario.id,
        "email": usuario.email,
    }


def autenticar(cliente, escenario):
    respuesta = cliente.post(
        "/api/auth/login",
        json={
            "email": escenario["email"],
            "password": PASSWORD,
        },
    )

    assert respuesta.status_code == 200, respuesta.text

    return {
        "Authorization":
        f"Bearer {respuesta.json()['access_token']}"
    }


def datos_categoria(nombre="Electronica"):
    return {
        "nombre": nombre,
        "descripcion": "Categoria HTTP de prueba",
    }


def datos_producto(categoria_id=None, sku="SKU-HTTP-001"):
    return {
        "categoria_id": categoria_id,
        "sku": sku,
        "nombre": "Producto HTTP Empresarial",
        "descripcion": "Producto temporal",
        "tipo_item": "PRODUCTO",
        "precio_venta": "125.50",
        "costo_referencia": "75.25",
        "controla_stock": True,
    }


@pytest.mark.parametrize(
    "metodo,ruta,cuerpo",
    [
        ("POST", "/api/categorias", datos_categoria()),
        ("GET", "/api/categorias", None),
        ("GET", "/api/categorias/1", None),
        ("PATCH", "/api/categorias/1", {"nombre": "Nueva"}),
        ("DELETE", "/api/categorias/1", None),
        ("POST", "/api/productos", datos_producto()),
        ("GET", "/api/productos", None),
        ("GET", "/api/productos/1", None),
        ("PATCH", "/api/productos/1", {"nombre": "Nuevo"}),
        ("DELETE", "/api/productos/1", None),
    ],
)
def test_todas_las_rutas_requieren_jwt(
    cliente_catalogo_http,
    metodo,
    ruta,
    cuerpo,
):
    respuesta = cliente_catalogo_http.request(
        metodo,
        ruta,
        json=cuerpo,
    )

    assert respuesta.status_code == 401, respuesta.text
    assert respuesta.headers.get("www-authenticate") == "Bearer"


@pytest.mark.parametrize(
    "ruta",
    ["/api/categorias", "/api/productos"],
)
def test_jwt_invalido(cliente_catalogo_http, ruta):
    respuesta = cliente_catalogo_http.get(
        ruta,
        headers={"Authorization": "Bearer token-invalido"},
    )
    assert respuesta.status_code == 401


def test_categorias_flujo_completo_y_auditoria(
    cliente_catalogo_http,
    db_testing,
):
    escenario = preparar_empresa(db_testing)
    headers = autenticar(cliente_catalogo_http, escenario)

    creacion = cliente_catalogo_http.post(
        "/api/categorias",
        headers=headers,
        json=datos_categoria(),
    )
    assert creacion.status_code == 201, creacion.text

    categoria = creacion.json()
    categoria_id = categoria["id"]

    assert categoria["empresa_id"] == escenario["empresa_id"]
    assert categoria["activo"] is True

    listado = cliente_catalogo_http.get(
        "/api/categorias",
        headers=headers,
        params={
            "busqueda": "electro",
            "activo": "true",
            "pagina": 1,
            "limite": 10,
        },
    )
    assert listado.status_code == 200, listado.text
    assert listado.json()["total"] == 1
    assert listado.json()["categorias"][0]["id"] == categoria_id

    consulta = cliente_catalogo_http.get(
        f"/api/categorias/{categoria_id}",
        headers=headers,
    )
    assert consulta.status_code == 200, consulta.text

    actualizacion = cliente_catalogo_http.patch(
        f"/api/categorias/{categoria_id}",
        headers=headers,
        json={"nombre": "Tecnologia"},
    )
    assert actualizacion.status_code == 200, actualizacion.text
    assert actualizacion.json()["nombre"] == "Tecnologia"

    baja = cliente_catalogo_http.delete(
        f"/api/categorias/{categoria_id}",
        headers=headers,
    )
    assert baja.status_code == 200, baja.text
    assert baja.json()["activo"] is False

    db_testing.expire_all()
    assert db_testing.get(Categoria, categoria_id).activo is False

    auditorias = db_testing.scalars(
        select(Auditoria).where(
            Auditoria.empresa_id == escenario["empresa_id"],
            Auditoria.entidad == "categorias",
            Auditoria.entidad_id == categoria_id,
        )
    ).all()

    assert len(auditorias) == 3


def test_productos_flujo_completo_y_auditoria(
    cliente_catalogo_http,
    db_testing,
):
    escenario = preparar_empresa(db_testing)
    headers = autenticar(cliente_catalogo_http, escenario)

    categoria = cliente_catalogo_http.post(
        "/api/categorias",
        headers=headers,
        json=datos_categoria(),
    )
    assert categoria.status_code == 201, categoria.text
    categoria_id = categoria.json()["id"]

    creacion = cliente_catalogo_http.post(
        "/api/productos",
        headers=headers,
        json=datos_producto(categoria_id),
    )
    assert creacion.status_code == 201, creacion.text

    producto = creacion.json()
    producto_id = producto["id"]

    assert producto["empresa_id"] == escenario["empresa_id"]
    assert producto["categoria_id"] == categoria_id
    assert producto["precio_venta"] == "125.50"

    listado = cliente_catalogo_http.get(
        "/api/productos",
        headers=headers,
        params={
            "busqueda": "SKU-HTTP-001",
            "categoria_id": categoria_id,
            "tipo_item": "PRODUCTO",
            "activo": "true",
        },
    )
    assert listado.status_code == 200, listado.text
    assert listado.json()["total"] == 1
    assert listado.json()["productos"][0]["id"] == producto_id

    consulta = cliente_catalogo_http.get(
        f"/api/productos/{producto_id}",
        headers=headers,
    )
    assert consulta.status_code == 200, consulta.text

    cambio = cliente_catalogo_http.patch(
        f"/api/productos/{producto_id}",
        headers=headers,
        json={
            "nombre": "Producto Actualizado",
            "precio_venta": "150.75",
        },
    )
    assert cambio.status_code == 200, cambio.text
    assert cambio.json()["nombre"] == "Producto Actualizado"
    assert cambio.json()["precio_venta"] == "150.75"

    # Una categoria con productos activos no se desactiva.
    rechazo_categoria = cliente_catalogo_http.delete(
        f"/api/categorias/{categoria_id}",
        headers=headers,
    )
    assert rechazo_categoria.status_code == 403

    baja = cliente_catalogo_http.delete(
        f"/api/productos/{producto_id}",
        headers=headers,
    )
    assert baja.status_code == 200, baja.text
    assert baja.json()["activo"] is False

    db_testing.expire_all()
    assert db_testing.get(Producto, producto_id).activo is False

    auditorias = db_testing.scalars(
        select(Auditoria).where(
            Auditoria.empresa_id == escenario["empresa_id"],
            Auditoria.entidad == "productos",
            Auditoria.entidad_id == producto_id,
        )
    ).all()
    assert len(auditorias) == 3


@pytest.mark.parametrize(
    "ruta,datos",
    [
        ("/api/categorias", datos_categoria()),
        ("/api/productos", datos_producto()),
    ],
)
def test_sin_permisos_retorna_403(
    cliente_catalogo_http,
    db_testing,
    ruta,
    datos,
):
    escenario = preparar_empresa(db_testing, permisos=())
    headers = autenticar(cliente_catalogo_http, escenario)

    listado = cliente_catalogo_http.get(ruta, headers=headers)
    creacion = cliente_catalogo_http.post(
        ruta,
        headers=headers,
        json=datos,
    )

    assert listado.status_code == 403
    assert creacion.status_code == 403


@pytest.mark.parametrize(
    "ruta,datos",
    [
        ("/api/categorias", datos_categoria()),
        ("/api/productos", datos_producto()),
    ],
)
def test_empresa_id_prohibido_y_paginacion_invalida(
    cliente_catalogo_http,
    db_testing,
    ruta,
    datos,
):
    escenario = preparar_empresa(db_testing)
    headers = autenticar(cliente_catalogo_http, escenario)

    cuerpo = {**datos, "empresa_id": 999999}
    creacion = cliente_catalogo_http.post(
        ruta,
        headers=headers,
        json=cuerpo,
    )
    assert creacion.status_code == 422, creacion.text

    listado = cliente_catalogo_http.get(
        ruta,
        headers=headers,
        params={"limite": 101},
    )
    assert listado.status_code == 422


def test_aislamiento_http_entre_empresas(
    cliente_catalogo_http,
    db_testing,
):
    empresa_a = preparar_empresa(db_testing)
    empresa_b = preparar_empresa(db_testing)

    headers_a = autenticar(cliente_catalogo_http, empresa_a)
    headers_b = autenticar(cliente_catalogo_http, empresa_b)

    categoria_b = cliente_catalogo_http.post(
        "/api/categorias",
        headers=headers_b,
        json=datos_categoria(),
    )
    assert categoria_b.status_code == 201, categoria_b.text
    categoria_id = categoria_b.json()["id"]

    producto_b = cliente_catalogo_http.post(
        "/api/productos",
        headers=headers_b,
        json=datos_producto(categoria_id),
    )
    assert producto_b.status_code == 201, producto_b.text
    producto_id = producto_b.json()["id"]

    for ruta, datos in (
        (f"/api/categorias/{categoria_id}", {"nombre": "Cambio ajeno"}),
        (f"/api/productos/{producto_id}", {"nombre": "Cambio ajeno"}),
    ):
        assert cliente_catalogo_http.get(
            ruta, headers=headers_a
        ).status_code == 403

        assert cliente_catalogo_http.patch(
            ruta, headers=headers_a, json=datos
        ).status_code == 403

        assert cliente_catalogo_http.delete(
            ruta, headers=headers_a
        ).status_code == 403

    for ruta in ("/api/categorias", "/api/productos"):
        respuesta = cliente_catalogo_http.get(
            ruta,
            headers=headers_a,
        )
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["total"] == 0

    # Tampoco se puede asignar un producto de A
    # a una categoria que pertenece a B.
    ajeno = cliente_catalogo_http.post(
        "/api/productos",
        headers=headers_a,
        json=datos_producto(categoria_id),
    )
    assert ajeno.status_code == 403

    db_testing.expire_all()
    assert db_testing.get(Categoria, categoria_id).activo is True
    assert db_testing.get(Producto, producto_id).activo is True
    assert db_testing.get(Producto, producto_id).empresa_id == (
        empresa_b["empresa_id"]
    )
