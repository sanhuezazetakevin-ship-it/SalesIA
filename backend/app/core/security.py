
"""
SalesIA Enterprise
FASE 05-A.3 - Seguridad central.

- Hash de contraseñas con Argon2.
- JWT de acceso y renovación.
- Validación de firma, expiración y tipo de token.
"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings


# Instancia reutilizable del algoritmo Argon2.
password_hasher = PasswordHash.recommended()


class TokenInvalidoError(Exception):
    """El token no es válido o ha expirado."""


def hash_password(password: str) -> str:
    """Genera un hash seguro de la contraseña."""

    if not isinstance(password, str) or not password:
        raise ValueError("La contraseña no puede estar vacía.")

    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Comprueba una contraseña contra su hash almacenado."""

    if not password or not password_hash:
        return False

    try:
        return password_hasher.verify(
            password,
            password_hash,
        )
    except (ValueError, TypeError):
        return False


def _crear_token(
    *,
    usuario_id: int,
    empresa_id: int,
    sesion_id: int,
    tipo: str,
    expiracion: timedelta,
) -> str:
    """Construye un JWT firmado con los datos mínimos necesarios."""

    if usuario_id <= 0 or empresa_id <= 0 or sesion_id <= 0:
        raise ValueError("Los identificadores deben ser positivos.")

    if tipo not in {"access", "refresh"}:
        raise ValueError("Tipo de token no permitido.")

    ahora = datetime.now(timezone.utc)

    payload = {
        "sub": str(usuario_id),
        "empresa_id": empresa_id,
        "sid": sesion_id,
        "type": tipo,
        "jti": str(uuid.uuid4()),
        "iat": ahora,
        "nbf": ahora,
        "exp": ahora + expiracion,
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_access_token(
    *,
    usuario_id: int,
    empresa_id: int,
    sesion_id: int,
) -> str:
    """Crea un JWT de acceso de corta duración."""

    return _crear_token(
        usuario_id=usuario_id,
        empresa_id=empresa_id,
        sesion_id=sesion_id,
        tipo="access",
        expiracion=timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    )


def create_refresh_token(
    *,
    usuario_id: int,
    empresa_id: int,
    sesion_id: int,
) -> str:
    """Crea un JWT para renovación de sesión."""

    return _crear_token(
        usuario_id=usuario_id,
        empresa_id=empresa_id,
        sesion_id=sesion_id,
        tipo="refresh",
        expiracion=timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        ),
    )


def decode_token(token: str, expected_type: str) -> dict:
    """
    Verifica firma, expiración y estructura del JWT.

    Esta función NO sustituye la comprobación de la sesión
    persistida en PostgreSQL.
    """

    if expected_type not in {"access", "refresh"}:
        raise ValueError("Tipo esperado no permitido.")

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={
                "require": [
                    "sub",
                    "empresa_id",
                    "sid",
                    "type",
                    "jti",
                    "iat",
                    "nbf",
                    "exp",
                ]
            },
        )

        if payload.get("type") != expected_type:
            raise TokenInvalidoError(
                "El tipo de token no corresponde."
            )

        if (
            not isinstance(payload.get("sub"), str)
            or not payload["sub"].isdigit()
            or int(payload["sub"]) <= 0
        ):
            raise TokenInvalidoError(
                "Identificador de usuario inválido."
            )

        for campo in ("empresa_id", "sid"):
            valor = payload.get(campo)

            if type(valor) is not int or valor <= 0:
                raise TokenInvalidoError(
                    f"Campo inválido: {campo}"
                )

        uuid.UUID(payload["jti"])

        return payload

    except (
        InvalidTokenError,
        ValueError,
        TypeError,
        KeyError,
    ) as exc:
        raise TokenInvalidoError(
            "Token inválido o expirado."
        ) from exc
