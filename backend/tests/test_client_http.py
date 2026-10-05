
"""
SalesIA Enterprise
FASE 06-D.3

Pruebas HTTP empresariales de clientes.

- JWT real y sesion persistida.
- Permisos RBAC.
- Aislamiento multiempresa.
- Exclusivamente PostgreSQL Testing.
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
from app.models.cliente import Cliente
from app.models.auditoria import Auditoria
from app.models.asociaciones import usuarios_roles, roles_permisos


PASSWORD_CLIENTES_HTTP = "ClaveClientesHTTP#2026"

PERMISOS_CLIENTES = (
    "clientes.ver",
    "clientes.crear",
    "clientes.editar",
)


@pytest.fixture
def cliente_clientes_http(db_testing):
    """
    Toda solicitud HTTP utiliza la conexion protegida
    por la fixture db_testing.
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


def preparar_empresa_clientes_http(
    db,
    *,
    permisos=PERMISOS_CLIENTES,
):
    identificador = uuid4().hex

    empresa = Empresa(
        razon_social=f"Clientes HTTP {identificador[:12]}",
        ruc=str(uuid4().int % 10**11).zfill(11),
        moneda_base="PEN",
        activo=True,
    )

    db.add(empresa)
    db.flush()

    rol = Rol(
        empresa_id=empresa.id,
        nombre=f"CLIENTES_HTTP_{identificador[:8]}",
        descripcion="Rol temporal HTTP de clientes",
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
        nombre="Operador Clientes HTTP",
        email=f"clientes-http-{identificador}@example.com",
        password_hash=hash_password(PASSWORD_CLIENTES_HTTP),
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

    # Confirma el savepoint de db_testing, no la
    # transaccion exterior protegida.
    db.commit()

    return {
        "empresa_id": empresa.id,
        "usuario_id": usuario.id,
        "email": usuario.email,
    }


def autenticar_cliente_http(cliente, escenario):
    respuesta = cliente.post(
        "/api/auth/login",
        json={
            "email": escenario["email"],
            "password": PASSWORD_CLIENTES_HTTP,
        },
    )

    assert respuesta.status_code == 200, respuesta.text

    token = respuesta.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }


def datos_cliente_http(documento="12345678"):
    return {
        "nombre": "Cliente HTTP Empresarial",
        "tipo_documento": "DNI",
        "numero_documento": documento,
        "email": "cliente-http@example.com",
        "telefono": "999888777",
        "direccion": "Direccion de Testing",
    }


@pytest.mark.parametrize(
    "metodo,ruta,datos",
    [
        ("POST", "/api/clientes", datos_cliente_http()),
        ("GET", "/api/clientes", None),
        ("GET", "/api/clientes/1", None),
        (
            "PATCH",
            "/api/clientes/1",
            {"nombre": "Cliente Modificado"},
        ),
        ("DELETE", "/api/clientes/1", None),
    ],
)
def test_clientes_http_requiere_jwt(
    cliente_clientes_http,
    metodo,
    ruta,
    datos,
):
    respuesta = cliente_clientes_http.request(
        metodo,
        ruta,
        json=datos,
    )

    assert respuesta.status_code == 401, respuesta.text
    assert respuesta.headers.get("www-authenticate") == "Bearer"


def test_clientes_http_rechaza_jwt_invalido(
    cliente_clientes_http,
):
    respuesta = cliente_clientes_http.get(
        "/api/clientes",
        headers={
            "Authorization": "Bearer token-invalido"
        },
    )

    assert respuesta.status_code == 401


def test_clientes_http_creacion_y_auditoria(
    cliente_clientes_http,
    db_testing,
):
    escenario = preparar_empresa_clientes_http(db_testing)
    headers = autenticar_cliente_http(
        cliente_clientes_http,
        escenario,
    )

    respuesta = cliente_clientes_http.post(
        "/api/clientes",
        headers=headers,
        json=datos_cliente_http(),
    )

    assert respuesta.status_code == 201, respuesta.text

    datos = respuesta.json()

    assert datos["id"] > 0
    assert datos["empresa_id"] == escenario["empresa_id"]
    assert datos["nombre"] == "Cliente HTTP Empresarial"
    assert datos["activo"] is True

    auditorias = db_testing.scalars(
        select(Auditoria).where(
            Auditoria.empresa_id == escenario["empresa_id"],
            Auditoria.usuario_id == escenario["usuario_id"],
            Auditoria.entidad == "clientes",
            Auditoria.entidad_id == datos["id"],
            Auditoria.accion == "CREAR",
        )
    ).all()

    assert len(auditorias) == 1


def test_clientes_http_listado_y_consulta_individual(
    cliente_clientes_http,
    db_testing,
):
    escenario = preparar_empresa_clientes_http(db_testing)
    headers = autenticar_cliente_http(
        cliente_clientes_http,
        escenario,
    )

    creacion = cliente_clientes_http.post(
        "/api/clientes",
        headers=headers,
        json=datos_cliente_http(),
    )

    assert creacion.status_code == 201, creacion.text
    cliente_id = creacion.json()["id"]

    listado = cliente_clientes_http.get(
        "/api/clientes",
        headers=headers,
        params={
            "pagina": 1,
            "limite": 10,
            "busqueda": "12345678",
            "activo": "true",
        },
    )

    assert listado.status_code == 200, listado.text

    datos = listado.json()

    assert datos["total"] == 1
    assert datos["pagina"] == 1
    assert datos["limite"] == 10
    assert len(datos["clientes"]) == 1
    assert datos["clientes"][0]["id"] == cliente_id

    individual = cliente_clientes_http.get(
        f"/api/clientes/{cliente_id}",
        headers=headers,
    )

    assert individual.status_code == 200, individual.text
    assert individual.json()["id"] == cliente_id


def test_clientes_http_actualizacion(
    cliente_clientes_http,
    db_testing,
):
    escenario = preparar_empresa_clientes_http(db_testing)
    headers = autenticar_cliente_http(
        cliente_clientes_http,
        escenario,
    )

    creacion = cliente_clientes_http.post(
        "/api/clientes",
        headers=headers,
        json=datos_cliente_http(),
    )

    assert creacion.status_code == 201, creacion.text
    cliente_id = creacion.json()["id"]

    respuesta = cliente_clientes_http.patch(
        f"/api/clientes/{cliente_id}",
        headers=headers,
        json={
            "nombre": "Cliente HTTP Actualizado",
        },
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["nombre"] == "Cliente HTTP Actualizado"
    assert respuesta.json()["numero_documento"] == "12345678"

    auditorias = db_testing.scalars(
        select(Auditoria).where(
            Auditoria.empresa_id == escenario["empresa_id"],
            Auditoria.entidad == "clientes",
            Auditoria.entidad_id == cliente_id,
            Auditoria.accion == "ACTUALIZAR",
        )
    ).all()

    assert len(auditorias) == 1


def test_clientes_http_baja_logica(
    cliente_clientes_http,
    db_testing,
):
    escenario = preparar_empresa_clientes_http(db_testing)
    headers = autenticar_cliente_http(
        cliente_clientes_http,
        escenario,
    )

    creacion = cliente_clientes_http.post(
        "/api/clientes",
        headers=headers,
        json=datos_cliente_http(),
    )

    assert creacion.status_code == 201, creacion.text
    cliente_id = creacion.json()["id"]

    respuesta = cliente_clientes_http.delete(
        f"/api/clientes/{cliente_id}",
        headers=headers,
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["activo"] is False

    db_testing.expire_all()

    cliente = db_testing.get(Cliente, cliente_id)

    assert cliente is not None
    assert cliente.activo is False

    segunda = cliente_clientes_http.delete(
        f"/api/clientes/{cliente_id}",
        headers=headers,
    )

    assert segunda.status_code == 403


def test_clientes_http_sin_permisos_recibe_403(
    cliente_clientes_http,
    db_testing,
):
    escenario = preparar_empresa_clientes_http(
        db_testing,
        permisos=(),
    )

    headers = autenticar_cliente_http(
        cliente_clientes_http,
        escenario,
    )

    listado = cliente_clientes_http.get(
        "/api/clientes",
        headers=headers,
    )

    creacion = cliente_clientes_http.post(
        "/api/clientes",
        headers=headers,
        json=datos_cliente_http(),
    )

    assert listado.status_code == 403
    assert creacion.status_code == 403


def test_clientes_http_aislamiento_multiempresa(
    cliente_clientes_http,
    db_testing,
):
    empresa_a = preparar_empresa_clientes_http(db_testing)
    empresa_b = preparar_empresa_clientes_http(db_testing)

    headers_a = autenticar_cliente_http(
        cliente_clientes_http,
        empresa_a,
    )

    headers_b = autenticar_cliente_http(
        cliente_clientes_http,
        empresa_b,
    )

    creacion_b = cliente_clientes_http.post(
        "/api/clientes",
        headers=headers_b,
        json=datos_cliente_http(),
    )

    assert creacion_b.status_code == 201, creacion_b.text
    cliente_b_id = creacion_b.json()["id"]

    # La empresa A no puede consultar ni modificar B.
    consulta = cliente_clientes_http.get(
        f"/api/clientes/{cliente_b_id}",
        headers=headers_a,
    )

    actualizacion = cliente_clientes_http.patch(
        f"/api/clientes/{cliente_b_id}",
        headers=headers_a,
        json={"nombre": "Cambio Ajeno"},
    )

    desactivacion = cliente_clientes_http.delete(
        f"/api/clientes/{cliente_b_id}",
        headers=headers_a,
    )

    assert consulta.status_code == 403
    assert actualizacion.status_code == 403
    assert desactivacion.status_code == 403

    listado_a = cliente_clientes_http.get(
        "/api/clientes",
        headers=headers_a,
    )

    assert listado_a.status_code == 200, listado_a.text
    assert listado_a.json()["total"] == 0

    db_testing.expire_all()

    cliente_b = db_testing.get(Cliente, cliente_b_id)

    assert cliente_b.empresa_id == empresa_b["empresa_id"]
    assert cliente_b.nombre == "Cliente HTTP Empresarial"
    assert cliente_b.activo is True


def test_clientes_http_validacion_de_datos(
    cliente_clientes_http,
    db_testing,
):
    escenario = preparar_empresa_clientes_http(db_testing)
    headers = autenticar_cliente_http(
        cliente_clientes_http,
        escenario,
    )

    # Un usuario no puede imponer la empresa desde el body.
    datos = datos_cliente_http()
    datos["empresa_id"] = 999999

    respuesta = cliente_clientes_http.post(
        "/api/clientes",
        headers=headers,
        json=datos,
    )

    assert respuesta.status_code == 422

    # Tipo y numero de documento deben ser coherentes.
    datos = datos_cliente_http()
    datos["numero_documento"] = None

    respuesta = cliente_clientes_http.post(
        "/api/clientes",
        headers=headers,
        json=datos,
    )

    assert respuesta.status_code == 422

    # Paginacion fuera del intervalo permitido.
    respuesta = cliente_clientes_http.get(
        "/api/clientes",
        headers=headers,
        params={"limite": 101},
    )

    assert respuesta.status_code == 422
