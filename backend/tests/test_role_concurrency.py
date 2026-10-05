

"""
SalesIA Enterprise
FASE 05-F.3B.3

Concurrencia RBAC: dos asignaciones simultaneas
del mismo rol al mismo usuario.

EXCLUSIVAMENTE PostgreSQL Testing.
"""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from sqlalchemy import (
    create_engine,
    delete,
    func,
    insert,
    select,
    text,
)
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.permiso import Permiso
from app.models.auditoria import Auditoria

from app.models.asociaciones import (
    usuarios_roles,
    roles_permisos,
)

from app.services.role_service import (
    RolServiceError,
    asignar_rol_usuario,
)

from scripts.verificar_aislamiento_real import (
    obtener_referencia_supabase,
)


TABLAS_AUDITADAS = (
    "empresas",
    "usuarios",
    "sesiones",
    "invitaciones_usuario",
    "roles",
    "usuarios_roles",
    "roles_permisos",
    "auditoria",
)


def crear_engine_testing_rbac():
    if not settings.TEST_DATABASE_URL:
        raise AssertionError(
            "TEST_DATABASE_URL no configurada."
        )

    principal = obtener_referencia_supabase(
        settings.DATABASE_URL
    )

    testing = obtener_referencia_supabase(
        settings.TEST_DATABASE_URL
    )

    if not principal or not testing or principal == testing:
        raise AssertionError(
            "SEGURIDAD: aislamiento PostgreSQL no verificado."
        )

    return create_engine(
        settings.TEST_DATABASE_URL,
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=2,
        connect_args={
            "options": (
                "-c lock_timeout=30s "
                "-c statement_timeout=60s"
            )
        },
    )


def test_asignacion_simultanea_no_duplica_rol_ni_auditoria():
    engine = crear_engine_testing_rbac()

    TestingSession = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    sufijo = uuid4().hex

    ids = {
        "empresa": None,
        "admin": None,
        "usuario": None,
        "rol_admin": None,
        "rol_destino": None,
    }

    permisos_creados = {}

    try:
        # 1. Comprobar limpieza inicial de Testing.
        with engine.connect() as conexion:
            conexion.execute(
                text("SET TRANSACTION READ ONLY")
            )

            for tabla in TABLAS_AUDITADAS:
                cantidad = conexion.execute(
                    text(
                        f"SELECT COUNT(*) FROM public.{tabla}"
                    )
                ).scalar_one()

                assert cantidad == 0, (
                    f"Testing no esta limpio: "
                    f"{tabla}={cantidad}"
                )

        # 2. Preparar datos confirmados.
        with TestingSession() as db:
            try:
                empresa = Empresa(
                    razon_social=f"RBAC Concurrente {sufijo}",
                    ruc=str(
                        80000000000
                        + int(sufijo[:8], 16) % 10000000000
                    ),
                    moneda_base="PEN",
                    activo=True,
                )

                db.add(empresa)
                db.flush()
                ids["empresa"] = empresa.id

                administrador = Usuario(
                    empresa_id=empresa.id,
                    nombre="Administrador Concurrente RBAC",
                    email=f"admin-rbac-conc-{sufijo}@example.com",
                    password_hash="hash-ficticio-no-utilizable",
                    activo=True,
                )

                usuario = Usuario(
                    empresa_id=empresa.id,
                    nombre="Usuario Concurrente RBAC",
                    email=f"usuario-rbac-conc-{sufijo}@example.com",
                    password_hash="hash-ficticio-no-utilizable",
                    activo=True,
                )

                db.add_all([administrador, usuario])
                db.flush()

                ids["admin"] = administrador.id
                ids["usuario"] = usuario.id

                rol_admin = Rol(
                    empresa_id=empresa.id,
                    nombre=f"ADMIN_CONC_{sufijo[:12]}",
                    descripcion="Administrador temporal RBAC",
                )

                rol_destino = Rol(
                    empresa_id=empresa.id,
                    nombre=f"OPERATIVO_CONC_{sufijo[:12]}",
                    descripcion="Rol temporal sin privilegios",
                )

                db.add_all([rol_admin, rol_destino])
                db.flush()

                ids["rol_admin"] = rol_admin.id
                ids["rol_destino"] = rol_destino.id

                for codigo in (
                    "roles.asignar",
                    "roles.revocar",
                ):
                    permiso = db.scalar(
                        select(Permiso).where(
                            Permiso.codigo == codigo
                        )
                    )

                    if permiso is None:
                        permiso = Permiso(
                            codigo=codigo,
                            descripcion=(
                                "Permiso temporal de concurrencia RBAC"
                            ),
                        )
                        db.add(permiso)
                        db.flush()
                        permisos_creados[codigo] = permiso.id

                    db.execute(
                        insert(roles_permisos).values(
                            rol_id=rol_admin.id,
                            permiso_id=permiso.id,
                        )
                    )

                db.execute(
                    insert(usuarios_roles).values(
                        usuario_id=administrador.id,
                        rol_id=rol_admin.id,
                        empresa_id=empresa.id,
                    )
                )

                # El rol destino no contiene permisos superiores.
                db.commit()

            except Exception:
                db.rollback()
                raise

        # 3. Lanzar dos asignaciones concurrentes.
        barrera = Barrier(2, timeout=20)

        def intentar_asignar():
            with TestingSession() as db:
                barrera.wait()

                try:
                    resultado = asignar_rol_usuario(
                        db,
                        administrador_id=ids["admin"],
                        usuario_id=ids["usuario"],
                        rol_id=ids["rol_destino"],
                    )

                    return ("asignado", resultado)

                except RolServiceError as exc:
                    return ("rechazado", str(exc))

        with ThreadPoolExecutor(max_workers=2) as executor:
            futuro_a = executor.submit(intentar_asignar)
            futuro_b = executor.submit(intentar_asignar)

            resultados = [
                futuro_a.result(timeout=75),
                futuro_b.result(timeout=75),
            ]

        asignados = [
            valor
            for estado, valor in resultados
            if estado == "asignado"
        ]

        rechazados = [
            valor
            for estado, valor in resultados
            if estado == "rechazado"
        ]

        assert len(asignados) == 1, resultados
        assert len(rechazados) == 1, resultados

        assert "ya tiene asignado" in rechazados[0]

        # 4. Consultar datos persistidos desde otra sesion.
        with TestingSession() as db:
            cantidad_asignaciones = db.scalar(
                select(func.count())
                .select_from(usuarios_roles)
                .where(
                    usuarios_roles.c.usuario_id == ids["usuario"],
                    usuarios_roles.c.rol_id == ids["rol_destino"],
                    usuarios_roles.c.empresa_id == ids["empresa"],
                )
            )

            assert cantidad_asignaciones == 1

            auditorias = db.scalars(
                select(Auditoria).where(
                    Auditoria.empresa_id == ids["empresa"],
                    Auditoria.entidad == "usuarios_roles",
                    Auditoria.entidad_id == ids["usuario"],
                    Auditoria.descripcion
                    == "Asignación administrativa de rol.",
                )
            ).all()

            assert len(auditorias) == 1

            assert auditorias[0].usuario_id == ids["admin"]

            assert auditorias[0].datos_nuevos["rol_id"] == (
                ids["rol_destino"]
            )

    finally:
        # 5. Limpiar solo los registros propios de la prueba.
        # No utilizar TRUNCATE ni borrados globales.
        try:
            if ids["empresa"] is not None:
                with TestingSession() as db:
                    try:
                        db.execute(
                            delete(Auditoria).where(
                                Auditoria.empresa_id == ids["empresa"]
                            )
                        )

                        db.execute(
                            delete(usuarios_roles).where(
                                usuarios_roles.c.empresa_id
                                == ids["empresa"]
                            )
                        )

                        roles_ids = [
                            valor
                            for valor in (
                                ids["rol_admin"],
                                ids["rol_destino"],
                            )
                            if valor is not None
                        ]

                        if roles_ids:
                            db.execute(
                                delete(roles_permisos).where(
                                    roles_permisos.c.rol_id.in_(roles_ids)
                                )
                            )

                            db.execute(
                                delete(Rol).where(
                                    Rol.id.in_(roles_ids),
                                    Rol.empresa_id == ids["empresa"],
                                )
                            )

                        usuarios_ids = [
                            valor
                            for valor in (
                                ids["admin"],
                                ids["usuario"],
                            )
                            if valor is not None
                        ]

                        if usuarios_ids:
                            db.execute(
                                delete(Usuario).where(
                                    Usuario.id.in_(usuarios_ids),
                                    Usuario.empresa_id == ids["empresa"],
                                )
                            )

                        db.execute(
                            delete(Empresa).where(
                                Empresa.id == ids["empresa"]
                            )
                        )

                        # Los permisos son globales: eliminar
                        # exclusivamente los creados aqui.
                        for codigo, permiso_id in permisos_creados.items():
                            db.execute(
                                delete(Permiso).where(
                                    Permiso.id == permiso_id,
                                    Permiso.codigo == codigo,
                                )
                            )

                        db.commit()

                    except Exception:
                        db.rollback()
                        raise

        finally:
            engine.dispose()

# ==========================================================
# FASE 05-F.3B.4
# REVOCACION CONCURRENTE ENTRE ADMINISTRADORES
# ==========================================================

from app.services.role_service import (
    revocar_rol_usuario,
    _contar_administradores_rbac,
)


def test_revocaciones_cruzadas_conservan_un_administrador():
    engine = crear_engine_testing_rbac()

    TestingSession = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    sufijo = uuid4().hex

    ids = {
        "empresa": None,
        "admin_a": None,
        "admin_b": None,
        "rol": None,
    }

    permisos_creados = {}

    try:
        # 1. Verificar que Testing esta limpio.
        with engine.connect() as conexion:
            conexion.execute(
                text("SET TRANSACTION READ ONLY")
            )

            for tabla in TABLAS_AUDITADAS:
                cantidad = conexion.execute(
                    text(f"SELECT COUNT(*) FROM public.{tabla}")
                ).scalar_one()

                assert cantidad == 0, (
                    f"Testing no esta limpio: {tabla}={cantidad}"
                )

        # 2. Crear dos administradores con el mismo rol.
        with TestingSession() as db:
            try:
                empresa = Empresa(
                    razon_social=f"RBAC Cruzado {sufijo}",
                    ruc=str(
                        80000000000
                        + int(sufijo[:8], 16) % 10000000000
                    ),
                    moneda_base="PEN",
                    activo=True,
                )

                db.add(empresa)
                db.flush()
                ids["empresa"] = empresa.id

                admin_a = Usuario(
                    empresa_id=empresa.id,
                    nombre="Administrador RBAC A",
                    email=f"rbac-a-{sufijo}@example.com",
                    password_hash="hash-ficticio-no-utilizable",
                    activo=True,
                )

                admin_b = Usuario(
                    empresa_id=empresa.id,
                    nombre="Administrador RBAC B",
                    email=f"rbac-b-{sufijo}@example.com",
                    password_hash="hash-ficticio-no-utilizable",
                    activo=True,
                )

                db.add_all([admin_a, admin_b])
                db.flush()

                ids["admin_a"] = admin_a.id
                ids["admin_b"] = admin_b.id

                rol = Rol(
                    empresa_id=empresa.id,
                    nombre=f"ADMIN_CRUZADO_{sufijo[:12]}",
                    descripcion="Rol administrativo concurrente",
                )

                db.add(rol)
                db.flush()
                ids["rol"] = rol.id

                for codigo in (
                    "roles.asignar",
                    "roles.revocar",
                ):
                    permiso = db.scalar(
                        select(Permiso).where(
                            Permiso.codigo == codigo
                        )
                    )

                    if permiso is None:
                        permiso = Permiso(
                            codigo=codigo,
                            descripcion=(
                                "Permiso temporal RBAC concurrente"
                            ),
                        )
                        db.add(permiso)
                        db.flush()
                        permisos_creados[codigo] = permiso.id

                    db.execute(
                        insert(roles_permisos).values(
                            rol_id=rol.id,
                            permiso_id=permiso.id,
                        )
                    )

                for admin in (admin_a, admin_b):
                    db.execute(
                        insert(usuarios_roles).values(
                            usuario_id=admin.id,
                            rol_id=rol.id,
                            empresa_id=empresa.id,
                        )
                    )

                assert _contar_administradores_rbac(
                    db,
                    empresa_id=empresa.id,
                ) == 2

                db.commit()

            except Exception:
                db.rollback()
                raise

        # 3. Ejecutar revocaciones cruzadas simultaneas.
        barrera = Barrier(2, timeout=20)

        def intentar_revocacion(actor_id, objetivo_id):
            with TestingSession() as db:
                barrera.wait()

                try:
                    resultado = revocar_rol_usuario(
                        db,
                        administrador_id=actor_id,
                        usuario_id=objetivo_id,
                        rol_id=ids["rol"],
                    )

                    return ("revocado", resultado)

                except RolServiceError as exc:
                    return ("rechazado", str(exc))

        with ThreadPoolExecutor(max_workers=2) as executor:
            futuro_a = executor.submit(
                intentar_revocacion,
                ids["admin_a"],
                ids["admin_b"],
            )

            futuro_b = executor.submit(
                intentar_revocacion,
                ids["admin_b"],
                ids["admin_a"],
            )

            resultados = [
                futuro_a.result(timeout=75),
                futuro_b.result(timeout=75),
            ]

        revocados = [
            valor
            for estado, valor in resultados
            if estado == "revocado"
        ]

        rechazados = [
            valor
            for estado, valor in resultados
            if estado == "rechazado"
        ]

        assert len(revocados) == 1, resultados
        assert len(rechazados) == 1, resultados

        # 4. Verificar el estado persistido.
        with TestingSession() as db:
            administradores_restantes = (
                _contar_administradores_rbac(
                    db,
                    empresa_id=ids["empresa"],
                )
            )

            assert administradores_restantes == 1

            asignaciones = db.execute(
                select(usuarios_roles.c.usuario_id).where(
                    usuarios_roles.c.empresa_id == ids["empresa"],
                    usuarios_roles.c.rol_id == ids["rol"],
                )
            ).scalars().all()

            assert len(asignaciones) == 1

            auditorias = db.scalars(
                select(Auditoria).where(
                    Auditoria.empresa_id == ids["empresa"],
                    Auditoria.entidad == "usuarios_roles",
                    Auditoria.descripcion
                    == "Revocación administrativa de rol.",
                )
            ).all()

            assert len(auditorias) == 1

            auditoria = auditorias[0]
            resultado_exitoso = revocados[0]

            assert (
                auditoria.usuario_id
                == resultado_exitoso["administrador_id"]
            )

            assert (
                auditoria.entidad_id
                == resultado_exitoso["usuario_id"]
            )

            assert resultado_exitoso["estado"] == "revocado"

    finally:
        # 5. Limpieza limitada exclusivamente a esta empresa.
        try:
            if ids["empresa"] is not None:
                with TestingSession() as db:
                    try:
                        db.execute(
                            delete(Auditoria).where(
                                Auditoria.empresa_id == ids["empresa"]
                            )
                        )

                        db.execute(
                            delete(usuarios_roles).where(
                                usuarios_roles.c.empresa_id
                                == ids["empresa"]
                            )
                        )

                        if ids["rol"] is not None:
                            db.execute(
                                delete(roles_permisos).where(
                                    roles_permisos.c.rol_id
                                    == ids["rol"]
                                )
                            )

                            db.execute(
                                delete(Rol).where(
                                    Rol.id == ids["rol"],
                                    Rol.empresa_id == ids["empresa"],
                                )
                            )

                        usuarios_ids = [
                            valor
                            for valor in (
                                ids["admin_a"],
                                ids["admin_b"],
                            )
                            if valor is not None
                        ]

                        if usuarios_ids:
                            db.execute(
                                delete(Usuario).where(
                                    Usuario.id.in_(usuarios_ids),
                                    Usuario.empresa_id
                                    == ids["empresa"],
                                )
                            )

                        db.execute(
                            delete(Empresa).where(
                                Empresa.id == ids["empresa"]
                            )
                        )

                        for codigo, permiso_id in permisos_creados.items():
                            db.execute(
                                delete(Permiso).where(
                                    Permiso.id == permiso_id,
                                    Permiso.codigo == codigo,
                                )
                            )

                        db.commit()

                    except Exception:
                        db.rollback()
                        raise

        finally:
            engine.dispose()
