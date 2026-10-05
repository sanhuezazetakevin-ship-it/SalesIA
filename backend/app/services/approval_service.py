"""
SalesIA Enterprise
FASE 05-B.5

Servicio de aprobación administrativa de usuarios.

Reglas:
- Administrador activo.
- Empresa activa.
- Permiso usuarios.autorizar obligatorio.
- Aislamiento estricto entre empresas.
- Registro previo mediante invitación aceptada.
- Registro de auditoría transaccional.
- Sin creación de sesiones ni JWT.
"""

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.permiso import Permiso
from app.models.auditoria import Auditoria
from app.models.invitacion_usuario import InvitacionUsuario

from app.models.asociaciones import (
    usuarios_roles,
    roles_permisos,
)


PERMISO_AUTORIZAR = "usuarios.autorizar"


class AprobacionError(Exception):
    """Error controlado del servicio de aprobación."""


def _tiene_permiso_autorizar(
    db: Session,
    *,
    usuario_id: int,
    empresa_id: int,
) -> bool:
    """
    Comprueba si un usuario posee el permiso
    usuarios.autorizar mediante alguno de sus roles
    dentro de la empresa correspondiente.
    """

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
            Permiso.codigo == PERMISO_AUTORIZAR,
        )
        .limit(1)
    )

    return db.scalar(consulta) is not None


def _validar_administrador(
    db: Session,
    *,
    administrador_id: int,
) -> tuple[Usuario, Empresa]:
    """
    Valida:
    - Identificador correcto.
    - Administrador existente y activo.
    - Empresa existente y activa.
    - Permiso usuarios.autorizar.
    """

    if (
        type(administrador_id) is not int
        or administrador_id <= 0
    ):
        raise AprobacionError(
            "Identificador de administrador inválido."
        )

    administrador = db.scalar(
        select(Usuario).where(
            Usuario.id == administrador_id,
            Usuario.activo.is_(True),
        )
    )

    if administrador is None:
        raise AprobacionError(
            "El administrador no existe o está inactivo."
        )

    empresa = db.scalar(
        select(Empresa).where(
            Empresa.id == administrador.empresa_id,
            Empresa.activo.is_(True),
        )
    )

    if empresa is None:
        raise AprobacionError(
            "La empresa no existe o está inactiva."
        )

    if not _tiene_permiso_autorizar(
        db,
        usuario_id=administrador.id,
        empresa_id=empresa.id,
    ):
        raise AprobacionError(
            "No tiene permiso para autorizar usuarios."
        )

    return administrador, empresa


def listar_usuarios_pendientes(
    db: Session,
    *,
    administrador_id: int,
) -> list[dict]:
    """
    Lista exclusivamente usuarios que:

    1. Pertenecen a la empresa del administrador.
    2. Se encuentran inactivos.
    3. Tienen una invitación aceptada.

    No modifica registros ni realiza commit.
    """

    _, empresa = _validar_administrador(
        db,
        administrador_id=administrador_id,
    )

    invitacion_aceptada = (
        select(InvitacionUsuario.id)
        .where(
            InvitacionUsuario.empresa_id == Usuario.empresa_id,
            InvitacionUsuario.email == Usuario.email,
            InvitacionUsuario.estado == "aceptada",
        )
        .exists()
    )

    usuarios = db.scalars(
        select(Usuario)
        .where(
            Usuario.empresa_id == empresa.id,
            Usuario.activo.is_(False),
            invitacion_aceptada,
        )
        .order_by(
            Usuario.created_at,
            Usuario.id,
        )
    ).all()

    return [
        {
            "usuario_id": usuario.id,
            "empresa_id": usuario.empresa_id,
            "nombre": usuario.nombre,
            "email": usuario.email,
            "activo": usuario.activo,
            "created_at": usuario.created_at.isoformat(),
        }
        for usuario in usuarios
    ]


def aprobar_usuario(
    db: Session,
    *,
    administrador_id: int,
    usuario_id: int,
) -> dict:
    """
    Aprueba una cuenta registrada mediante invitación.

    La activación del usuario y el registro de auditoría
    se confirman dentro de una misma transacción.

    No genera sesiones ni tokens JWT.
    """

    try:
        # 1. Validar identificador del usuario.

        if type(usuario_id) is not int or usuario_id <= 0:
            raise AprobacionError(
                "Identificador de usuario inválido."
            )

        # 2. Validar administrador, empresa y permiso.

        administrador, empresa = _validar_administrador(
            db,
            administrador_id=administrador_id,
        )

        # 3. Buscar y bloquear el usuario.
        # El filtro por empresa impide aprobaciones cruzadas.

        usuario = db.scalar(
            select(Usuario)
            .where(
                Usuario.id == usuario_id,
                Usuario.empresa_id == empresa.id,
            )
            .with_for_update()
        )

        if usuario is None:
            raise AprobacionError(
                "El usuario no existe en esta empresa."
            )

        # 4. Impedir aprobaciones duplicadas.

        if usuario.activo:
            raise AprobacionError(
                "El usuario ya se encuentra activo."
            )

        # 5. Comprobar que completó el registro
        # mediante una invitación aceptada.

        invitacion_aceptada = db.scalar(
            select(InvitacionUsuario.id)
            .where(
                InvitacionUsuario.empresa_id == empresa.id,
                InvitacionUsuario.email == usuario.email,
                InvitacionUsuario.estado == "aceptada",
            )
            .limit(1)
        )

        if invitacion_aceptada is None:
            raise AprobacionError(
                "El usuario no tiene un registro por invitación completado."
            )

        # 6. Activar la cuenta.

        usuario.activo = True

        # 7. Registrar la aprobación en auditoría.
        # Se utiliza la misma transacción.

        auditoria = Auditoria(
            empresa_id=empresa.id,
            usuario_id=administrador.id,
            accion="ACTUALIZAR",
            entidad="usuarios",
            entidad_id=usuario.id,
            descripcion="Aprobación administrativa de cuenta.",
            datos_anteriores={
                "activo": False,
            },
            datos_nuevos={
                "activo": True,
            },
            origen="SISTEMA",
        )

        db.add(auditoria)

        # Verificar que las operaciones puedan
        # persistirse antes de confirmar.

        db.flush()

        resultado = {
            "usuario_id": usuario.id,
            "empresa_id": usuario.empresa_id,
            "nombre": usuario.nombre,
            "email": usuario.email,
            "activo": True,
            "estado": "aprobado",
            "aprobado_por_id": administrador.id,
        }

        # 8. Confirmar activación y auditoría juntas.

        db.commit()

        return resultado

    except Exception:
        db.rollback()
        raise