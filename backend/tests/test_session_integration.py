
"""
SalesIA Enterprise
FASE 05-A.4-D

Pruebas reales de integración con PostgreSQL Testing.

Todos los registros se crean mediante db_testing.
No utiliza SessionLocal ni DATABASE_URL.
"""

import hashlib
import uuid

import pytest

from sqlalchemy import select

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.sesion import Sesion

from app.services.session_service import (
    SesionInvalidaError,
    crear_sesion,
    validar_sesion,
    renovar_sesion,
    revocar_sesion,
)



@pytest.fixture
def usuario_testing(db_testing):
    """
    Crea una empresa, un rol empresarial y un usuario
    ficticios dentro de PostgreSQL Testing.

    El usuario recibe un rol válido de su propia empresa.
    Todos los registros quedan sujetos al rollback del
    fixture db_testing.
    """

    identificador = uuid.uuid4().hex

    # Once dígitos ficticios para satisfacer String(11).
    ruc_ficticio = str(
        uuid.uuid4().int % 10**11
    ).zfill(11)

    # 1. Crear empresa de pruebas.
    empresa = Empresa(
        razon_social=f"Empresa Test {identificador[:12]}",
        ruc=ruc_ficticio,
        moneda_base="PEN",
        activo=True,
    )

    db_testing.add(empresa)
    db_testing.flush()

    # 2. Crear rol perteneciente a esa empresa.
    rol = Rol(
        empresa_id=empresa.id,
        nombre="Usuario Testing",
        descripcion="Rol para pruebas de integración",
    )

    db_testing.add(rol)
    db_testing.flush()

    # 3. Crear usuario aprobado.
    usuario = Usuario(
        empresa_id=empresa.id,
        nombre="Usuario de Integracion",
        email=f"test-{identificador}@example.invalid",
        password_hash="hash-ficticio-sin-login",
        activo=True,
    )

    db_testing.add(usuario)
    db_testing.flush()

    # 4. Asignar el rol empresarial al usuario.
    # SQLAlchemy registra la relación en usuarios_roles.
    usuario.roles.append(rol)

    db_testing.flush()

    return empresa, usuario



def test_creacion_real_persiste_hash(
    db_testing,
    usuario_testing,
):
    empresa, usuario = usuario_testing

    tokens = crear_sesion(
        db_testing,
        usuario_id=usuario.id,
        empresa_id=empresa.id,
    )

    sesion = db_testing.execute(
        select(Sesion).where(
            Sesion.usuario_id == usuario.id
        )
    ).scalar_one()

    assert sesion.id is not None
    assert sesion.empresa_id == empresa.id
    assert sesion.revocada is False

    refresh = tokens["refresh_token"]

    assert sesion.token_hash != refresh
    assert sesion.token_hash == hashlib.sha256(
        refresh.encode("utf-8")
    ).hexdigest()


def test_validacion_real_access_token(
    db_testing,
    usuario_testing,
):
    empresa, usuario = usuario_testing

    tokens = crear_sesion(
        db_testing,
        usuario_id=usuario.id,
        empresa_id=empresa.id,
    )

    autenticado = validar_sesion(
        db_testing,
        access_token=tokens["access_token"],
    )

    assert autenticado.id == usuario.id
    assert autenticado.empresa_id == empresa.id


def test_rotacion_real_invalida_refresh_anterior(
    db_testing,
    usuario_testing,
):
    empresa, usuario = usuario_testing

    originales = crear_sesion(
        db_testing,
        usuario_id=usuario.id,
        empresa_id=empresa.id,
    )

    anteriores = originales["refresh_token"]

    renovados = renovar_sesion(
        db_testing,
        refresh_token=anteriores,
    )

    assert renovados["refresh_token"] != anteriores

    with pytest.raises(SesionInvalidaError):
        renovar_sesion(
            db_testing,
            refresh_token=anteriores,
        )

    # El refresh nuevo debe continuar funcionando
    # después del rechazo del anterior.
    nuevos = renovar_sesion(
        db_testing,
        refresh_token=renovados["refresh_token"],
    )

    assert nuevos["refresh_token"] != renovados["refresh_token"]


def test_revocacion_real_bloquea_access(
    db_testing,
    usuario_testing,
):
    empresa, usuario = usuario_testing

    tokens = crear_sesion(
        db_testing,
        usuario_id=usuario.id,
        empresa_id=empresa.id,
    )

    revocar_sesion(
        db_testing,
        access_token=tokens["access_token"],
    )

    with pytest.raises(SesionInvalidaError):
        validar_sesion(
            db_testing,
            access_token=tokens["access_token"],
        )

    with pytest.raises(SesionInvalidaError):
        renovar_sesion(
            db_testing,
            refresh_token=tokens["refresh_token"],
        )


def test_usuario_y_empresa_inactivos(
    db_testing,
    usuario_testing,
):
    empresa, usuario = usuario_testing

    tokens = crear_sesion(
        db_testing,
        usuario_id=usuario.id,
        empresa_id=empresa.id,
    )

    usuario.activo = False
    db_testing.flush()

    with pytest.raises(SesionInvalidaError):
        validar_sesion(
            db_testing,
            access_token=tokens["access_token"],
        )

    usuario.activo = True
    empresa.activo = False
    db_testing.flush()

    with pytest.raises(SesionInvalidaError):
        validar_sesion(
            db_testing,
            access_token=tokens["access_token"],
        )

def test_retirar_rol_invalida_sesion(
    db_testing,
    usuario_testing,
):
    """
    Si un usuario pierde todos sus roles empresariales,
    su sesión existente deja de autorizar operaciones.
    """

    empresa, usuario = usuario_testing

    # Crear sesión mientras conserva un rol válido.
    tokens = crear_sesion(
        db_testing,
        usuario_id=usuario.id,
        empresa_id=empresa.id,
    )

    # Comprobar que inicialmente tiene acceso.
    autenticado = validar_sesion(
        db_testing,
        access_token=tokens["access_token"],
    )

    assert autenticado.id == usuario.id

    # Simular que un administrador retira sus roles.
    usuario.roles.clear()
    db_testing.flush()

    # El access token deja de autorizar el acceso.
    with pytest.raises(SesionInvalidaError):
        validar_sesion(
            db_testing,
            access_token=tokens["access_token"],
        )

    # Tampoco puede renovar su sesión.
    with pytest.raises(SesionInvalidaError):
        renovar_sesion(
            db_testing,
            refresh_token=tokens["refresh_token"],
        )
