
"""
SalesIA Enterprise
FASE 05-B.5-B

Prueba de concurrencia de aprobación administrativa.

Dos administradores autorizados intentan aprobar
simultáneamente al mismo usuario.

Exclusivamente PostgreSQL Testing.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import uuid4

from sqlalchemy import (
    create_engine,
    delete,
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
from app.models.invitacion_usuario import InvitacionUsuario
from app.models.auditoria import Auditoria

from app.models.asociaciones import (
    usuarios_roles,
    roles_permisos,
)

from app.services.approval_service import (
    AprobacionError,
    aprobar_usuario,
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


def crear_engine_testing():
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


def test_aprobacion_simultanea_genera_una_sola_auditoria():
    engine = crear_engine_testing()

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
        "usuario": None,
        "rol": None,
        "permiso": None,
        "permiso_creado": False,
        "invitacion": None,
    }

    try:
        # 1. Verificar la existencia de las tablas, sin exigir una base vacia.
        # Testing contiene datos de configuracion y seeds persistentes.
        # Cada escenario utiliza identificadores exclusivos y limpieza acotada.
        with engine.connect() as conexion:
            conexion.execute(text("SET TRANSACTION READ ONLY"))
            for tabla in TABLAS_AUDITADAS:
                existe = conexion.execute(
                    text("SELECT to_regclass(:tabla) IS NOT NULL"),
                    {"tabla": f"public.{tabla}"},
                ).scalar_one()
                assert existe, f"Falta la tabla requerida: public.{tabla}"

        # 2. Crear datos confirmados para que ambas
        # conexiones independientes puedan consultarlos.
        with TestingSession() as db:
            try:
                empresa = Empresa(
                    razon_social=f"Approval Concurrente {sufijo}",
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
                    nombre="Administrador Concurrente A",
                    email=f"admin-a-{sufijo}@example.com",
                    password_hash="hash-ficticio-admin-a",
                    activo=True,
                )

                admin_b = Usuario(
                    empresa_id=empresa.id,
                    nombre="Administrador Concurrente B",
                    email=f"admin-b-{sufijo}@example.com",
                    password_hash="hash-ficticio-admin-b",
                    activo=True,
                )

                usuario = Usuario(
                    empresa_id=empresa.id,
                    nombre="Usuario Pendiente Concurrente",
                    email=f"pendiente-{sufijo}@example.com",
                    password_hash="hash-ficticio-usuario",
                    activo=False,
                )

                db.add_all([
                    admin_a,
                    admin_b,
                    usuario,
                ])
                db.flush()

                ids["admin_a"] = admin_a.id
                ids["admin_b"] = admin_b.id
                ids["usuario"] = usuario.id

                rol = Rol(
                    empresa_id=empresa.id,
                    nombre=f"Autorizador {sufijo[:12]}",
                    descripcion="Rol temporal de concurrencia",
                )

                db.add(rol)
                db.flush()
                ids["rol"] = rol.id

                permiso = db.scalar(
                    select(Permiso).where(
                        Permiso.codigo == "usuarios.autorizar"
                    )
                )

                if permiso is None:
                    permiso = Permiso(
                        codigo="usuarios.autorizar",
                        descripcion=(
                            "Permiso temporal para prueba "
                            "de aprobación concurrente"
                        ),
                    )
                    db.add(permiso)
                    db.flush()
                    ids["permiso_creado"] = True

                ids["permiso"] = permiso.id

                db.execute(
                    insert(roles_permisos).values(
                        rol_id=rol.id,
                        permiso_id=permiso.id,
                    )
                )

                for administrador in (admin_a, admin_b):
                    db.execute(
                        insert(usuarios_roles).values(
                            usuario_id=administrador.id,
                            rol_id=rol.id,
                            empresa_id=empresa.id,
                        )
                    )

                invitacion = InvitacionUsuario(
                    empresa_id=empresa.id,
                    invitado_por_id=admin_a.id,
                    email=usuario.email,
                    token_hash=uuid4().hex + uuid4().hex,
                    estado="aceptada",
                    fecha_expiracion=(
                        datetime.now(timezone.utc)
                        + timedelta(hours=48)
                    ),
                )

                db.add(invitacion)
                db.flush()
                ids["invitacion"] = invitacion.id

                db.commit()

            except Exception:
                db.rollback()
                raise

        # 3. Iniciar ambas aprobaciones simultáneamente.
        barrera = Barrier(2, timeout=20)

        def intentar_aprobacion(administrador_id):
            with TestingSession() as db:
                barrera.wait()

                try:
                    resultado = aprobar_usuario(
                        db,
                        administrador_id=administrador_id,
                        usuario_id=ids["usuario"],
                    )

                    return ("aprobado", resultado)

                except AprobacionError as exc:
                    return ("rechazado", str(exc))

        with ThreadPoolExecutor(max_workers=2) as executor:
            futuro_a = executor.submit(
                intentar_aprobacion,
                ids["admin_a"],
            )

            futuro_b = executor.submit(
                intentar_aprobacion,
                ids["admin_b"],
            )

            resultados = [
                futuro_a.result(timeout=75),
                futuro_b.result(timeout=75),
            ]

        aprobados = [
            valor
            for estado, valor in resultados
            if estado == "aprobado"
        ]

        rechazados = [
            valor
            for estado, valor in resultados
            if estado == "rechazado"
        ]

        # Solo una aprobación debe completarse.
        assert len(aprobados) == 1, resultados
        assert len(rechazados) == 1, resultados

        assert "ya se encuentra activo" in rechazados[0]

        # 4. Comprobar el resultado realmente persistido.
        with TestingSession() as db:
            usuario = db.get(
                Usuario,
                ids["usuario"],
            )

            assert usuario is not None
            assert usuario.activo is True

            auditorias = db.scalars(
                select(Auditoria).where(
                    Auditoria.empresa_id == ids["empresa"],
                    Auditoria.entidad == "usuarios",
                    Auditoria.entidad_id == ids["usuario"],
                    Auditoria.accion == "ACTUALIZAR",
                )
            ).all()

            assert len(auditorias) == 1

            auditoria = auditorias[0]

            assert auditoria.usuario_id in (
                ids["admin_a"],
                ids["admin_b"],
            )

            assert auditoria.datos_anteriores == {
                "activo": False
            }

            assert auditoria.datos_nuevos == {
                "activo": True
            }

            assert aprobados[0]["usuario_id"] == ids["usuario"]

            assert (
                aprobados[0]["aprobado_por_id"]
                == auditoria.usuario_id
            )

    finally:
        # 5. Limpieza exclusiva de los registros
        # identificados como pertenecientes a esta prueba.
        #
        # No utiliza TRUNCATE ni borrados globales.
        try:
            if ids["empresa"] is not None:
                with TestingSession() as db:
                    try:
                        # Auditoría antes de eliminar usuarios.
                        db.execute(
                            delete(Auditoria).where(
                                Auditoria.empresa_id
                                == ids["empresa"],
                                Auditoria.entidad == "usuarios",
                                Auditoria.entidad_id
                                == ids["usuario"],
                            )
                        )

                        if ids["invitacion"] is not None:
                            db.execute(
                                delete(InvitacionUsuario).where(
                                    InvitacionUsuario.id
                                    == ids["invitacion"],
                                    InvitacionUsuario.empresa_id
                                    == ids["empresa"],
                                )
                            )

                        if ids["rol"] is not None:
                            db.execute(
                                delete(usuarios_roles).where(
                                    usuarios_roles.c.rol_id
                                    == ids["rol"],
                                    usuarios_roles.c.empresa_id
                                    == ids["empresa"],
                                )
                            )

                            db.execute(
                                delete(roles_permisos).where(
                                    roles_permisos.c.rol_id
                                    == ids["rol"],
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
                                ids["usuario"],
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

                        # Eliminar el permiso global solo si
                        # esta prueba lo creó expresamente.
                        if (
                            ids["permiso_creado"]
                            and ids["permiso"] is not None
                        ):
                            db.execute(
                                delete(Permiso).where(
                                    Permiso.id == ids["permiso"],
                                    Permiso.codigo
                                    == "usuarios.autorizar",
                                )
                            )

                        db.commit()

                    except Exception:
                        db.rollback()
                        raise

        finally:
            engine.dispose()
