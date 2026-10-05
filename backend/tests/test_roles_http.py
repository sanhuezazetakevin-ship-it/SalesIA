
"""
SalesIA Enterprise
FASE 05-F.4A

Seguridad HTTP RBAC:
los endpoints no permiten solicitudes anonimas.
"""

import pytest

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


@pytest.mark.parametrize(
    "metodo,ruta,datos",
    [
        ("GET", "/api/roles", None),
        ("GET", "/api/roles/1/permisos", None),
        (
            "POST",
            "/api/roles/asignaciones",
            {"usuario_id": 1, "rol_id": 1},
        ),
        (
            "DELETE",
            "/api/roles/asignaciones",
            {"usuario_id": 1, "rol_id": 1},
        ),
    ],
)
def test_endpoints_rbac_requieren_autenticacion(
    metodo,
    ruta,
    datos,
):
    respuesta = client.request(
        metodo,
        ruta,
        json=datos,
    )

    assert respuesta.status_code == 401

    assert (
        respuesta.headers.get("www-authenticate")
        == "Bearer"
    )


def test_rutas_rbac_publicadas_en_openapi():
    esquema = app.openapi()
    rutas = esquema["paths"]

    assert "get" in rutas["/api/roles"]

    assert "get" in rutas[
        "/api/roles/{rol_id}/permisos"
    ]

    assert "post" in rutas[
        "/api/roles/asignaciones"
    ]

    assert "delete" in rutas[
        "/api/roles/asignaciones"
    ]

# ==========================================================
# FASE 05-F.4B
# INTEGRACION HTTP RBAC CON JWT REAL
# ==========================================================

import uuid

from sqlalchemy import select

from app.database.connection import get_db
from app.core.security import hash_password

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.permiso import Permiso
from app.models.auditoria import Auditoria
from app.models.sesion import Sesion

from app.models.asociaciones import (
    usuarios_roles,
    roles_permisos,
)


PASSWORD_RBAC_HTTP = "ClaveRBACHTTP#2026"


@pytest.fixture
def cliente_rbac_http(db_testing):
    """
    Todas las solicitudes HTTP usan PostgreSQL Testing.
    Se restauran los overrides originales al finalizar.
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


def crear_empresa_rbac_http(
    db,
    *,
    permisos_admin=(
        "roles.ver",
        "roles.asignar",
        "roles.revocar",
    ),
):
    identificador = uuid.uuid4().hex

    empresa = Empresa(
        razon_social=f"Empresa RBAC HTTP {identificador[:12]}",
        ruc=str(uuid.uuid4().int % 10**11).zfill(11),
        moneda_base="PEN",
        activo=True,
    )

    db.add(empresa)
    db.flush()

    rol_admin = Rol(
        empresa_id=empresa.id,
        nombre=f"ADMIN_RBAC_{identificador[:8]}",
        descripcion="Administrador HTTP RBAC",
    )

    rol_operativo = Rol(
        empresa_id=empresa.id,
        nombre=f"OPERATIVO_{identificador[:8]}",
        descripcion="Rol operativo HTTP RBAC",
    )

    db.add_all([rol_admin, rol_operativo])
    db.flush()

    for codigo in permisos_admin:
        permiso = db.scalar(
            select(Permiso).where(Permiso.codigo == codigo)
        )

        if permiso is None:
            permiso = Permiso(
                codigo=codigo,
                descripcion=f"Permiso temporal HTTP: {codigo}",
            )
            db.add(permiso)
            db.flush()

        db.execute(
            roles_permisos.insert().values(
                rol_id=rol_admin.id,
                permiso_id=permiso.id,
            )
        )

    administrador = Usuario(
        empresa_id=empresa.id,
        nombre="Administrador RBAC HTTP",
        email=f"admin-rbac-http-{identificador}@example.com",
        password_hash=hash_password(PASSWORD_RBAC_HTTP),
        activo=True,
    )

    usuario_destino = Usuario(
        empresa_id=empresa.id,
        nombre="Usuario Destino RBAC HTTP",
        email=f"destino-rbac-http-{identificador}@example.com",
        password_hash=hash_password(PASSWORD_RBAC_HTTP),
        activo=True,
    )

    db.add_all([administrador, usuario_destino])
    db.flush()

    db.execute(
        usuarios_roles.insert().values(
            usuario_id=administrador.id,
            rol_id=rol_admin.id,
            empresa_id=empresa.id,
        )
    )

    # Confirmamos el escenario de prueba para que los
    # rollback() intencionales no eliminen sus datos base.
    # La transaccion exterior de db_testing sigue protegida.
    db.commit()

    return {
        "empresa": empresa,
        "administrador": administrador,
        "usuario": usuario_destino,
        "rol_admin": rol_admin,
        "rol_operativo": rol_operativo,
    }


def login_rbac_http(cliente, administrador):
    respuesta = cliente.post(
        "/api/auth/login",
        json={
            "email": administrador.email,
            "password": PASSWORD_RBAC_HTTP,
        },
    )

    assert respuesta.status_code == 200, respuesta.text

    token = respuesta.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }


def test_rbac_http_admin_puede_consultar_roles(
    cliente_rbac_http,
    db_testing,
):
    escenario = crear_empresa_rbac_http(db_testing)

    headers = login_rbac_http(
        cliente_rbac_http,
        escenario["administrador"],
    )

    respuesta = cliente_rbac_http.get(
        "/api/roles",
        headers=headers,
    )

    assert respuesta.status_code == 200, respuesta.text

    roles = respuesta.json()

    ids = {rol["rol_id"] for rol in roles}

    assert escenario["rol_admin"].id in ids
    assert escenario["rol_operativo"].id in ids

    assert all(
        rol["empresa_id"] == escenario["empresa"].id
        for rol in roles
    )


def test_rbac_http_sin_permiso_recibe_403(
    cliente_rbac_http,
    db_testing,
):
    escenario = crear_empresa_rbac_http(
        db_testing,
        permisos_admin=("roles.asignar", "roles.revocar"),
    )

    headers = login_rbac_http(
        cliente_rbac_http,
        escenario["administrador"],
    )

    respuesta = cliente_rbac_http.get(
        "/api/roles",
        headers=headers,
    )

    assert respuesta.status_code == 403


def test_rbac_http_no_consulta_rol_otra_empresa(
    cliente_rbac_http,
    db_testing,
):
    empresa_a = crear_empresa_rbac_http(db_testing)
    empresa_b = crear_empresa_rbac_http(db_testing)

    headers_a = login_rbac_http(
        cliente_rbac_http,
        empresa_a["administrador"],
    )

    respuesta = cliente_rbac_http.get(
        (
            f"/api/roles/"
            f"{empresa_b['rol_operativo'].id}/permisos"
        ),
        headers=headers_a,
    )

    assert respuesta.status_code == 403


def test_rbac_http_asignar_y_revocar_con_auditoria(
    cliente_rbac_http,
    db_testing,
):
    escenario = crear_empresa_rbac_http(db_testing)

    admin = escenario["administrador"]
    usuario = escenario["usuario"]
    rol = escenario["rol_operativo"]

    headers = login_rbac_http(cliente_rbac_http, admin)

    datos = {
        "usuario_id": usuario.id,
        "rol_id": rol.id,
    }

    asignacion = cliente_rbac_http.post(
        "/api/roles/asignaciones",
        headers=headers,
        json=datos,
    )

    assert asignacion.status_code == 201, asignacion.text
    assert asignacion.json()["estado"] == "asignado"
    assert asignacion.json()["administrador_id"] == admin.id

    # La asignacion duplicada debe rechazarse.
    duplicada = cliente_rbac_http.post(
        "/api/roles/asignaciones",
        headers=headers,
        json=datos,
    )

    assert duplicada.status_code == 403

    revocacion = cliente_rbac_http.request(
        "DELETE",
        "/api/roles/asignaciones",
        headers=headers,
        json=datos,
    )

    assert revocacion.status_code == 200, revocacion.text
    assert revocacion.json()["estado"] == "revocado"
    assert revocacion.json()["administrador_id"] == admin.id
    assert revocacion.json()["sesiones_revocadas"] == 0

    db_testing.expire_all()

    asignacion_restante = db_testing.scalar(
        select(usuarios_roles.c.rol_id).where(
            usuarios_roles.c.usuario_id == usuario.id,
            usuarios_roles.c.rol_id == rol.id,
            usuarios_roles.c.empresa_id ==
            escenario["empresa"].id,
        )
    )

    assert asignacion_restante is None

    auditorias = db_testing.scalars(
        select(Auditoria).where(
            Auditoria.empresa_id == escenario["empresa"].id,
            Auditoria.entidad == "usuarios_roles",
            Auditoria.entidad_id == usuario.id,
        )
    ).all()

    assert len(auditorias) == 2

    assert {
        auditoria.descripcion for auditoria in auditorias
    } == {
        "Asignación administrativa de rol.",
        "Revocación administrativa de rol.",
    }


def test_rbac_http_rechaza_suplantacion_en_body(
    cliente_rbac_http,
    db_testing,
):
    escenario = crear_empresa_rbac_http(db_testing)

    headers = login_rbac_http(
        cliente_rbac_http,
        escenario["administrador"],
    )

    respuesta = cliente_rbac_http.post(
        "/api/roles/asignaciones",
        headers=headers,
        json={
            "usuario_id": escenario["usuario"].id,
            "rol_id": escenario["rol_operativo"].id,
            "administrador_id": 999999,
            "empresa_id": 999999,
        },
    )

    assert respuesta.status_code == 422

    asignacion = db_testing.scalar(
        select(usuarios_roles.c.rol_id).where(
            usuarios_roles.c.usuario_id ==
            escenario["usuario"].id,
            usuarios_roles.c.rol_id ==
            escenario["rol_operativo"].id,
        )
    )

    assert asignacion is None


def test_rbac_http_sesion_revocada_recibe_401(
    cliente_rbac_http,
    db_testing,
):
    escenario = crear_empresa_rbac_http(db_testing)

    headers = login_rbac_http(
        cliente_rbac_http,
        escenario["administrador"],
    )

    # El logout revoca la sesion persistida.
    logout = cliente_rbac_http.post(
        "/api/auth/logout",
        headers=headers,
    )

    assert logout.status_code == 200, logout.text

    respuesta = cliente_rbac_http.get(
        "/api/roles",
        headers=headers,
    )

    assert respuesta.status_code == 401
