
"""
SalesIA Enterprise
FASE 05-F.2A

Servicio empresarial RBAC.

Primera etapa:
- Validación del administrador.
- Comprobación de permisos efectivos.
- Aislamiento multiempresa.
- Consulta de roles y permisos.

Las operaciones de esta etapa son de solo lectura.
"""

from sqlalchemy import and_, select
from sqlalchemy.orm import Session
from sqlalchemy import update
from app.models.sesion import Sesion
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.permiso import Permiso
from app.models.auditoria import Auditoria
from sqlalchemy import func
from app.models.asociaciones import (
    usuarios_roles,
    roles_permisos,
)


PERMISO_VER_ROLES = "roles.ver"
PERMISO_ASIGNAR_ROLES = "roles.asignar"
PERMISO_REVOCAR_ROLES = "roles.revocar"


class RolServiceError(Exception):
    """Error controlado del servicio RBAC."""


def _obtener_permisos_efectivos(
    db: Session,
    *,
    usuario_id: int,
    empresa_id: int,
) -> set[str]:
    """
    Obtiene los permisos concedidos al usuario
    mediante sus roles en la empresa indicada.

    Los permisos se consultan directamente en PostgreSQL.
    """

    consulta = (
        select(Permiso.codigo)
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
        )
        .distinct()
    )

    return set(db.scalars(consulta).all())


def _validar_administrador_roles(
    db: Session,
    *,
    administrador_id: int,
    permiso_requerido: str,
) -> tuple[Usuario, Empresa, set[str]]:
    """
    Comprueba:
    - Identificador válido.
    - Usuario existente y activo.
    - Empresa existente y activa.
    - Permiso efectivo requerido.
    """

    if (
        type(administrador_id) is not int
        or administrador_id <= 0
    ):
        raise RolServiceError(
            "Identificador de administrador inválido."
        )

    administrador = db.scalar(
        select(Usuario).where(
            Usuario.id == administrador_id,
            Usuario.activo.is_(True),
        )
    )

    if administrador is None:
        raise RolServiceError(
            "El administrador no existe o está inactivo."
        )

    empresa = db.scalar(
        select(Empresa).where(
            Empresa.id == administrador.empresa_id,
            Empresa.activo.is_(True),
        )
    )

    if empresa is None:
        raise RolServiceError(
            "La empresa no existe o está inactiva."
        )

    permisos = _obtener_permisos_efectivos(
        db,
        usuario_id=administrador.id,
        empresa_id=empresa.id,
    )

    if permiso_requerido not in permisos:
        raise RolServiceError(
            "No tiene el permiso requerido para esta operación."
        )

    return administrador, empresa, permisos


def listar_roles_empresa(
    db: Session,
    *,
    administrador_id: int,
) -> list[dict]:
    """
    Lista únicamente los roles de la empresa
    a la que pertenece el administrador autenticado.

    Requiere roles.ver.
    No realiza commit.
    """

    _, empresa, _ = _validar_administrador_roles(
        db,
        administrador_id=administrador_id,
        permiso_requerido=PERMISO_VER_ROLES,
    )

    roles = db.scalars(
        select(Rol)
        .where(
            Rol.empresa_id == empresa.id,
        )
        .order_by(
            Rol.nombre,
            Rol.id,
        )
    ).all()

    return [
        {
            "rol_id": rol.id,
            "empresa_id": rol.empresa_id,
            "nombre": rol.nombre,
            "descripcion": rol.descripcion,
        }
        for rol in roles
    ]


def listar_permisos_rol(
    db: Session,
    *,
    administrador_id: int,
    rol_id: int,
) -> dict:
    """
    Consulta los permisos de un rol empresarial.

    Requiere roles.ver.
    Rechaza roles pertenecientes a otras empresas.
    No realiza commit.
    """

    if type(rol_id) is not int or rol_id <= 0:
        raise RolServiceError(
            "Identificador de rol inválido."
        )

    _, empresa, _ = _validar_administrador_roles(
        db,
        administrador_id=administrador_id,
        permiso_requerido=PERMISO_VER_ROLES,
    )

    rol = db.scalar(
        select(Rol).where(
            Rol.id == rol_id,
            Rol.empresa_id == empresa.id,
        )
    )

    if rol is None:
        raise RolServiceError(
            "El rol no existe en esta empresa."
        )

    permisos = db.scalars(
        select(Permiso.codigo)
        .select_from(roles_permisos)
        .join(
            Permiso,
            Permiso.id == roles_permisos.c.permiso_id,
        )
        .where(
            roles_permisos.c.rol_id == rol.id,
        )
        .order_by(Permiso.codigo)
    ).all()

    return {
        "rol_id": rol.id,
        "empresa_id": rol.empresa_id,
        "nombre": rol.nombre,
        "descripcion": rol.descripcion,
        "permisos": list(permisos),
    }

# ==========================================================
# FASE 05-F.3
# ASIGNACIÓN Y REVOCACIÓN SEGURA DE ROLES
# ==========================================================


def _permisos_del_rol(
    db: Session,
    *,
    rol_id: int,
) -> set[str]:
    return set(
        db.scalars(
            select(Permiso.codigo)
            .select_from(roles_permisos)
            .join(
                Permiso,
                Permiso.id == roles_permisos.c.permiso_id,
            )
            .where(roles_permisos.c.rol_id == rol_id)
        ).all()
    )


def _bloquear_empresa(
    db: Session,
    *,
    empresa_id: int,
) -> Empresa:
    """
    Serializa las modificaciones RBAC de una empresa.
    Todas las operaciones de escritura RBAC deben
    adquirir este bloqueo antes de modificar asignaciones.
    """
    empresa = db.scalar(
        select(Empresa)
        .where(
            Empresa.id == empresa_id,
            Empresa.activo.is_(True),
        )
        .with_for_update()
    )

    if empresa is None:
        raise RolServiceError(
            "La empresa no existe o está inactiva."
        )

    return empresa


def _obtener_usuario_y_rol(
    db: Session,
    *,
    empresa_id: int,
    usuario_id: int,
    rol_id: int,
) -> tuple[Usuario, Rol]:
    if type(usuario_id) is not int or usuario_id <= 0:
        raise RolServiceError(
            "Identificador de usuario inválido."
        )

    if type(rol_id) is not int or rol_id <= 0:
        raise RolServiceError(
            "Identificador de rol inválido."
        )

    usuario = db.scalar(
        select(Usuario)
        .where(
            Usuario.id == usuario_id,
            Usuario.empresa_id == empresa_id,
            Usuario.activo.is_(True),
        )
        .with_for_update()
    )

    if usuario is None:
        raise RolServiceError(
            "El usuario no existe, está inactivo "
            "o pertenece a otra empresa."
        )

    rol = db.scalar(
        select(Rol).where(
            Rol.id == rol_id,
            Rol.empresa_id == empresa_id,
        )
    )

    if rol is None:
        raise RolServiceError(
            "El rol no existe en esta empresa."
        )

    return usuario, rol


def _contar_administradores_rbac(
    db: Session,
    *,
    empresa_id: int,
) -> int:
    """
    Cuenta usuarios activos que conservan ambos permisos:
    roles.asignar y roles.revocar.

    La consulta se realiza contra las asignaciones actuales.
    """

    usuarios_con_permisos = (
        select(usuarios_roles.c.usuario_id)
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
        .join(
            Usuario,
            and_(
                Usuario.id == usuarios_roles.c.usuario_id,
                Usuario.empresa_id == usuarios_roles.c.empresa_id,
            ),
        )
        .where(
            Usuario.empresa_id == empresa_id,
            Usuario.activo.is_(True),
            Permiso.codigo.in_(
                ("roles.asignar", "roles.revocar")
            ),
        )
        .group_by(usuarios_roles.c.usuario_id)
        .having(
            func.count(func.distinct(Permiso.codigo)) == 2
        )
        .subquery()
    )

    return db.scalar(
        select(func.count()).select_from(usuarios_con_permisos)
    )


def asignar_rol_usuario(
    db: Session,
    *,
    administrador_id: int,
    usuario_id: int,
    rol_id: int,
) -> dict:
    """
    Asigna un rol empresarial con control de privilegios
    y auditoría transaccional.
    """

    try:
        administrador, empresa, _ = (
            _validar_administrador_roles(
                db,
                administrador_id=administrador_id,
                permiso_requerido=PERMISO_ASIGNAR_ROLES,
            )
        )

        _bloquear_empresa(
            db,
            empresa_id=empresa.id,
        )

        # Revalidar los permisos después de adquirir
        # el bloqueo empresarial.
        permisos_admin = _obtener_permisos_efectivos(
            db,
            usuario_id=administrador.id,
            empresa_id=empresa.id,
        )

        if PERMISO_ASIGNAR_ROLES not in permisos_admin:
            raise RolServiceError(
                "Ya no tiene permiso para asignar roles."
            )

        usuario, rol = _obtener_usuario_y_rol(
            db,
            empresa_id=empresa.id,
            usuario_id=usuario_id,
            rol_id=rol_id,
        )

        if usuario.id == administrador.id:
            raise RolServiceError(
                "No puede modificar sus propios roles."
            )

        permisos_rol = _permisos_del_rol(
            db,
            rol_id=rol.id,
        )

        if not permisos_rol.issubset(permisos_admin):
            raise RolServiceError(
                "No puede conceder permisos que no posee."
            )

        asignacion_existente = db.scalar(
            select(usuarios_roles.c.rol_id)
            .where(
                usuarios_roles.c.usuario_id == usuario.id,
                usuarios_roles.c.rol_id == rol.id,
                usuarios_roles.c.empresa_id == empresa.id,
            )
        )

        if asignacion_existente is not None:
            raise RolServiceError(
                "El usuario ya tiene asignado este rol."
            )

        db.execute(
            usuarios_roles.insert().values(
                usuario_id=usuario.id,
                rol_id=rol.id,
                empresa_id=empresa.id,
            )
        )

        db.add(
            Auditoria(
                empresa_id=empresa.id,
                usuario_id=administrador.id,
                accion="ACTUALIZAR",
                entidad="usuarios_roles",
                entidad_id=usuario.id,
                descripcion="Asignación administrativa de rol.",
                datos_anteriores={
                    "rol_id": None,
                },
                datos_nuevos={
                    "rol_id": rol.id,
                    "usuario_id": usuario.id,
                },
                origen="SISTEMA",
            )
        )

        db.flush()

        resultado = {
            "usuario_id": usuario.id,
            "empresa_id": empresa.id,
            "rol_id": rol.id,
            "rol_nombre": rol.nombre,
            "estado": "asignado",
            "administrador_id": administrador.id,
        }

        db.commit()
        return resultado

    except Exception:
        db.rollback()
        raise


def _revocar_sesiones_si_no_tiene_roles(
    db: Session,
    *,
    usuario_id: int,
    empresa_id: int,
) -> int:
    """
    Revoca las sesiones del usuario únicamente cuando
    ya no conserva ningún rol de su empresa.

    Debe ejecutarse dentro de la misma transacción
    que elimina la asignación del rol.

    Devuelve el número de sesiones revocadas.
    """

    tiene_otro_rol = db.scalar(
        select(usuarios_roles.c.rol_id)
        .where(
            usuarios_roles.c.usuario_id == usuario_id,
            usuarios_roles.c.empresa_id == empresa_id,
        )
        .limit(1)
    )

    if tiene_otro_rol is not None:
        return 0

    resultado = db.execute(
        update(Sesion)
        .where(
            Sesion.usuario_id == usuario_id,
            Sesion.empresa_id == empresa_id,
            Sesion.revocada.is_(False),
        )
        .values(revocada=True)
    )

    return resultado.rowcount

def revocar_rol_usuario(
    db: Session,
    *,
    administrador_id: int,
    usuario_id: int,
    rol_id: int,
) -> dict:
    """
    Revoca un rol empresarial.

    Impide eliminar la última cuenta activa con capacidad
    de asignar y revocar roles.
    """

    try:
        administrador, empresa, _ = (
            _validar_administrador_roles(
                db,
                administrador_id=administrador_id,
                permiso_requerido=PERMISO_REVOCAR_ROLES,
            )
        )

        _bloquear_empresa(
            db,
            empresa_id=empresa.id,
        )

        permisos_admin = _obtener_permisos_efectivos(
            db,
            usuario_id=administrador.id,
            empresa_id=empresa.id,
        )

        if PERMISO_REVOCAR_ROLES not in permisos_admin:
            raise RolServiceError(
                "Ya no tiene permiso para revocar roles."
            )

        usuario, rol = _obtener_usuario_y_rol(
            db,
            empresa_id=empresa.id,
            usuario_id=usuario_id,
            rol_id=rol_id,
        )

        if usuario.id == administrador.id:
            raise RolServiceError(
                "No puede modificar sus propios roles."
            )

        permisos_rol = _permisos_del_rol(
            db,
            rol_id=rol.id,
        )

        if not permisos_rol.issubset(permisos_admin):
            raise RolServiceError(
                "No puede revocar un rol con permisos "
                "superiores a los que posee."
            )

        asignacion = db.scalar(
            select(usuarios_roles.c.rol_id)
            .where(
                usuarios_roles.c.usuario_id == usuario.id,
                usuarios_roles.c.rol_id == rol.id,
                usuarios_roles.c.empresa_id == empresa.id,
            )
        )

        if asignacion is None:
            raise RolServiceError(
                "El usuario no tiene asignado este rol."
            )

        administradores_antes = _contar_administradores_rbac(
            db,
            empresa_id=empresa.id,
        )

        db.execute(
            usuarios_roles.delete().where(
                usuarios_roles.c.usuario_id == usuario.id,
                usuarios_roles.c.rol_id == rol.id,
                usuarios_roles.c.empresa_id == empresa.id,
            )
        )

        administradores_despues = _contar_administradores_rbac(
            db,
            empresa_id=empresa.id,
        )

        if (
            administradores_antes > 0
            and administradores_despues == 0
        ):
            raise RolServiceError(
                "No puede retirar el último administrador RBAC."
            )

        sesiones_revocadas = (
            _revocar_sesiones_si_no_tiene_roles(
                db,
                usuario_id=usuario.id,
                empresa_id=empresa.id,
            )
        )

        
    
        db.add(
            Auditoria(
                empresa_id=empresa.id,
                usuario_id=administrador.id,
                accion="ACTUALIZAR",
                entidad="usuarios_roles",
                entidad_id=usuario.id,
                descripcion="Revocación administrativa de rol.",
                datos_anteriores={
                    "rol_id": rol.id,
                    "usuario_id": usuario.id,
                },
                datos_nuevos={
                    "rol_id": None,
                },
                origen="SISTEMA",
            )
        )

        db.flush()

        
        resultado = {
            "usuario_id": usuario.id,
            "empresa_id": empresa.id,
            "rol_id": rol.id,
            "rol_nombre": rol.nombre,
            "estado": "revocado",
            "administrador_id": administrador.id,
            "sesiones_revocadas": sesiones_revocadas,
        }

        db.commit()
        return resultado


        db.commit()
        return resultado

    except Exception:
        db.rollback()
        raise
