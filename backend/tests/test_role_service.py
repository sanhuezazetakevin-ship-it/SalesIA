
"""
SalesIA Enterprise
FASE 05-F.2B

Pruebas del servicio RBAC:
- Consulta de roles.
- Permisos efectivos.
- Aislamiento multiempresa.
- Validación de identificadores.

Todas las operaciones utilizan db_testing.
"""

import uuid

import pytest

from sqlalchemy import select

from app.core.security import hash_password

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.permiso import Permiso
import hashlib

from datetime import datetime, timedelta, timezone

from app.models.sesion import Sesion
from app.models.asociaciones import roles_permisos

from app.services.role_service import (
    RolServiceError,
    listar_roles_empresa,
    listar_permisos_rol,
)


def crear_escenario_rbac(
    db,
    *,
    conceder_roles_ver=True,
):
    identificador = uuid.uuid4().hex

    empresa = Empresa(
        razon_social=f"Empresa RBAC {identificador[:12]}",
        ruc=str(uuid.uuid4().int % 10**11).zfill(11),
        moneda_base="PEN",
        activo=True,
    )

    db.add(empresa)
    db.flush()

    rol_administrador = Rol(
        empresa_id=empresa.id,
        nombre=f"ADMIN_TEST_{identificador[:8]}",
        descripcion="Administrador de pruebas RBAC",
    )

    rol_operativo = Rol(
        empresa_id=empresa.id,
        nombre=f"OPERATIVO_TEST_{identificador[:8]}",
        descripcion="Rol operativo de pruebas RBAC",
    )

    db.add_all([rol_administrador, rol_operativo])
    db.flush()

    codigo_permiso = "roles.ver"

    permiso = db.scalar(
        select(Permiso).where(
            Permiso.codigo == codigo_permiso
        )
    )

    if permiso is None:
        permiso = Permiso(
            codigo=codigo_permiso,
            descripcion="Consultar roles empresariales",
        )
        db.add(permiso)
        db.flush()

    if conceder_roles_ver:
        db.execute(
            roles_permisos.insert().values(
                rol_id=rol_administrador.id,
                permiso_id=permiso.id,
            )
        )

    administrador = Usuario(
        empresa_id=empresa.id,
        nombre="Administrador RBAC Testing",
        email=f"admin-rbac-{identificador}@example.com",
        password_hash=hash_password("ClaveRBAC#2026"),
        activo=True,
    )

    db.add(administrador)
    db.flush()

    administrador.roles.append(rol_administrador)
    db.flush()

    return {
        "empresa": empresa,
        "administrador": administrador,
        "rol_administrador": rol_administrador,
        "rol_operativo": rol_operativo,
    }


def test_administrador_puede_listar_roles_propios(db_testing):
    escenario = crear_escenario_rbac(db_testing)

    resultado = listar_roles_empresa(
        db_testing,
        administrador_id=escenario["administrador"].id,
    )

    ids = {rol["rol_id"] for rol in resultado}

    assert escenario["rol_administrador"].id in ids
    assert escenario["rol_operativo"].id in ids

    assert all(
        rol["empresa_id"] == escenario["empresa"].id
        for rol in resultado
    )


def test_usuario_sin_permiso_no_puede_listar_roles(db_testing):
    escenario = crear_escenario_rbac(
        db_testing,
        conceder_roles_ver=False,
    )

    with pytest.raises(RolServiceError):
        listar_roles_empresa(
            db_testing,
            administrador_id=escenario["administrador"].id,
        )


def test_consulta_permisos_de_rol_propio(db_testing):
    escenario = crear_escenario_rbac(db_testing)

    resultado = listar_permisos_rol(
        db_testing,
        administrador_id=escenario["administrador"].id,
        rol_id=escenario["rol_administrador"].id,
    )

    assert resultado["rol_id"] == escenario["rol_administrador"].id
    assert resultado["empresa_id"] == escenario["empresa"].id
    assert "roles.ver" in resultado["permisos"]


def test_no_puede_consultar_rol_de_otra_empresa(db_testing):
    empresa_a = crear_escenario_rbac(db_testing)
    empresa_b = crear_escenario_rbac(db_testing)

    with pytest.raises(RolServiceError):
        listar_permisos_rol(
            db_testing,
            administrador_id=empresa_a["administrador"].id,
            rol_id=empresa_b["rol_operativo"].id,
        )


def test_rechaza_identificadores_invalidos(db_testing):
    escenario = crear_escenario_rbac(db_testing)

    with pytest.raises(RolServiceError):
        listar_roles_empresa(
            db_testing,
            administrador_id=0,
        )

    with pytest.raises(RolServiceError):
        listar_permisos_rol(
            db_testing,
            administrador_id=escenario["administrador"].id,
            rol_id=-1,
        )

# ==========================================================
# FASE 05-F.3A
# PRUEBAS DE ASIGNACIÓN Y REVOCACIÓN RBAC
# ==========================================================

from app.models.auditoria import Auditoria
from app.models.asociaciones import usuarios_roles

from app.services.role_service import (
    asignar_rol_usuario,
    revocar_rol_usuario,
)


def preparar_escenario_escritura(db):
    """
    Crea un administrador con permisos RBAC completos
    y un segundo usuario activo de la misma empresa.
    """

    escenario = crear_escenario_rbac(db)

    administrador = escenario["administrador"]
    empresa = escenario["empresa"]
    rol_admin = escenario["rol_administrador"]
    rol_operativo = escenario["rol_operativo"]

    for codigo in ("roles.asignar", "roles.revocar"):
        permiso = db.scalar(
            select(Permiso).where(Permiso.codigo == codigo)
        )

        if permiso is None:
            permiso = Permiso(
                codigo=codigo,
                descripcion=f"Permiso de prueba: {codigo}",
            )
            db.add(permiso)
            db.flush()

        db.execute(
            roles_permisos.insert().values(
                rol_id=rol_admin.id,
                permiso_id=permiso.id,
            )
        )

    # El administrador puede conceder todos los permisos
    # incluidos en este rol operativo.
    permiso_ver = db.scalar(
        select(Permiso).where(Permiso.codigo == "roles.ver")
    )

    db.execute(
        roles_permisos.insert().values(
            rol_id=rol_operativo.id,
            permiso_id=permiso_ver.id,
        )
    )

    identificador = uuid.uuid4().hex

    usuario = Usuario(
        empresa_id=empresa.id,
        nombre="Usuario Operativo RBAC",
        email=f"operativo-{identificador}@example.com",
        password_hash=hash_password("ClaveRBAC#2026"),
        activo=True,
    )

    db.add(usuario)
    db.flush()

    escenario["usuario_operativo"] = usuario

    # Confirmar únicamente el escenario de prueba.
    # La fixture db_testing conserva su transacción exterior,
    # que se revertirá al finalizar el test.
    db.commit()

    return escenario


def test_asignacion_y_revocacion_generan_auditoria(db_testing):
    escenario = preparar_escenario_escritura(db_testing)

    admin = escenario["administrador"]
    usuario = escenario["usuario_operativo"]
    rol = escenario["rol_operativo"]

    asignacion = asignar_rol_usuario(
        db_testing,
        administrador_id=admin.id,
        usuario_id=usuario.id,
        rol_id=rol.id,
    )

    assert asignacion["estado"] == "asignado"
    assert asignacion["administrador_id"] == admin.id

    existe = db_testing.scalar(
        select(usuarios_roles.c.rol_id).where(
            usuarios_roles.c.usuario_id == usuario.id,
            usuarios_roles.c.rol_id == rol.id,
        )
    )

    assert existe == rol.id

    revocacion = revocar_rol_usuario(
        db_testing,
        administrador_id=admin.id,
        usuario_id=usuario.id,
        rol_id=rol.id,
    )

    assert revocacion["estado"] == "revocado"

    existe_despues = db_testing.scalar(
        select(usuarios_roles.c.rol_id).where(
            usuarios_roles.c.usuario_id == usuario.id,
            usuarios_roles.c.rol_id == rol.id,
        )
    )

    assert existe_despues is None

    auditorias = db_testing.scalars(
        select(Auditoria).where(
            Auditoria.empresa_id == escenario["empresa"].id,
            Auditoria.usuario_id == admin.id,
            Auditoria.entidad == "usuarios_roles",
            Auditoria.entidad_id == usuario.id,
        )
    ).all()

    assert len(auditorias) == 2

    descripciones = {
        auditoria.descripcion for auditoria in auditorias
    }

    assert "Asignación administrativa de rol." in descripciones
    assert "Revocación administrativa de rol." in descripciones


def test_no_permite_asignacion_duplicada(db_testing):
    escenario = preparar_escenario_escritura(db_testing)

    datos = {
        "administrador_id": escenario["administrador"].id,
        "usuario_id": escenario["usuario_operativo"].id,
        "rol_id": escenario["rol_operativo"].id,
    }

    asignar_rol_usuario(db_testing, **datos)

    with pytest.raises(RolServiceError):
        asignar_rol_usuario(db_testing, **datos)

    auditorias = db_testing.scalars(
        select(Auditoria).where(
            Auditoria.entidad == "usuarios_roles",
            Auditoria.entidad_id == datos["usuario_id"],
        )
    ).all()

    assert len(auditorias) == 1


def test_no_permite_asignar_rol_de_otra_empresa(db_testing):
    empresa_a = preparar_escenario_escritura(db_testing)
    empresa_b = preparar_escenario_escritura(db_testing)

    with pytest.raises(RolServiceError):
        asignar_rol_usuario(
            db_testing,
            administrador_id=empresa_a["administrador"].id,
            usuario_id=empresa_a["usuario_operativo"].id,
            rol_id=empresa_b["rol_operativo"].id,
        )

    with pytest.raises(RolServiceError):
        asignar_rol_usuario(
            db_testing,
            administrador_id=empresa_a["administrador"].id,
            usuario_id=empresa_b["usuario_operativo"].id,
            rol_id=empresa_a["rol_operativo"].id,
        )


def test_no_permite_escalada_de_privilegios(db_testing):
    escenario = preparar_escenario_escritura(db_testing)

    permiso_superior = db_testing.scalar(
        select(Permiso).where(
            Permiso.codigo == "configuracion.editar"
        )
    )

    if permiso_superior is None:
        permiso_superior = Permiso(
            codigo="configuracion.editar",
            descripcion="Modificar configuración empresarial",
        )
        db_testing.add(permiso_superior)
        db_testing.flush()

    # Se concede al rol operativo, pero NO al administrador.
    db_testing.execute(
        roles_permisos.insert().values(
            rol_id=escenario["rol_operativo"].id,
            permiso_id=permiso_superior.id,
        )
    )

    with pytest.raises(RolServiceError):
        asignar_rol_usuario(
            db_testing,
            administrador_id=escenario["administrador"].id,
            usuario_id=escenario["usuario_operativo"].id,
            rol_id=escenario["rol_operativo"].id,
        )

    asignacion = db_testing.scalar(
        select(usuarios_roles.c.rol_id).where(
            usuarios_roles.c.usuario_id ==
            escenario["usuario_operativo"].id,
            usuarios_roles.c.rol_id ==
            escenario["rol_operativo"].id,
        )
    )

    assert asignacion is None


def test_administrador_no_puede_modificar_sus_roles(db_testing):
    escenario = preparar_escenario_escritura(db_testing)

    admin_id = escenario["administrador"].id

    with pytest.raises(RolServiceError):
        asignar_rol_usuario(
            db_testing,
            administrador_id=admin_id,
            usuario_id=admin_id,
            rol_id=escenario["rol_operativo"].id,
        )

    with pytest.raises(RolServiceError):
        revocar_rol_usuario(
            db_testing,
            administrador_id=admin_id,
            usuario_id=admin_id,
            rol_id=escenario["rol_administrador"].id,
        )

    # El administrador debe conservar su rol original.
    asignacion_original = db_testing.scalar(
        select(usuarios_roles.c.rol_id).where(
            usuarios_roles.c.usuario_id == admin_id,
            usuarios_roles.c.rol_id ==
            escenario["rol_administrador"].id,
        )
    )

    assert asignacion_original == escenario["rol_administrador"].id


def test_no_permite_revocar_rol_inexistente(db_testing):
    escenario = preparar_escenario_escritura(db_testing)

    with pytest.raises(RolServiceError):
        revocar_rol_usuario(
            db_testing,
            administrador_id=escenario["administrador"].id,
            usuario_id=escenario["usuario_operativo"].id,
            rol_id=escenario["rol_operativo"].id,
        )

# ==========================================================
# FASE 05-F.3B.1
# PRUEBAS DE REVOCACIÓN AUTOMÁTICA DE SESIONES
# ==========================================================


def crear_sesion_testing(
    db,
    *,
    usuario_id: int,
    empresa_id: int,
) -> Sesion:
    """
    Crea una sesión ficticia únicamente para Testing.
    No genera ni almacena tokens reales.
    """

    identificador = uuid.uuid4().hex

    sesion = Sesion(
        usuario_id=usuario_id,
        empresa_id=empresa_id,
        token_hash=hashlib.sha256(
            identificador.encode("utf-8")
        ).hexdigest(),
        fecha_expiracion=(
            datetime.now(timezone.utc)
            + timedelta(days=1)
        ),
        revocada=False,
    )

    db.add(sesion)
    db.flush()

    return sesion


def test_revocar_ultimo_rol_revoca_sesiones(db_testing):
    escenario = preparar_escenario_escritura(db_testing)

    administrador = escenario["administrador"]
    usuario = escenario["usuario_operativo"]
    rol = escenario["rol_operativo"]

    asignar_rol_usuario(
        db_testing,
        administrador_id=administrador.id,
        usuario_id=usuario.id,
        rol_id=rol.id,
    )

    sesion_1 = crear_sesion_testing(
        db_testing,
        usuario_id=usuario.id,
        empresa_id=escenario["empresa"].id,
    )

    sesion_2 = crear_sesion_testing(
        db_testing,
        usuario_id=usuario.id,
        empresa_id=escenario["empresa"].id,
    )

    db_testing.commit()

    resultado = revocar_rol_usuario(
        db_testing,
        administrador_id=administrador.id,
        usuario_id=usuario.id,
        rol_id=rol.id,
    )

    assert resultado["estado"] == "revocado"
    assert resultado["sesiones_revocadas"] == 2

    sesiones = db_testing.scalars(
        select(Sesion).where(
            Sesion.id.in_([sesion_1.id, sesion_2.id])
        )
    ).all()

    assert len(sesiones) == 2
    assert all(sesion.revocada for sesion in sesiones)


def test_conservar_otro_rol_mantiene_sesion(db_testing):
    escenario = preparar_escenario_escritura(db_testing)

    administrador = escenario["administrador"]
    usuario = escenario["usuario_operativo"]
    rol_operativo = escenario["rol_operativo"]

    identificador = uuid.uuid4().hex

    segundo_rol = Rol(
        empresa_id=escenario["empresa"].id,
        nombre=f"ROL_ADICIONAL_{identificador[:8]}",
        descripcion="Segundo rol empresarial de Testing",
    )

    db_testing.add(segundo_rol)
    db_testing.flush()

    asignar_rol_usuario(
        db_testing,
        administrador_id=administrador.id,
        usuario_id=usuario.id,
        rol_id=rol_operativo.id,
    )

    asignar_rol_usuario(
        db_testing,
        administrador_id=administrador.id,
        usuario_id=usuario.id,
        rol_id=segundo_rol.id,
    )

    sesion = crear_sesion_testing(
        db_testing,
        usuario_id=usuario.id,
        empresa_id=escenario["empresa"].id,
    )

    db_testing.commit()

    resultado = revocar_rol_usuario(
        db_testing,
        administrador_id=administrador.id,
        usuario_id=usuario.id,
        rol_id=rol_operativo.id,
    )

    assert resultado["sesiones_revocadas"] == 0

    db_testing.refresh(sesion)

    assert sesion.revocada is False

    rol_restante = db_testing.scalar(
        select(usuarios_roles.c.rol_id).where(
            usuarios_roles.c.usuario_id == usuario.id,
            usuarios_roles.c.rol_id == segundo_rol.id,
        )
    )

    assert rol_restante == segundo_rol.id


def test_revocacion_rechazada_no_modifica_sesion(db_testing):
    escenario = preparar_escenario_escritura(db_testing)

    administrador = escenario["administrador"]

    sesion = crear_sesion_testing(
        db_testing,
        usuario_id=administrador.id,
        empresa_id=escenario["empresa"].id,
    )

    db_testing.commit()

    # La autorrevocación debe ser rechazada.
    with pytest.raises(RolServiceError):
        revocar_rol_usuario(
            db_testing,
            administrador_id=administrador.id,
            usuario_id=administrador.id,
            rol_id=escenario["rol_administrador"].id,
        )

    db_testing.refresh(sesion)

    assert sesion.revocada is False

    rol_original = db_testing.scalar(
        select(usuarios_roles.c.rol_id).where(
            usuarios_roles.c.usuario_id == administrador.id,
            usuarios_roles.c.rol_id ==
            escenario["rol_administrador"].id,
        )
    )

    assert rol_original == escenario["rol_administrador"].id

# ==========================================================
# FASE 05-F.3B.2
# PROTECCIÓN DE CAPACIDADES ADMINISTRATIVAS
# ==========================================================

from app.services.role_service import (
    _contar_administradores_rbac,
)


def test_administrador_con_permisos_distribuidos_entre_roles(
    db_testing,
):
    escenario = preparar_escenario_escritura(db_testing)

    empresa = escenario["empresa"]
    administrador = escenario["administrador"]
    usuario = escenario["usuario_operativo"]

    identificador = uuid.uuid4().hex

    rol_asignador = Rol(
        empresa_id=empresa.id,
        nombre=f"ASIGNADOR_{identificador[:8]}",
        descripcion="Permite asignar roles",
    )

    rol_revocador = Rol(
        empresa_id=empresa.id,
        nombre=f"REVOCADOR_{identificador[:8]}",
        descripcion="Permite revocar roles",
    )

    db_testing.add_all([rol_asignador, rol_revocador])
    db_testing.flush()

    permiso_asignar = db_testing.scalar(
        select(Permiso).where(
            Permiso.codigo == "roles.asignar"
        )
    )

    permiso_revocar = db_testing.scalar(
        select(Permiso).where(
            Permiso.codigo == "roles.revocar"
        )
    )

    db_testing.execute(
        roles_permisos.insert().values(
            rol_id=rol_asignador.id,
            permiso_id=permiso_asignar.id,
        )
    )

    db_testing.execute(
        roles_permisos.insert().values(
            rol_id=rol_revocador.id,
            permiso_id=permiso_revocar.id,
        )
    )

    # El usuario recibe dos roles diferentes.
    # Cada uno aporta uno de los permisos administrativos.
    db_testing.execute(
        usuarios_roles.insert().values(
            usuario_id=usuario.id,
            rol_id=rol_asignador.id,
            empresa_id=empresa.id,
        )
    )

    db_testing.execute(
        usuarios_roles.insert().values(
            usuario_id=usuario.id,
            rol_id=rol_revocador.id,
            empresa_id=empresa.id,
        )
    )

    db_testing.flush()

    # Administrador original + segundo usuario con
    # permisos distribuidos.
    assert _contar_administradores_rbac(
        db_testing,
        empresa_id=empresa.id,
    ) == 2

    db_testing.commit()

    # Retirar un permiso administrativo al segundo usuario.
    resultado = revocar_rol_usuario(
        db_testing,
        administrador_id=administrador.id,
        usuario_id=usuario.id,
        rol_id=rol_asignador.id,
    )

    assert resultado["estado"] == "revocado"

    # Debe permanecer el administrador original.
    assert _contar_administradores_rbac(
        db_testing,
        empresa_id=empresa.id,
    ) == 1

    # El usuario conserva su segundo rol.
    rol_restante = db_testing.scalar(
        select(usuarios_roles.c.rol_id).where(
            usuarios_roles.c.usuario_id == usuario.id,
            usuarios_roles.c.rol_id == rol_revocador.id,
            usuarios_roles.c.empresa_id == empresa.id,
        )
    )

    assert rol_restante == rol_revocador.id
