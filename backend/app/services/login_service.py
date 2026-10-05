
"""
SalesIA Enterprise
FASE 05-C.1

Login empresarial clásico.

Reutiliza el servicio de sesiones desarrollado
en la FASE 05-A.4.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.rol import Rol

from app.services.session_service import crear_sesion


class LoginError(Exception):
    """Error controlado del inicio de sesión."""


def iniciar_sesion(
    db: Session,
    *,
    email: str,
    password: str,
) -> dict:
    """
    Autentica al usuario y delega la creación
    de sesión en session_service.

    La empresa se obtiene del usuario autenticado.
    Nunca se acepta empresa_id desde el frontend.
    """

    if (
        not isinstance(email, str)
        or not isinstance(password, str)
        or not email.strip()
        or not password
    ):
        raise LoginError("Credenciales inválidas.")

    correo = email.strip().lower()

    try:
        usuario = db.scalar(
            select(Usuario).where(
                Usuario.email == correo
            )
        )

        if usuario is None:
            raise LoginError("Credenciales inválidas.")

        if not verify_password(
            password,
            usuario.password_hash,
        ):
            raise LoginError("Credenciales inválidas.")

        if not usuario.activo:
            raise LoginError(
                "La cuenta todavía no está autorizada."
            )

        empresa = db.scalar(
            select(Empresa).where(
                Empresa.id == usuario.empresa_id,
                Empresa.activo.is_(True),
            )
        )

        if empresa is None:
            raise LoginError(
                "La empresa no se encuentra habilitada."
            )

        tiene_rol = db.scalar(
            select(Usuario.id).where(
                Usuario.id == usuario.id,
                Usuario.empresa_id == empresa.id,
                Usuario.roles.any(
                    Rol.empresa_id == empresa.id
                ),
            )
        )

        if tiene_rol is None:
            raise LoginError(
                "El usuario no tiene un rol empresarial asignado."
            )

        # Reutilizar el servicio de sesiones existente.
        resultado = crear_sesion(
            db,
            usuario_id=usuario.id,
            empresa_id=empresa.id,
        )

        return {
            **resultado,
            "usuario": {
                "id": usuario.id,
                "empresa_id": empresa.id,
                "nombre": usuario.nombre,
                "email": usuario.email,
            },
        }

    except Exception:
        db.rollback()
        raise
