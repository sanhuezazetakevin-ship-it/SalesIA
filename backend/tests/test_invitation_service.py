
"""
SalesIA Enterprise
FASE 05-B.3-B

Pruebas de invitaciones empresariales con PostgreSQL Testing.
No utiliza la base de datos principal.
"""

import hashlib
from itertools import count
from uuid import uuid4

import pytest

from sqlalchemy import insert, select

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.permiso import Permiso
from app.models.invitacion_usuario import InvitacionUsuario
from app.models.asociaciones import usuarios_roles, roles_permisos

from app.services.invitation_service import (
    InvitacionError,
    crear_invitacion,
)


_secuencia_ruc = count(90000000001)


def preparar_escenario(db, *, con_permiso=True):
    """
    Crea una empresa, un administrador ficticio y su rol.
    Todo queda dentro de la transacción protegida de db_testing.
    """

    sufijo = uuid4().hex

    empresa = Empresa(
        razon_social=f"Empresa Invitaciones {sufijo}",
        ruc=str(next(_secuencia_ruc)),
        moneda_base="PEN",
        activo=True,
    )

    db.add(empresa)
    db.flush()

    administrador = Usuario(
        empresa_id=empresa.id,
        nombre="Administrador de Pruebas",
        email=f"admin-{sufijo}@example.com",
        password_hash="hash-ficticio-no-utilizable",
        activo=True,
    )

    db.add(administrador)
    db.flush()

    rol = Rol(
        empresa_id=empresa.id,
        nombre=f"ROL_TEST_{sufijo[:12]}",
        descripcion="Rol temporal para pruebas",
    )

    db.add(rol)
    db.flush()

    db.execute(
        insert(usuarios_roles).values(
            usuario_id=administrador.id,
            rol_id=rol.id,
            empresa_id=empresa.id,
        )
    )

    
    
    if con_permiso:
        permiso_id = db.scalar(
            select(Permiso.id).where(
                Permiso.codigo == "usuarios.crear"
            )
        )

        # Crear el permiso temporal si Testing no tiene seed.
        if permiso_id is None:
            permiso = Permiso(
                codigo="usuarios.crear",
                descripcion="Permiso temporal para pruebas",
            )

            db.add(permiso)
            db.flush()

            permiso_id = permiso.id

        db.execute(
            insert(roles_permisos).values(
                rol_id=rol.id,
                permiso_id=permiso_id,
            )
        )

    db.flush()

    return empresa, administrador


    return empresa, administrador


def email_nuevo():
    return f"invitado-{uuid4().hex}@example.com"


def test_administrador_autorizado_crea_invitacion(db_testing):
    db = db_testing
    empresa, administrador = preparar_escenario(db)

    resultado = crear_invitacion(
        db,
        administrador_id=administrador.id,
        email_invitado=email_nuevo(),
    )

    invitacion = db.get(
        InvitacionUsuario,
        resultado["invitacion_id"],
    )

    assert invitacion is not None
    assert invitacion.empresa_id == empresa.id
    assert invitacion.invitado_por_id == administrador.id
    assert invitacion.estado == "pendiente"
    assert resultado["empresa_id"] == empresa.id
    assert resultado["token"]


def test_usuario_sin_permiso_no_puede_invitar(db_testing):
    db = db_testing
    _, administrador = preparar_escenario(
        db,
        con_permiso=False,
    )

    with pytest.raises(InvitacionError, match="permiso"):
        crear_invitacion(
            db,
            administrador_id=administrador.id,
            email_invitado=email_nuevo(),
        )


def test_administrador_inactivo_no_puede_invitar(db_testing):
    db = db_testing
    _, administrador = preparar_escenario(db)

    administrador.activo = False
    db.flush()

    with pytest.raises(InvitacionError, match="inactivo"):
        crear_invitacion(
            db,
            administrador_id=administrador.id,
            email_invitado=email_nuevo(),
        )


def test_empresa_inactiva_no_puede_invitar(db_testing):
    db = db_testing
    empresa, administrador = preparar_escenario(db)

    empresa.activo = False
    db.flush()

    with pytest.raises(InvitacionError, match="inactiva"):
        crear_invitacion(
            db,
            administrador_id=administrador.id,
            email_invitado=email_nuevo(),
        )


def test_correo_ya_registrado_es_rechazado(db_testing):
    db = db_testing
    empresa, administrador = preparar_escenario(db)

    correo = email_nuevo()

    usuario_existente = Usuario(
        empresa_id=empresa.id,
        nombre="Usuario Existente",
        email=correo,
        password_hash="hash-ficticio-no-utilizable",
        activo=False,
    )

    db.add(usuario_existente)
    db.flush()

    with pytest.raises(InvitacionError, match="registrada"):
        crear_invitacion(
            db,
            administrador_id=administrador.id,
            email_invitado=correo,
        )


def test_correo_invalido_es_rechazado(db_testing):
    db = db_testing
    _, administrador = preparar_escenario(db)

    with pytest.raises(InvitacionError, match="no es válido"):
        crear_invitacion(
            db,
            administrador_id=administrador.id,
            email_invitado="correo-invalido",
        )


def test_invitacion_vigente_duplicada_es_rechazada(db_testing):
    db = db_testing
    _, administrador = preparar_escenario(db)

    correo = email_nuevo()

    crear_invitacion(
        db,
        administrador_id=administrador.id,
        email_invitado=correo,
    )

    with pytest.raises(InvitacionError, match="invitación vigente"):
        crear_invitacion(
            db,
            administrador_id=administrador.id,
            email_invitado=correo,
        )


def test_token_se_almacena_unicamente_como_hash(db_testing):
    db = db_testing
    _, administrador = preparar_escenario(db)

    resultado = crear_invitacion(
        db,
        administrador_id=administrador.id,
        email_invitado=email_nuevo(),
    )

    invitacion = db.get(
        InvitacionUsuario,
        resultado["invitacion_id"],
    )

    token_original = resultado["token"]

    hash_esperado = hashlib.sha256(
        token_original.encode("utf-8")
    ).hexdigest()

    assert invitacion.token_hash == hash_esperado
    assert invitacion.token_hash != token_original
    assert len(invitacion.token_hash) == 64
