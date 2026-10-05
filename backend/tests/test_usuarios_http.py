
"""
SalesIA Enterprise
FASE 05-E.3

Pruebas HTTP de invitaciones, registro
y aprobación administrativa.

Todas las solicitudes utilizan db_testing.
"""

import uuid

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
from app.models.auditoria import Auditoria
from app.models.asociaciones import roles_permisos


PASSWORD_ADMIN = "ClaveAdminHTTP#2026"
PASSWORD_INVITADO = "ClaveInvitadoHTTP#2026"


@pytest.fixture
def cliente_usuarios_http(db_testing):
    """Redirige todas las dependencias get_db a PostgreSQL Testing."""

    def override_get_db():
        yield db_testing

    overrides_originales = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as cliente:
            yield cliente
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides_originales)


def obtener_permiso(db, codigo):
    permiso = db.scalar(
        select(Permiso).where(Permiso.codigo == codigo)
    )

    if permiso is None:
        permiso = Permiso(
            codigo=codigo,
            descripcion=f"Permiso de prueba: {codigo}",
        )
        db.add(permiso)
        db.flush()

    return permiso


def crear_administrador_testing(
    db,
    *,
    puede_invitar=True,
    puede_autorizar=True,
):
    identificador = uuid.uuid4().hex

    empresa = Empresa(
        razon_social=f"Empresa HTTP {identificador[:12]}",
        ruc=str(uuid.uuid4().int % 10**11).zfill(11),
        moneda_base="PEN",
        activo=True,
    )

    db.add(empresa)
    db.flush()

    rol = Rol(
        empresa_id=empresa.id,
        nombre=f"Administrador HTTP {identificador[:8]}",
        descripcion="Rol exclusivo para pruebas HTTP",
    )

    db.add(rol)
    db.flush()

    codigos = []

    if puede_invitar:
        codigos.append("usuarios.crear")

    if puede_autorizar:
        codigos.append("usuarios.autorizar")

    for codigo in codigos:
        permiso = obtener_permiso(db, codigo)

        db.execute(
            roles_permisos.insert().values(
                rol_id=rol.id,
                permiso_id=permiso.id,
            )
        )

    administrador = Usuario(
        empresa_id=empresa.id,
        nombre="Administrador HTTP",
        email=f"admin-{identificador}@example.com",
        password_hash=hash_password(PASSWORD_ADMIN),
        activo=True,
    )

    db.add(administrador)
    db.flush()

    administrador.roles.append(rol)
    db.flush()

    return empresa, administrador


def iniciar_sesion_admin(cliente, administrador):
    respuesta = cliente.post(
        "/api/auth/login",
        json={
            "email": administrador.email,
            "password": PASSWORD_ADMIN,
        },
    )

    assert respuesta.status_code == 200, respuesta.text

    return {
        "Authorization": (
            f"Bearer {respuesta.json()['access_token']}"
        )
    }


def test_rutas_administrativas_requieren_sesion(
    cliente_usuarios_http,
):
    cliente = cliente_usuarios_http

    assert cliente.post(
        "/api/invitaciones",
        json={"email": "invitado@example.com"},
    ).status_code == 401

    assert cliente.get(
        "/api/usuarios/pendientes"
    ).status_code == 401

    assert cliente.post(
        "/api/usuarios/1/aprobar"
    ).status_code == 401


def test_flujo_invitacion_registro_aprobacion(
    cliente_usuarios_http,
    db_testing,
):
    cliente = cliente_usuarios_http

    empresa, administrador = crear_administrador_testing(
        db_testing
    )

    headers = iniciar_sesion_admin(cliente, administrador)

    identificador = uuid.uuid4().hex
    email_invitado = f"invitado-{identificador}@example.com"

    # 1. El administrador genera la invitación.
    invitacion = cliente.post(
        "/api/invitaciones",
        headers=headers,
        json={"email": email_invitado},
    )

    assert invitacion.status_code == 201, invitacion.text

    datos_invitacion = invitacion.json()

    assert datos_invitacion["empresa_id"] == empresa.id
    assert datos_invitacion["email"] == email_invitado

    token = datos_invitacion["token"]

    # 2. El invitado se registra sin seleccionar empresa.
    datos_registro = {
        "token": token,
        "nombre": "Usuario Invitado HTTP",
        "email": email_invitado,
        "password": PASSWORD_INVITADO,
    }

    registro = cliente.post(
        "/api/auth/register-invitation",
        json=datos_registro,
    )

    assert registro.status_code == 201, registro.text

    usuario_registrado = registro.json()

    assert usuario_registrado["empresa_id"] == empresa.id
    assert usuario_registrado["activo"] is False
    assert usuario_registrado["estado"] == "pendiente_aprobacion"
    assert "access_token" not in usuario_registrado
    assert "refresh_token" not in usuario_registrado

    usuario_id = usuario_registrado["usuario_id"]

    # 3. La invitación no puede utilizarse dos veces.
    segundo_registro = cliente.post(
        "/api/auth/register-invitation",
        json=datos_registro,
    )

    assert segundo_registro.status_code == 400

    # 4. La cuenta todavía no puede iniciar sesión.
    login_pendiente = cliente.post(
        "/api/auth/login",
        json={
            "email": email_invitado,
            "password": PASSWORD_INVITADO,
        },
    )

    assert login_pendiente.status_code == 401

    # 5. El administrador consulta usuarios pendientes.
    pendientes = cliente.get(
        "/api/usuarios/pendientes",
        headers=headers,
    )

    assert pendientes.status_code == 200, pendientes.text

    ids_pendientes = [
        usuario["usuario_id"]
        for usuario in pendientes.json()
    ]

    assert usuario_id in ids_pendientes

    # 6. El administrador aprueba al usuario.
    aprobacion = cliente.post(
        f"/api/usuarios/{usuario_id}/aprobar",
        headers=headers,
    )

    assert aprobacion.status_code == 200, aprobacion.text

    datos_aprobacion = aprobacion.json()

    assert datos_aprobacion["usuario_id"] == usuario_id
    assert datos_aprobacion["empresa_id"] == empresa.id
    assert datos_aprobacion["activo"] is True
    assert datos_aprobacion["estado"] == "aprobado"
    assert datos_aprobacion["aprobado_por_id"] == administrador.id

    # 7. La aprobación debe quedar auditada.
    auditoria = db_testing.scalar(
        select(Auditoria).where(
            Auditoria.empresa_id == empresa.id,
            Auditoria.usuario_id == administrador.id,
            Auditoria.entidad == "usuarios",
            Auditoria.entidad_id == usuario_id,
        )
    )

    assert auditoria is not None
    assert auditoria.datos_anteriores["activo"] is False
    assert auditoria.datos_nuevos["activo"] is True

    # 8. No se conceden roles automáticamente.
    db_testing.expire_all()

    usuario_aprobado = db_testing.get(Usuario, usuario_id)

    assert usuario_aprobado.activo is True
    assert usuario_aprobado.roles == []

    # El login continúa bloqueado hasta asignar un rol válido.
    login_sin_rol = cliente.post(
        "/api/auth/login",
        json={
            "email": email_invitado,
            "password": PASSWORD_INVITADO,
        },
    )

    assert login_sin_rol.status_code == 401


def test_usuario_sin_permiso_no_puede_invitar(
    cliente_usuarios_http,
    db_testing,
):
    empresa, administrador = crear_administrador_testing(
        db_testing,
        puede_invitar=False,
        puede_autorizar=True,
    )

    headers = iniciar_sesion_admin(
        cliente_usuarios_http,
        administrador,
    )

    respuesta = cliente_usuarios_http.post(
        "/api/invitaciones",
        headers=headers,
        json={
            "email": (
                f"sinpermiso-{uuid.uuid4().hex}@example.com"
            )
        },
    )

    assert respuesta.status_code == 400


def test_usuario_sin_permiso_no_puede_consultar_pendientes(
    cliente_usuarios_http,
    db_testing,
):
    empresa, administrador = crear_administrador_testing(
        db_testing,
        puede_invitar=True,
        puede_autorizar=False,
    )

    headers = iniciar_sesion_admin(
        cliente_usuarios_http,
        administrador,
    )

    respuesta = cliente_usuarios_http.get(
        "/api/usuarios/pendientes",
        headers=headers,
    )

    assert respuesta.status_code == 403


def test_registro_no_acepta_empresa_ni_activacion_externa(
    cliente_usuarios_http,
):
    respuesta = cliente_usuarios_http.post(
        "/api/auth/register-invitation",
        json={
            "token": "a" * 43,
            "nombre": "Usuario Externo",
            "email": "externo@example.com",
            "password": PASSWORD_INVITADO,
            "empresa_id": 999,
            "activo": True,
        },
    )

    assert respuesta.status_code == 422

# ==========================================================
# FASE 05-E.4
# PRUEBAS ADICIONALES DE SEGURIDAD MULTIEMPRESA
# ==========================================================


def test_administrador_no_puede_aprobar_usuario_otra_empresa(
    cliente_usuarios_http,
    db_testing,
):
    """
    Un administrador de la empresa B no puede aprobar
    usuarios registrados en la empresa A.
    """

    cliente = cliente_usuarios_http

    empresa_a, admin_a = crear_administrador_testing(
        db_testing
    )

    empresa_b, admin_b = crear_administrador_testing(
        db_testing
    )

    headers_a = iniciar_sesion_admin(cliente, admin_a)
    headers_b = iniciar_sesion_admin(cliente, admin_b)

    email = f"cruzado-{uuid.uuid4().hex}@example.com"

    invitacion = cliente.post(
        "/api/invitaciones",
        headers=headers_a,
        json={"email": email},
    )

    assert invitacion.status_code == 201, invitacion.text

    registro = cliente.post(
        "/api/auth/register-invitation",
        json={
            "token": invitacion.json()["token"],
            "nombre": "Usuario Empresa A",
            "email": email,
            "password": PASSWORD_INVITADO,
        },
    )

    assert registro.status_code == 201, registro.text

    usuario_id = registro.json()["usuario_id"]

    # El administrador B intenta aprobar al usuario A.
    respuesta = cliente.post(
        f"/api/usuarios/{usuario_id}/aprobar",
        headers=headers_b,
    )

    assert respuesta.status_code == 403

    db_testing.expire_all()

    usuario = db_testing.get(Usuario, usuario_id)

    assert usuario.empresa_id == empresa_a.id
    assert usuario.empresa_id != empresa_b.id
    assert usuario.activo is False

    # El administrador legítimo conserva su capacidad
    # de aprobar al usuario de su propia empresa.
    aprobacion_legitima = cliente.post(
        f"/api/usuarios/{usuario_id}/aprobar",
        headers=headers_a,
    )

    assert (
        aprobacion_legitima.status_code == 200
    ), aprobacion_legitima.text


def test_sin_permiso_autorizar_no_puede_aprobar(
    cliente_usuarios_http,
    db_testing,
):
    """
    Tener una sesión válida no concede automáticamente
    el permiso usuarios.autorizar.
    """

    cliente = cliente_usuarios_http

    empresa, administrador = crear_administrador_testing(
        db_testing,
        puede_invitar=True,
        puede_autorizar=False,
    )

    headers = iniciar_sesion_admin(
        cliente,
        administrador,
    )

    email = f"pendiente-{uuid.uuid4().hex}@example.com"

    invitacion = cliente.post(
        "/api/invitaciones",
        headers=headers,
        json={"email": email},
    )

    assert invitacion.status_code == 201, invitacion.text

    registro = cliente.post(
        "/api/auth/register-invitation",
        json={
            "token": invitacion.json()["token"],
            "nombre": "Usuario Pendiente",
            "email": email,
            "password": PASSWORD_INVITADO,
        },
    )

    assert registro.status_code == 201, registro.text

    usuario_id = registro.json()["usuario_id"]

    respuesta = cliente.post(
        f"/api/usuarios/{usuario_id}/aprobar",
        headers=headers,
    )

    assert respuesta.status_code == 403

    db_testing.expire_all()

    usuario = db_testing.get(Usuario, usuario_id)

    assert usuario.empresa_id == empresa.id
    assert usuario.activo is False


def test_no_se_puede_suplantar_administrador_desde_frontend(
    cliente_usuarios_http,
    db_testing,
):
    """
    La identidad administrativa debe proceder
    exclusivamente de la sesión JWT validada.
    """

    cliente = cliente_usuarios_http

    empresa_a, admin_a = crear_administrador_testing(
        db_testing
    )

    empresa_b, admin_b = crear_administrador_testing(
        db_testing
    )

    headers_a = iniciar_sesion_admin(cliente, admin_a)

    # Intento de inyectar identidad empresarial
    # en el cuerpo de la invitación.
    invitacion_manipulada = cliente.post(
        "/api/invitaciones",
        headers=headers_a,
        json={
            "email": (
                f"suplantacion-{uuid.uuid4().hex}@example.com"
            ),
            "administrador_id": admin_b.id,
            "empresa_id": empresa_b.id,
        },
    )

    assert invitacion_manipulada.status_code == 422

    # Intento de inyectar administrador_id
    # en el cuerpo de una aprobación.
    aprobacion_manipulada = cliente.post(
        f"/api/usuarios/{admin_b.id}/aprobar",
        headers=headers_a,
        json={
            "administrador_id": admin_b.id,
            "empresa_id": empresa_b.id,
        },
    )

    # El servicio debe impedir la aprobación cruzada.
    assert aprobacion_manipulada.status_code == 403

    db_testing.expire_all()

    assert db_testing.get(Usuario, admin_b.id).empresa_id == empresa_b.id


def test_aprobacion_duplicada_no_genera_nueva_auditoria(
    cliente_usuarios_http,
    db_testing,
):
    """
    Una cuenta aprobada no puede aprobarse nuevamente.
    La segunda solicitud no debe duplicar auditorías.
    """

    cliente = cliente_usuarios_http

    empresa, administrador = crear_administrador_testing(
        db_testing
    )

    headers = iniciar_sesion_admin(
        cliente,
        administrador,
    )

    email = f"duplicado-{uuid.uuid4().hex}@example.com"

    invitacion = cliente.post(
        "/api/invitaciones",
        headers=headers,
        json={"email": email},
    )

    assert invitacion.status_code == 201, invitacion.text

    registro = cliente.post(
        "/api/auth/register-invitation",
        json={
            "token": invitacion.json()["token"],
            "nombre": "Usuario Duplicado",
            "email": email,
            "password": PASSWORD_INVITADO,
        },
    )

    assert registro.status_code == 201, registro.text

    usuario_id = registro.json()["usuario_id"]

    # Primera aprobación.
    primera = cliente.post(
        f"/api/usuarios/{usuario_id}/aprobar",
        headers=headers,
    )

    assert primera.status_code == 200, primera.text

    consulta_auditorias = select(Auditoria).where(
        Auditoria.empresa_id == empresa.id,
        Auditoria.entidad == "usuarios",
        Auditoria.entidad_id == usuario_id,
        Auditoria.accion == "ACTUALIZAR",
    )

    auditorias_antes = db_testing.scalars(
        consulta_auditorias
    ).all()

    assert len(auditorias_antes) == 1

    # Segunda aprobación del mismo usuario.
    segunda = cliente.post(
        f"/api/usuarios/{usuario_id}/aprobar",
        headers=headers,
    )

    assert segunda.status_code == 403

    db_testing.expire_all()

    auditorias_despues = db_testing.scalars(
        consulta_auditorias
    ).all()

    assert len(auditorias_despues) == 1

    usuario = db_testing.get(Usuario, usuario_id)

    assert usuario.activo is True
