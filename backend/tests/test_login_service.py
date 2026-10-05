
"""
SalesIA Enterprise
FASE 05-C.5

Pruebas funcionales del login empresarial.

Utiliza exclusivamente db_testing.
No utiliza SessionLocal ni DATABASE_URL.
"""

import hashlib
import uuid

import pytest

from sqlalchemy import select

from app.core.security import hash_password

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.sesion import Sesion

from app.services.login_service import (
    LoginError,
    iniciar_sesion,
)

from app.services.session_service import validar_sesion


PASSWORD_TEST = "ClaveSeguraTesting#2026"


@pytest.fixture
def datos_login(db_testing):
    """
    Empresa activa, usuario aprobado y rol empresarial.

    Todos los registros se crean dentro de la transacción
    aislada proporcionada por db_testing.
    """

    identificador = uuid.uuid4().hex

    ruc_ficticio = str(
        uuid.uuid4().int % 10**11
    ).zfill(11)

    empresa = Empresa(
        razon_social=f"Empresa Login {identificador[:12]}",
        ruc=ruc_ficticio,
        moneda_base="PEN",
        activo=True,
    )

    db_testing.add(empresa)
    db_testing.flush()

    rol = Rol(
        empresa_id=empresa.id,
        nombre="Usuario Login Testing",
        descripcion="Rol para pruebas del login",
    )

    db_testing.add(rol)
    db_testing.flush()

    usuario = Usuario(
        empresa_id=empresa.id,
        nombre="Usuario Login",
        email=f"login-{identificador}@example.invalid",
        password_hash=hash_password(PASSWORD_TEST),
        activo=True,
    )

    db_testing.add(usuario)
    db_testing.flush()

    usuario.roles.append(rol)
    db_testing.flush()

    return empresa, usuario


def test_login_exitoso_crea_sesion_persistente(
    db_testing,
    datos_login,
):
    empresa, usuario = datos_login

    resultado = iniciar_sesion(
        db_testing,
        email=usuario.email,
        password=PASSWORD_TEST,
    )

    assert resultado["token_type"] == "bearer"
    assert resultado["access_token"]
    assert resultado["refresh_token"]

    assert resultado["usuario"]["id"] == usuario.id
    assert resultado["usuario"]["empresa_id"] == empresa.id
    assert resultado["usuario"]["email"] == usuario.email

    sesion = db_testing.scalar(
        select(Sesion).where(
            Sesion.usuario_id == usuario.id,
            Sesion.empresa_id == empresa.id,
        )
    )

    assert sesion is not None
    assert sesion.revocada is False

    # PostgreSQL conserva el hash, nunca el JWT original.
    refresh = resultado["refresh_token"]

    assert sesion.token_hash != refresh
    assert sesion.token_hash == hashlib.sha256(
        refresh.encode("utf-8")
    ).hexdigest()

    autenticado = validar_sesion(
        db_testing,
        access_token=resultado["access_token"],
    )

    assert autenticado.id == usuario.id


def test_login_rechaza_password_incorrecta(
    db_testing,
    datos_login,
):
    empresa, usuario = datos_login

    with pytest.raises(LoginError):
        iniciar_sesion(
            db_testing,
            email=usuario.email,
            password="PasswordIncorrecta#123",
        )

    assert db_testing.scalar(
        select(Sesion.id).where(
            Sesion.usuario_id == usuario.id
        )
    ) is None


def test_login_rechaza_usuario_no_aprobado(
    db_testing,
    datos_login,
):
    empresa, usuario = datos_login

    usuario.activo = False
    db_testing.flush()

    with pytest.raises(LoginError):
        iniciar_sesion(
            db_testing,
            email=usuario.email,
            password=PASSWORD_TEST,
        )


def test_login_rechaza_empresa_inactiva(
    db_testing,
    datos_login,
):
    empresa, usuario = datos_login

    empresa.activo = False
    db_testing.flush()

    with pytest.raises(LoginError):
        iniciar_sesion(
            db_testing,
            email=usuario.email,
            password=PASSWORD_TEST,
        )


def test_login_rechaza_usuario_sin_rol(
    db_testing,
    datos_login,
):
    empresa, usuario = datos_login

    usuario.roles.clear()
    db_testing.flush()

    with pytest.raises(LoginError):
        iniciar_sesion(
            db_testing,
            email=usuario.email,
            password=PASSWORD_TEST,
        )
