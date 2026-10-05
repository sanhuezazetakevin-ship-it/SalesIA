
"""
SalesIA Enterprise
FASE 05-B.5-A

Pruebas funcionales del servicio de aprobación administrativa.

Utiliza exclusivamente la fixture db_testing.
No modifica PostgreSQL principal.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from sqlalchemy import event, select

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.permiso import Permiso
from app.models.invitacion_usuario import InvitacionUsuario
from app.models.auditoria import Auditoria

from app.services.approval_service import (
    AprobacionError,
    aprobar_usuario,
    listar_usuarios_pendientes,
)


def preparar_escenario(
    db,
    *,
    administrador_activo=True,
    empresa_activa=True,
    conceder_permiso=True,
    invitacion_aceptada=True,
    usuario_activo=False,
):
    """
    Crea una empresa, un administrador y un usuario
    de prueba con identificadores únicos.

    Todos los cambios quedan dentro del aislamiento
    transaccional de db_testing.
    """

    sufijo = uuid4().hex

    empresa = Empresa(
        razon_social=f"Empresa Approval {sufijo}",
        ruc=str(
            80000000000
            + int(sufijo[:8], 16) % 10000000000
        ),
        moneda_base="PEN",
        activo=empresa_activa,
    )

    db.add(empresa)
    db.flush()

    administrador = Usuario(
        empresa_id=empresa.id,
        nombre="Administrador de Prueba",
        email=f"admin-{sufijo}@example.com",
        password_hash="hash-ficticio-admin",
        activo=administrador_activo,
    )

    usuario = Usuario(
        empresa_id=empresa.id,
        nombre="Usuario Pendiente",
        email=f"pendiente-{sufijo}@example.com",
        password_hash="hash-ficticio-usuario",
        activo=usuario_activo,
    )

    db.add_all([administrador, usuario])
    db.flush()

    rol = Rol(
        empresa_id=empresa.id,
        nombre=f"Administrador {sufijo[:12]}",
        descripcion="Rol temporal para pruebas",
    )

    db.add(rol)
    db.flush()

    if conceder_permiso:
        permiso = db.scalar(
            select(Permiso).where(
                Permiso.codigo == "usuarios.autorizar"
            )
        )

        if permiso is None:
            permiso = Permiso(
                codigo="usuarios.autorizar",
                descripcion="Autorizar usuarios de la empresa",
            )
            db.add(permiso)
            db.flush()

        rol.permisos.append(permiso)

    administrador.roles.append(rol)

    invitacion = InvitacionUsuario(
        empresa_id=empresa.id,
        invitado_por_id=administrador.id,
        email=usuario.email,
        token_hash=uuid4().hex + uuid4().hex,
        estado=(
            "aceptada"
            if invitacion_aceptada
            else "pendiente"
        ),
        fecha_expiracion=(
            datetime.now(timezone.utc)
            + timedelta(hours=48)
        ),
    )

    db.add(invitacion)
    db.commit()

    return {
        "empresa_id": empresa.id,
        "administrador_id": administrador.id,
        "usuario_id": usuario.id,
        "invitacion_id": invitacion.id,
    }


def test_administrador_puede_listar_usuarios_pendientes(db_testing):
    datos = preparar_escenario(db_testing)

    pendientes = listar_usuarios_pendientes(
        db_testing,
        administrador_id=datos["administrador_id"],
    )

    assert len(pendientes) == 1
    assert pendientes[0]["usuario_id"] == datos["usuario_id"]
    assert pendientes[0]["empresa_id"] == datos["empresa_id"]
    assert pendientes[0]["activo"] is False
    assert "password_hash" not in pendientes[0]


def test_listado_excluye_usuario_sin_invitacion_aceptada(db_testing):
    datos = preparar_escenario(
        db_testing,
        invitacion_aceptada=False,
    )

    pendientes = listar_usuarios_pendientes(
        db_testing,
        administrador_id=datos["administrador_id"],
    )

    assert pendientes == []


def test_aprobacion_valida_activa_usuario(db_testing):
    datos = preparar_escenario(db_testing)

    resultado = aprobar_usuario(
        db_testing,
        administrador_id=datos["administrador_id"],
        usuario_id=datos["usuario_id"],
    )

    usuario = db_testing.get(
        Usuario,
        datos["usuario_id"],
    )

    assert usuario.activo is True
    assert resultado["activo"] is True
    assert resultado["estado"] == "aprobado"
    assert resultado["aprobado_por_id"] == datos["administrador_id"]
    assert resultado["empresa_id"] == datos["empresa_id"]


def test_aprobacion_registra_auditoria(db_testing):
    datos = preparar_escenario(db_testing)

    aprobar_usuario(
        db_testing,
        administrador_id=datos["administrador_id"],
        usuario_id=datos["usuario_id"],
    )

    registros = db_testing.scalars(
        select(Auditoria).where(
            Auditoria.empresa_id == datos["empresa_id"],
            Auditoria.usuario_id == datos["administrador_id"],
            Auditoria.entidad == "usuarios",
            Auditoria.entidad_id == datos["usuario_id"],
            Auditoria.accion == "ACTUALIZAR",
        )
    ).all()

    assert len(registros) == 1

    auditoria = registros[0]

    assert auditoria.datos_anteriores == {"activo": False}
    assert auditoria.datos_nuevos == {"activo": True}


def test_administrador_sin_permiso_no_puede_aprobar(db_testing):
    datos = preparar_escenario(
        db_testing,
        conceder_permiso=False,
    )

    with pytest.raises(
        AprobacionError,
        match="No tiene permiso",
    ):
        aprobar_usuario(
            db_testing,
            administrador_id=datos["administrador_id"],
            usuario_id=datos["usuario_id"],
        )

    db_testing.expire_all()

    assert db_testing.get(
        Usuario,
        datos["usuario_id"],
    ).activo is False


def test_administrador_inactivo_no_puede_aprobar(db_testing):
    datos = preparar_escenario(
        db_testing,
        administrador_activo=False,
    )

    with pytest.raises(
        AprobacionError,
        match="inactivo",
    ):
        aprobar_usuario(
            db_testing,
            administrador_id=datos["administrador_id"],
            usuario_id=datos["usuario_id"],
        )


def test_empresa_inactiva_no_puede_aprobar(db_testing):
    datos = preparar_escenario(
        db_testing,
        empresa_activa=False,
    )

    with pytest.raises(
        AprobacionError,
        match="empresa",
    ):
        aprobar_usuario(
            db_testing,
            administrador_id=datos["administrador_id"],
            usuario_id=datos["usuario_id"],
        )


def test_administrador_no_puede_aprobar_otra_empresa(db_testing):
    empresa_a = preparar_escenario(db_testing)
    empresa_b = preparar_escenario(db_testing)

    with pytest.raises(
        AprobacionError,
        match="no existe en esta empresa",
    ):
        aprobar_usuario(
            db_testing,
            administrador_id=empresa_a["administrador_id"],
            usuario_id=empresa_b["usuario_id"],
        )

    db_testing.expire_all()

    assert db_testing.get(
        Usuario,
        empresa_b["usuario_id"],
    ).activo is False


def test_usuario_sin_invitacion_aceptada_es_rechazado(db_testing):
    datos = preparar_escenario(
        db_testing,
        invitacion_aceptada=False,
    )

    with pytest.raises(
        AprobacionError,
        match="invitación completado",
    ):
        aprobar_usuario(
            db_testing,
            administrador_id=datos["administrador_id"],
            usuario_id=datos["usuario_id"],
        )

    db_testing.expire_all()

    assert db_testing.get(
        Usuario,
        datos["usuario_id"],
    ).activo is False


def test_no_permite_aprobar_dos_veces(db_testing):
    datos = preparar_escenario(db_testing)

    aprobar_usuario(
        db_testing,
        administrador_id=datos["administrador_id"],
        usuario_id=datos["usuario_id"],
    )

    with pytest.raises(
        AprobacionError,
        match="ya se encuentra activo",
    ):
        aprobar_usuario(
            db_testing,
            administrador_id=datos["administrador_id"],
            usuario_id=datos["usuario_id"],
        )

    db_testing.expire_all()

    registros = db_testing.scalars(
        select(Auditoria).where(
            Auditoria.empresa_id == datos["empresa_id"],
            Auditoria.entidad == "usuarios",
            Auditoria.entidad_id == datos["usuario_id"],
        )
    ).all()

    assert len(registros) == 1


def test_fallo_de_auditoria_revierte_activacion(db_testing):
    datos = preparar_escenario(db_testing)

    def provocar_fallo(session, flush_context, instances):
        if any(
            isinstance(objeto, Auditoria)
            for objeto in session.new
        ):
            raise RuntimeError(
                "Fallo simulado al registrar auditoría."
            )

    event.listen(
        db_testing,
        "before_flush",
        provocar_fallo,
    )

    try:
        with pytest.raises(
            RuntimeError,
            match="Fallo simulado",
        ):
            aprobar_usuario(
                db_testing,
                administrador_id=datos["administrador_id"],
                usuario_id=datos["usuario_id"],
            )
    finally:
        event.remove(
            db_testing,
            "before_flush",
            provocar_fallo,
        )

    db_testing.expire_all()

    usuario = db_testing.get(
        Usuario,
        datos["usuario_id"],
    )

    assert usuario.activo is False

    registros = db_testing.scalars(
        select(Auditoria).where(
            Auditoria.empresa_id == datos["empresa_id"],
            Auditoria.entidad_id == datos["usuario_id"],
        )
    ).all()

    assert registros == []


def test_aprobacion_no_devuelve_credenciales(db_testing):
    datos = preparar_escenario(db_testing)

    resultado = aprobar_usuario(
        db_testing,
        administrador_id=datos["administrador_id"],
        usuario_id=datos["usuario_id"],
    )

    assert "password_hash" not in resultado
    assert "access_token" not in resultado
    assert "refresh_token" not in resultado
    assert "token" not in resultado


@pytest.mark.parametrize(
    "usuario_id",
    [0, -1, True, "123", None],
)
def test_identificador_usuario_invalido(db_testing, usuario_id):
    datos = preparar_escenario(db_testing)

    with pytest.raises(
        AprobacionError,
        match="Identificador de usuario inválido",
    ):
        aprobar_usuario(
            db_testing,
            administrador_id=datos["administrador_id"],
            usuario_id=usuario_id,
        )
