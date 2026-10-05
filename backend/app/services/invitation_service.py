
"""
SalesIA Enterprise
FASE 05-B.3

Servicio de invitaciones empresariales.
"""

import hashlib
import secrets

from datetime import datetime, timedelta, timezone

from email_validator import EmailNotValidError, validate_email

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.permiso import Permiso
from app.models.invitacion_usuario import InvitacionUsuario
from app.models.asociaciones import usuarios_roles, roles_permisos


INVITACION_EXPIRE_HOURS = 48
PERMISO_INVITAR = "usuarios.crear"


class InvitacionError(Exception):
    """Error controlado del servicio de invitaciones."""


def _normalizar_email(email: str) -> str:
    try:
        resultado = validate_email(
            email.strip(),
            check_deliverability=False,
        )
        return resultado.normalized.lower()

    except (EmailNotValidError, AttributeError):
        raise InvitacionError("El correo electrónico no es válido.")


def _tiene_permiso_invitar(
    db: Session,
    *,
    usuario_id: int,
    empresa_id: int,
) -> bool:
    consulta = (
        select(Permiso.id)
        .select_from(usuarios_roles)
        .join(
            Rol,
            and_(
                Rol.id == usuarios_roles.c.rol_id,
                Rol.empresa_id == usuarios_roles.c.empresa_id,
            ),
        )
        .join(
            roles_permisos,
            roles_permisos.c.rol_id == Rol.id,
        )
        .join(
            Permiso,
            Permiso.id == roles_permisos.c.permiso_id,
        )
        .where(
            usuarios_roles.c.usuario_id == usuario_id,
            usuarios_roles.c.empresa_id == empresa_id,
            Permiso.codigo == PERMISO_INVITAR,
        )
        .limit(1)
    )

    return db.scalar(consulta) is not None


def crear_invitacion(
    db: Session,
    *,
    administrador_id: int,
    email_invitado: str,
) -> dict:
    """
    Crea una invitación para la empresa del administrador.

    El token original se devuelve una sola vez.
    En PostgreSQL únicamente se almacena su hash.
    """

    email = _normalizar_email(email_invitado)
    ahora = datetime.now(timezone.utc)

    try:
        administrador = db.scalar(
            select(Usuario).where(
                Usuario.id == administrador_id,
                Usuario.activo.is_(True),
            )
        )

        if administrador is None:
            raise InvitacionError(
                "El administrador no existe o está inactivo."
            )

        
        empresa = db.scalar(
            select(Empresa)
        .where(
            Empresa.id == administrador.empresa_id,
            Empresa.activo.is_(True),
        )
    .with_for_update()
)


        if empresa is None:
            raise InvitacionError(
                "La empresa no existe o está inactiva."
            )

        if not _tiene_permiso_invitar(
            db,
            usuario_id=administrador.id,
            empresa_id=empresa.id,
        ):
            raise InvitacionError(
                "No tiene permiso para invitar usuarios."
            )

        usuario_existente = db.scalar(
            select(Usuario.id).where(
                Usuario.email == email,
            )
        )

        if usuario_existente is not None:
            raise InvitacionError(
                "El correo ya pertenece a una cuenta registrada."
            )

        invitacion_pendiente = db.scalar(
            select(InvitacionUsuario.id).where(
                InvitacionUsuario.empresa_id == empresa.id,
                InvitacionUsuario.email == email,
                InvitacionUsuario.estado == "pendiente",
                InvitacionUsuario.fecha_expiracion > ahora,
            )
        )

        if invitacion_pendiente is not None:
            raise InvitacionError(
                "Ya existe una invitación vigente para este correo."
            )

        token = secrets.token_urlsafe(32)

        token_hash = hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

        expiracion = ahora + timedelta(
            hours=INVITACION_EXPIRE_HOURS
        )

        invitacion = InvitacionUsuario(
            empresa_id=empresa.id,
            invitado_por_id=administrador.id,
            email=email,
            token_hash=token_hash,
            estado="pendiente",
            fecha_expiracion=expiracion,
        )

        db.add(invitacion)
        db.flush()

        resultado = {
            "invitacion_id": invitacion.id,
            "empresa_id": empresa.id,
            "email": email,
            "token": token,
            "fecha_expiracion": expiracion.isoformat(),
        }

        db.commit()

        return resultado

    except Exception:
        db.rollback()
        raise
