
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.core.security import create_access_token
from app.services import session_service as service


def preparar_db(resultado):
    """Simula una consulta SQLAlchemy."""
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = resultado
    return db


def test_token_invalido_rechazado():
    db = MagicMock()

    with pytest.raises(service.SesionInvalidaError):
        service.validar_sesion(
            db,
            access_token="token-invalido",
        )

    # No debe consultar PostgreSQL si el JWT es inválido.
    db.execute.assert_not_called()


def test_sesion_revocada_rechazada():
    token = create_access_token(
        usuario_id=1,
        empresa_id=1,
        sesion_id=10,
    )

    # La consulta no encuentra sesiones vigentes.
    db = preparar_db(None)

    with pytest.raises(service.SesionInvalidaError):
        service.validar_sesion(
            db,
            access_token=token,
        )


def test_sesion_valida_verifica_usuario_y_empresa(monkeypatch):
    token = create_access_token(
        usuario_id=1,
        empresa_id=1,
        sesion_id=10,
    )

    sesion = SimpleNamespace(
        id=10,
        usuario_id=1,
        empresa_id=1,
        revocada=False,
        fecha_expiracion=(
            datetime.now(timezone.utc)
            + timedelta(hours=1)
        ),
    )

    db = preparar_db(sesion)

    usuario = SimpleNamespace(
        id=1,
        empresa_id=1,
        activo=True,
    )

    def verificar(db_recibida, usuario_id, empresa_id):
        assert db_recibida is db
        assert usuario_id == 1
        assert empresa_id == 1
        return usuario

    monkeypatch.setattr(
        service,
        "_verificar_usuario_empresa",
        verificar,
    )

    resultado = service.validar_sesion(
        db,
        access_token=token,
    )

    assert resultado is usuario
    db.execute.assert_called_once()

# ==========================================================
# FASE 05-A.4-B: creación, rotación y revocación
# ==========================================================

import hashlib

from app.core.security import (
    create_refresh_token,
    decode_token,
)


def test_crear_sesion_guarda_hash_y_no_token_plano(monkeypatch):
    db = MagicMock()

    monkeypatch.setattr(
        service,
        "_verificar_usuario_empresa",
        lambda db, usuario_id, empresa_id: SimpleNamespace(id=1),
    )

    def asignar_id():
        # Simula el ID generado por PostgreSQL tras flush().
        sesion = db.add.call_args.args[0]
        sesion.id = 10

    db.flush.side_effect = asignar_id

    resultado = service.crear_sesion(
        db,
        usuario_id=1,
        empresa_id=1,
    )

    sesion = db.add.call_args.args[0]
    refresh = resultado["refresh_token"]

    assert sesion.id == 10
    assert sesion.token_hash != refresh
    assert sesion.token_hash == hashlib.sha256(
        refresh.encode("utf-8")
    ).hexdigest()

    assert decode_token(
        resultado["access_token"], "access"
    )["sid"] == 10

    db.commit.assert_called_once()


def test_renovacion_invalida_refresh_anterior(monkeypatch):
    refresh_original = create_refresh_token(
        usuario_id=1,
        empresa_id=1,
        sesion_id=10,
    )

    sesion = SimpleNamespace(
        id=10,
        usuario_id=1,
        empresa_id=1,
        revocada=False,
        fecha_expiracion=(
            datetime.now(timezone.utc) + timedelta(days=1)
        ),
        token_hash=service._hash_token(refresh_original),
    )

    db = preparar_db(sesion)

    monkeypatch.setattr(
        service,
        "_verificar_usuario_empresa",
        lambda *args: SimpleNamespace(id=1),
    )

    resultado = service.renovar_sesion(
        db,
        refresh_token=refresh_original,
    )

    nuevo_refresh = resultado["refresh_token"]

    assert nuevo_refresh != refresh_original
    assert sesion.token_hash == service._hash_token(nuevo_refresh)
    db.commit.assert_called_once()

    # El refresh anterior ya no coincide con el hash almacenado.
    with pytest.raises(service.SesionInvalidaError):
        service.renovar_sesion(
            db,
            refresh_token=refresh_original,
        )


def test_sesion_expirada_no_puede_renovarse():
    refresh = create_refresh_token(
        usuario_id=1,
        empresa_id=1,
        sesion_id=10,
    )

    sesion = SimpleNamespace(
        id=10,
        usuario_id=1,
        empresa_id=1,
        revocada=False,
        fecha_expiracion=(
            datetime.now(timezone.utc) - timedelta(minutes=1)
        ),
        token_hash=service._hash_token(refresh),
    )

    db = preparar_db(sesion)

    with pytest.raises(service.SesionInvalidaError):
        service.renovar_sesion(
            db,
            refresh_token=refresh,
        )

    db.commit.assert_not_called()


def test_revocar_sesion_marca_registro_y_confirma():
    token = create_access_token(
        usuario_id=1,
        empresa_id=1,
        sesion_id=10,
    )

    sesion = SimpleNamespace(
        id=10,
        usuario_id=1,
        empresa_id=1,
        revocada=False,
    )

    db = preparar_db(sesion)

    service.revocar_sesion(
        db,
        access_token=token,
    )

    assert sesion.revocada is True
    db.commit.assert_called_once()

    # Simulamos que la consulta de sesiones vigentes
    # ya no devuelve la sesión revocada.
    db.execute.return_value.scalar_one_or_none.return_value = None

    with pytest.raises(service.SesionInvalidaError):
        service.validar_sesion(
            db,
            access_token=token,
        )
