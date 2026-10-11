
"""
SalesIA Enterprise
FASE 05-A.4 - Sesiones persistentes.

El campo token_hash almacena exclusivamente el hash
SHA-256 del refresh token.
"""

import hashlib
import hmac

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    TokenInvalidoError,
    create_access_token,
    create_refresh_token,
    decode_token,
)

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.sesion import Sesion


class SesionInvalidaError(Exception):
    """La sesión no existe, expiró o fue revocada."""


def _ahora():
    return datetime.now(timezone.utc)


def _hash_token(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()



def _verificar_usuario_empresa(
    db: Session,
    usuario_id: int,
    empresa_id: int,
):
    """
    Verifica que el usuario:
    - Exista y esté aprobado.
    - Pertenezca a la empresa indicada.
    - Tenga una empresa activa.
    - Conserve al menos un rol de su propia empresa.
    """

    # Una sola consulta en lugar de tres viajes a PostgreSQL.
    # EXISTS evita duplicados cuando el usuario tiene varios roles.
    # Las condiciones conservan el aislamiento de la empresa y los
    # controles de usuario/empresa activos en cada validación.
    usuario = db.execute(
        select(Usuario)
        .join(
            Empresa,
            Empresa.id == Usuario.empresa_id,
        )
        .where(
            Usuario.id == usuario_id,
            Usuario.empresa_id == empresa_id,
            Usuario.activo.is_(True),
            Empresa.id == empresa_id,
            Empresa.activo.is_(True),
            Usuario.roles.any(Rol.empresa_id == empresa_id),
        )
    ).scalar_one_or_none()

    if usuario is None:
        raise SesionInvalidaError(
            "Usuario, empresa o rol empresarial no autorizado."
        )

    return usuario



def crear_sesion(
    db: Session,
    *,
    usuario_id: int,
    empresa_id: int,
) -> dict:
    """
    Crea una sesión y genera los dos tokens.

    Debe llamarse después de verificar las credenciales.
    Esta función no comprueba la contraseña.
    """

    try:
        _verificar_usuario_empresa(
            db,
            usuario_id,
            empresa_id,
        )

        expiracion = _ahora() + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        # Valor temporal, sustituido antes del commit.
        sesion = Sesion(
            usuario_id=usuario_id,
            empresa_id=empresa_id,
            token_hash=hashlib.sha256(
                f"pending:{__import__('uuid').uuid4()}".encode()
            ).hexdigest(),
            fecha_expiracion=expiracion,
            revocada=False,
        )

        db.add(sesion)
        db.flush()

        access_token = create_access_token(
            usuario_id=usuario_id,
            empresa_id=empresa_id,
            sesion_id=sesion.id,
        )

        refresh_token = create_refresh_token(
            usuario_id=usuario_id,
            empresa_id=empresa_id,
            sesion_id=sesion.id,
        )

        sesion.token_hash = _hash_token(refresh_token)

        db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": (
                settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            ),
        }

    except Exception:
        db.rollback()
        raise


def validar_sesion(
    db: Session,
    *,
    access_token: str,
) -> Usuario:
    """
    Valida el access token y comprueba su sesión
    persistida en PostgreSQL.
    """

    try:
        payload = decode_token(
            access_token,
            expected_type="access",
        )
    except TokenInvalidoError as exc:
        raise SesionInvalidaError(
            "Token de acceso inválido."
        ) from exc

    usuario_id = int(payload["sub"])
    empresa_id = payload["empresa_id"]
    sesion_id = payload["sid"]

    sesion = db.execute(
        select(Sesion).where(
            Sesion.id == sesion_id,
            Sesion.usuario_id == usuario_id,
            Sesion.empresa_id == empresa_id,
            Sesion.revocada.is_(False),
            Sesion.fecha_expiracion > _ahora(),
        )
    ).scalar_one_or_none()

    if sesion is None:
        raise SesionInvalidaError(
            "La sesión no está vigente."
        )

    return _verificar_usuario_empresa(
        db,
        usuario_id,
        empresa_id,
    )


def renovar_sesion(
    db: Session,
    *,
    refresh_token: str,
) -> dict:
    """
    Renueva una sesión mediante rotación del refresh token.

    Bloquea la fila para impedir que dos renovaciones
    simultáneas reutilicen el mismo token.
    """

    try:
        payload = decode_token(
            refresh_token,
            expected_type="refresh",
        )
    except TokenInvalidoError as exc:
        raise SesionInvalidaError(
            "Refresh token inválido."
        ) from exc

    usuario_id = int(payload["sub"])
    empresa_id = payload["empresa_id"]
    sesion_id = payload["sid"]

    try:
        sesion = db.execute(
            select(Sesion)
            .where(
                Sesion.id == sesion_id,
                Sesion.usuario_id == usuario_id,
                Sesion.empresa_id == empresa_id,
            )
            .with_for_update()
        ).scalar_one_or_none()

        if (
            sesion is None
            or sesion.revocada
            or sesion.fecha_expiracion <= _ahora()
        ):
            raise SesionInvalidaError(
                "La sesión no está vigente."
            )

        hash_recibido = _hash_token(refresh_token)

        if not hmac.compare_digest(
            sesion.token_hash,
            hash_recibido,
        ):
            raise SesionInvalidaError(
                "El refresh token ya no es válido."
            )

        _verificar_usuario_empresa(
            db,
            usuario_id,
            empresa_id,
        )

        nuevo_access = create_access_token(
            usuario_id=usuario_id,
            empresa_id=empresa_id,
            sesion_id=sesion_id,
        )

        nuevo_refresh = create_refresh_token(
            usuario_id=usuario_id,
            empresa_id=empresa_id,
            sesion_id=sesion_id,
        )

        sesion.token_hash = _hash_token(nuevo_refresh)

        # La rotación conserva el límite original de
        # expiración de la sesión; no lo extiende.
        db.commit()

        return {
            "access_token": nuevo_access,
            "refresh_token": nuevo_refresh,
            "token_type": "bearer",
            "expires_in": (
                settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            ),
        }

    except Exception:
        db.rollback()
        raise


def revocar_sesion(
    db: Session,
    *,
    access_token: str,
) -> None:
    """Revoca la sesión asociada a un access token válido."""

    try:
        payload = decode_token(
            access_token,
            expected_type="access",
        )
    except TokenInvalidoError as exc:
        raise SesionInvalidaError(
            "Token de acceso inválido."
        ) from exc

    try:
        sesion = db.execute(
            select(Sesion)
            .where(
                Sesion.id == payload["sid"],
                Sesion.usuario_id == int(payload["sub"]),
                Sesion.empresa_id == payload["empresa_id"],
            )
            .with_for_update()
        ).scalar_one_or_none()

        if sesion is None:
            raise SesionInvalidaError(
                "Sesión inexistente."
            )

        sesion.revocada = True
        db.commit()

    except Exception:
        db.rollback()
        raise
