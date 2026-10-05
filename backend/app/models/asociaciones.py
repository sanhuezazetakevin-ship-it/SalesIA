
from sqlalchemy import (
    Column,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    PrimaryKeyConstraint,
    Table,
)

from app.database.base import Base


usuarios_roles = Table(
    "usuarios_roles",
    Base.metadata,

    Column("usuario_id", Integer, nullable=False),
    Column("rol_id", Integer, nullable=False),
    Column("empresa_id", Integer, nullable=False),

    PrimaryKeyConstraint(
        "usuario_id",
        "rol_id",
        name="pk_usuarios_roles"
    ),

    ForeignKeyConstraint(
        ["usuario_id", "empresa_id"],
        ["usuarios.id", "usuarios.empresa_id"],
        name="fk_ur_usuario_empresa",
        ondelete="CASCADE"
    ),

    ForeignKeyConstraint(
        ["rol_id", "empresa_id"],
        ["roles.id", "roles.empresa_id"],
        name="fk_ur_rol_empresa",
        ondelete="CASCADE"
    )
)


roles_permisos = Table(
    "roles_permisos",
    Base.metadata,

    Column(
        "rol_id",
        Integer,
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False
    ),

    Column(
        "permiso_id",
        Integer,
        ForeignKey("permisos.id", ondelete="CASCADE"),
        nullable=False
    ),

    PrimaryKeyConstraint(
        "rol_id",
        "permiso_id",
        name="pk_roles_permisos"
    )
)
