
"""
SalesIA Enterprise
FASE 05-B.4

Registro empresarial mediante invitación.

Reglas:
- Invitación válida, vigente y de un solo uso.
- Empresa obtenida exclusivamente de la invitación.
- Correo obligatorio y coincidente.
- Contraseña protegida mediante Argon2.
- Usuario inicialmente inactivo.
- Aprobación administrativa obligatoria.
- Sin creación de sesiones ni emisión de JWT.
"""

import hashlib

from datetime import datetime, timezone

from email_validator import (
    EmailNotValidError,
    validate_email,
)

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.invitacion_usuario import InvitacionUsuario


class RegistroInvitacionError(Exception):
    """Error controlado del registro mediante invitación."""


def _normalizar_email(email: str) -> str:
    if not isinstance(email, str):
        raise RegistroInvitacionError(
            "El correo electrónico no es válido."
        )

    try:
        resultado = validate_email(
            email.strip(),
            check_deliverability=False,
        )

        return resultado.normalized.lower()

    except EmailNotValidError as exc:
        raise RegistroInvitacionError(
            "El correo electrónico no es válido."
        ) from exc


def _validar_nombre(nombre: str) -> str:
    if not isinstance(nombre, str):
        raise RegistroInvitacionError(
            "El nombre no es válido."
        )

    nombre = nombre.strip()

    if not 2 <= len(nombre) <= 120:
        raise RegistroInvitacionError(
            "El nombre debe contener entre 2 y 120 caracteres."
        )

    return nombre


def _validar_password(password: str) -> None:
    if not isinstance(password, str):
        raise RegistroInvitacionError(
            "La contraseña no es válida."
        )

    if not 12 <= len(password) <= 128:
        raise RegistroInvitacionError(
            "La contraseña debe contener entre "
            "12 y 128 caracteres."
        )

    if not password.strip():
        raise RegistroInvitacionError(
            "La contraseña no puede estar vacía."
        )


def _validar_token(token: str) -> str:
    if not isinstance(token, str):
        raise RegistroInvitacionError(
            "La invitación no es válida."
        )

    # token_urlsafe(32) genera un token de 43 caracteres.
    # No aceptamos espacios ni alteraciones del valor original.
    if (
        len(token) != 43
        or not all(
            caracter.isalnum() or caracter in "-_"
            for caracter in token
        )
    ):
        raise RegistroInvitacionError(
            "La invitación no es válida."
        )

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def registrar_con_invitacion(
    db: Session,
    *,
    token: str,
    nombre: str,
    email: str,
    password: str,
) -> dict:
    """
    Registra una cuenta pendiente de autorización administrativa.

    La invitación y el usuario se actualizan en una única transacción.
    No se emiten tokens de autenticación.
    """

    try:
        nombre_normalizado = _validar_nombre(nombre)
        email_normalizado = _normalizar_email(email)

        _validar_password(password)

        token_hash = _validar_token(token)

        # Bloquea la invitación hasta confirmar o revertir
        # la transacción. Impide consumirla simultáneamente.
        invitacion = db.scalar(
            select(InvitacionUsuario)
            .where(
                InvitacionUsuario.token_hash == token_hash
            )
            .with_for_update()
        )

        if invitacion is None:
            raise RegistroInvitacionError(
                "La invitación no es válida."
            )

        if invitacion.estado != "pendiente":
            raise RegistroInvitacionError(
                "La invitación ya no está disponible."
            )

        # Se obtiene la hora después de adquirir el bloqueo.
        ahora = datetime.now(timezone.utc)

        expiracion = invitacion.fecha_expiracion

        if expiracion.tzinfo is None:
            raise RegistroInvitacionError(
                "La fecha de expiración no tiene zona horaria."
            )

        if expiracion <= ahora:
            raise RegistroInvitacionError(
                "La invitación ha expirado."
            )

        if invitacion.email != email_normalizado:
            raise RegistroInvitacionError(
                "El correo no corresponde a la invitación."
            )

        # La empresa procede exclusivamente de PostgreSQL.
        # Nunca se recibe empresa_id desde el frontend.
        empresa = db.scalar(
            select(Empresa)
            .where(
                Empresa.id == invitacion.empresa_id,
                Empresa.activo.is_(True),
            )
        )

        if empresa is None:
            raise RegistroInvitacionError(
                "La empresa no está disponible."
            )

        usuario_existente = db.scalar(
            select(Usuario.id)
            .where(
                Usuario.email == email_normalizado
            )
        )

        if usuario_existente is not None:
            raise RegistroInvitacionError(
                "El correo ya pertenece a una cuenta registrada."
            )

        password_hash = hash_password(password)

        usuario = Usuario(
            empresa_id=invitacion.empresa_id,
            nombre=nombre_normalizado,
            email=email_normalizado,
            password_hash=password_hash,
            activo=False,
        )

        db.add(usuario)
        db.flush()

        invitacion.estado = "aceptada"

        resultado = {
            "usuario_id": usuario.id,
            "empresa_id": usuario.empresa_id,
            "nombre": usuario.nombre,
            "email": usuario.email,
            "activo": False,
            "estado": "pendiente_aprobacion",
            "mensaje": (
                "Registro completado. "
                "La cuenta requiere aprobación administrativa."
            ),
        }

        # Ambas operaciones se confirman conjuntamente.
        db.commit()

        return resultado

    except IntegrityError as exc:
        db.rollback()

        raise RegistroInvitacionError(
            "No fue posible completar el registro."
        ) from exc

    except Exception:
        db.rollback()
        raise
