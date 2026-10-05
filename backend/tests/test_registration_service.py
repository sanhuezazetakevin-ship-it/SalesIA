
"""
SalesIA Enterprise
FASE 05-B.4-A

Pruebas funcionales del registro mediante invitación.

Exclusivamente PostgreSQL Testing mediante db_testing.
No utiliza la base de datos principal.
"""

import hashlib
import secrets

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from sqlalchemy import func, select

from app.core.security import verify_password
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.invitacion_usuario import InvitacionUsuario

from app.services.registration_service import (
    RegistroInvitacionError,
    registrar_con_invitacion,
)


PASSWORD_PRUEBA = "ClaveDePruebaSegura2026!"


def preparar_escenario(
    db,
    *,
    estado="pendiente",
    horas_vigencia=48,
    empresa_activa=True,
):
    """
    Prepara una empresa, administrador e invitación temporal.

    Confirma el setup dentro del savepoint protegido
    por la fixture db_testing.
    """

    sufijo = uuid4().hex
    token = secrets.token_urlsafe(32)
    correo = f"registro-{sufijo}@example.com"

    empresa = Empresa(
        razon_social=f"Empresa Registro {sufijo}",
        ruc=str(80000000000 + int(sufijo[:8], 16)),
        moneda_base="PEN",
        activo=empresa_activa,
    )

    db.add(empresa)
    db.flush()

    administrador = Usuario(
        empresa_id=empresa.id,
        nombre="Administrador de Pruebas",
        email=f"admin-registro-{sufijo}@example.com",
        password_hash="hash-ficticio-no-utilizable",
        activo=True,
    )

    db.add(administrador)
    db.flush()

    invitacion = InvitacionUsuario(
        empresa_id=empresa.id,
        invitado_por_id=administrador.id,
        email=correo,
        token_hash=hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest(),
        estado=estado,
        fecha_expiracion=(
            datetime.now(timezone.utc)
            + timedelta(hours=horas_vigencia)
        ),
    )

    db.add(invitacion)
    db.flush()

    ids = {
        "empresa_id": empresa.id,
        "administrador_id": administrador.id,
        "invitacion_id": invitacion.id,
        "email": correo,
        "token": token,
    }

    db.commit()

    return ids


def registrar(db, escenario, **cambios):
    datos = {
        "token": escenario["token"],
        "nombre": "Usuario de Pruebas",
        "email": escenario["email"],
        "password": PASSWORD_PRUEBA,
    }

    datos.update(cambios)

    return registrar_con_invitacion(db, **datos)


def contar_usuarios(db, correo):
    return db.scalar(
        select(func.count(Usuario.id)).where(
            Usuario.email == correo
        )
    )


def test_registro_valido_crea_usuario_inactivo(db_testing):
    db = db_testing
    escenario = preparar_escenario(db)

    resultado = registrar(db, escenario)

    usuario = db.get(Usuario, resultado["usuario_id"])

    assert usuario is not None
    assert usuario.empresa_id == escenario["empresa_id"]
    assert usuario.email == escenario["email"]
    assert usuario.nombre == "Usuario de Pruebas"
    assert usuario.activo is False

    assert resultado["activo"] is False
    assert resultado["estado"] == "pendiente_aprobacion"


def test_password_se_almacena_con_hash_seguro(db_testing):
    db = db_testing
    escenario = preparar_escenario(db)

    resultado = registrar(db, escenario)
    usuario = db.get(Usuario, resultado["usuario_id"])

    assert usuario.password_hash != PASSWORD_PRUEBA
    assert verify_password(
        PASSWORD_PRUEBA,
        usuario.password_hash,
    )


def test_registro_acepta_invitacion_en_misma_transaccion(db_testing):
    db = db_testing
    escenario = preparar_escenario(db)

    resultado = registrar(db, escenario)

    invitacion = db.get(
        InvitacionUsuario,
        escenario["invitacion_id"],
    )

    assert invitacion.estado == "aceptada"
    assert resultado["empresa_id"] == invitacion.empresa_id
    assert contar_usuarios(db, escenario["email"]) == 1


def test_token_inexistente_es_rechazado(db_testing):
    db = db_testing
    escenario = preparar_escenario(db)

    with pytest.raises(
        RegistroInvitacionError,
        match="no es válida",
    ):
        registrar(
            db,
            escenario,
            token=secrets.token_urlsafe(32),
        )

    assert contar_usuarios(db, escenario["email"]) == 0


@pytest.mark.parametrize(
    "estado",
    ["revocada", "aceptada", "expirada"],
)
def test_invitacion_no_pendiente_es_rechazada(
    db_testing,
    estado,
):
    db = db_testing
    escenario = preparar_escenario(
        db,
        estado=estado,
    )

    with pytest.raises(
        RegistroInvitacionError,
        match="no está disponible",
    ):
        registrar(db, escenario)

    assert contar_usuarios(db, escenario["email"]) == 0


def test_invitacion_vencida_es_rechazada(db_testing):
    db = db_testing
    escenario = preparar_escenario(
        db,
        horas_vigencia=-1,
    )

    with pytest.raises(
        RegistroInvitacionError,
        match="expirado",
    ):
        registrar(db, escenario)

    assert contar_usuarios(db, escenario["email"]) == 0


def test_token_no_puede_reutilizarse(db_testing):
    db = db_testing
    escenario = preparar_escenario(db)

    registrar(db, escenario)

    with pytest.raises(
        RegistroInvitacionError,
        match="no está disponible",
    ):
        registrar(db, escenario)

    assert contar_usuarios(db, escenario["email"]) == 1


def test_correo_diferente_es_rechazado(db_testing):
    db = db_testing
    escenario = preparar_escenario(db)

    with pytest.raises(
        RegistroInvitacionError,
        match="no corresponde",
    ):
        registrar(
            db,
            escenario,
            email=f"otro-{uuid4().hex}@example.com",
        )

    assert contar_usuarios(db, escenario["email"]) == 0


def test_empresa_inactiva_es_rechazada(db_testing):
    db = db_testing
    escenario = preparar_escenario(
        db,
        empresa_activa=False,
    )

    with pytest.raises(
        RegistroInvitacionError,
        match="empresa no está disponible",
    ):
        registrar(db, escenario)

    assert contar_usuarios(db, escenario["email"]) == 0


def test_correo_ya_registrado_es_rechazado(db_testing):
    db = db_testing
    escenario = preparar_escenario(db)

    usuario = Usuario(
        empresa_id=escenario["empresa_id"],
        nombre="Usuario Existente",
        email=escenario["email"],
        password_hash="hash-ficticio-no-utilizable",
        activo=False,
    )

    db.add(usuario)
    db.commit()

    with pytest.raises(
        RegistroInvitacionError,
        match="cuenta registrada",
    ):
        registrar(db, escenario)

    assert contar_usuarios(db, escenario["email"]) == 1


def test_nombre_invalido_es_rechazado(db_testing):
    db = db_testing
    escenario = preparar_escenario(db)

    with pytest.raises(
        RegistroInvitacionError,
        match="nombre",
    ):
        registrar(
            db,
            escenario,
            nombre=" ",
        )

    assert contar_usuarios(db, escenario["email"]) == 0


def test_password_corta_es_rechazada(db_testing):
    db = db_testing
    escenario = preparar_escenario(db)

    with pytest.raises(
        RegistroInvitacionError,
        match="contraseña",
    ):
        registrar(
            db,
            escenario,
            password="12345",
        )

    assert contar_usuarios(db, escenario["email"]) == 0


def test_error_en_hash_provoca_rollback(
    db_testing,
    monkeypatch,
):
    db = db_testing
    escenario = preparar_escenario(db)

    def hash_fallido(_password):
        raise RuntimeError("Fallo simulado del hasher")

    monkeypatch.setattr(
        "app.services.registration_service.hash_password",
        hash_fallido,
    )

    with pytest.raises(
        RuntimeError,
        match="Fallo simulado",
    ):
        registrar(db, escenario)

    assert contar_usuarios(db, escenario["email"]) == 0

    invitacion = db.get(
        InvitacionUsuario,
        escenario["invitacion_id"],
    )

    assert invitacion.estado == "pendiente"


def test_registro_no_devuelve_credenciales(db_testing):
    db = db_testing
    escenario = preparar_escenario(db)

    resultado = registrar(db, escenario)

    campos_prohibidos = {
        "token",
        "access_token",
        "refresh_token",
        "password",
        "password_hash",
        "sesion_id",
    }

    assert not campos_prohibidos.intersection(
        resultado.keys()
    )

    assert resultado["estado"] == "pendiente_aprobacion"
