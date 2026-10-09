
"""
SalesIA Enterprise
FASE 05-B.3-C

Prueba integral de concurrencia de invitaciones.

ATENCIÓN:
Utiliza exclusivamente PostgreSQL Testing.
Crea datos temporales confirmados y los elimina al finalizar.
"""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest

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
from app.models.invitacion_usuario import InvitacionUsuario

from app.models.asociaciones import (
    usuarios_roles,
    roles_permisos,
)

from app.services.invitation_service import (
    crear_invitacion,
    InvitacionError,
)

from scripts.verificar_aislamiento_real import (
    obtener_referencia_supabase,
)


def crear_engine_testing():
    if not settings.TEST_DATABASE_URL:
        pytest.fail("TEST_DATABASE_URL no configurada.")

    principal = obtener_referencia_supabase(
        settings.DATABASE_URL
    )

    testing = obtener_referencia_supabase(
        settings.TEST_DATABASE_URL
    )

    if not principal or not testing or principal == testing:
        pytest.fail(
            "SEGURIDAD: no se verificó el aislamiento de Testing."
        )

    return create_engine(
        settings.TEST_DATABASE_URL,
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=2,
        connect_args={
            "options": (
                "-c lock_timeout=10s "
                "-c statement_timeout=20s"
            )
        },
    )


def test_dos_invitaciones_simultaneas_mismo_correo():
    engine = crear_engine_testing()

    TestingSession = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    identificador = uuid4().hex

    email_admin = f"admin-conc-{identificador}@example.com"
    email_invitado = f"invitado-conc-{identificador}@example.com"

    ids = {
        "empresa": None,
        "usuario": None,
        "rol": None,
        "permiso": None,
        "permiso_creado": False,
    }

    try:
        # 1. Verificar la existencia de las tablas, sin exigir una base vacia.
        # Testing contiene datos de configuracion y seeds persistentes.
        # Cada escenario utiliza identificadores exclusivos y limpieza acotada.
        with engine.connect() as conexion:
            conexion.execute(text("SET TRANSACTION READ ONLY"))
            for tabla in (
                "empresas",
                "usuarios",
                "sesiones",
                "invitaciones_usuario",
                "roles",
                "usuarios_roles",
                "roles_permisos",
            ):
                existe = conexion.execute(
                    text("SELECT to_regclass(:tabla) IS NOT NULL"),
                    {"tabla": f"public.{tabla}"},
                ).scalar_one()
                assert existe, f"Falta la tabla requerida: public.{tabla}"

        # PASO 2: crear datos temporales confirmados.
        with TestingSession() as db:
            try:
                empresa = Empresa(
                    razon_social=f"Empresa Concurrencia {identificador}",
                    ruc=str(
                        80000000000
                        + int(identificador[:8], 16) % 10000000000
                    ),
                    moneda_base="PEN",
                    activo=True,
                )

                db.add(empresa)
                db.flush()
                ids["empresa"] = empresa.id

                administrador = Usuario(
                    empresa_id=empresa.id,
                    nombre="Administrador Concurrencia",
                    email=email_admin,
                    password_hash="hash-ficticio-no-utilizable",
                    activo=True,
                )

                db.add(administrador)
                db.flush()
                ids["usuario"] = administrador.id

                rol = Rol(
                    empresa_id=empresa.id,
                    nombre=f"ROL_CONC_{identificador[:12]}",
                    descripcion="Rol temporal de concurrencia",
                )

                db.add(rol)
                db.flush()
                ids["rol"] = rol.id

                permiso = db.scalar(
                    select(Permiso).where(
                        Permiso.codigo == "usuarios.crear"
                    )
                )

                if permiso is None:
                    permiso = Permiso(
                        codigo="usuarios.crear",
                        descripcion=(
                            "Permiso temporal para prueba "
                            f"de concurrencia {identificador}"
                        ),
                    )
                    db.add(permiso)
                    db.flush()
                    ids["permiso_creado"] = True

                ids["permiso"] = permiso.id

                db.execute(
                    insert(usuarios_roles).values(
                        usuario_id=administrador.id,
                        rol_id=rol.id,
                        empresa_id=empresa.id,
                    )
                )

                db.execute(
                    insert(roles_permisos).values(
                        rol_id=rol.id,
                        permiso_id=permiso.id,
                    )
                )

                db.commit()

            except Exception:
                db.rollback()
                raise

        # PASO 3: dos sesiones independientes.
        barrera = Barrier(2, timeout=15)

        def intentar_invitar():
            with TestingSession() as db:
                barrera.wait()

                try:
                    resultado = crear_invitacion(
                        db,
                        administrador_id=ids["usuario"],
                        email_invitado=email_invitado,
                    )

                    return ("creada", resultado)

                except InvitacionError as exc:
                    return ("rechazada", str(exc))

        with ThreadPoolExecutor(max_workers=2) as executor:
            futuro_a = executor.submit(intentar_invitar)
            futuro_b = executor.submit(intentar_invitar)

            resultados = [
                futuro_a.result(timeout=35),
                futuro_b.result(timeout=35),
            ]

        # PASO 4: verificar resultados.
        creadas = [
            resultado
            for resultado in resultados
            if resultado[0] == "creada"
        ]

        rechazadas = [
            resultado
            for resultado in resultados
            if resultado[0] == "rechazada"
        ]

        assert len(creadas) == 1, resultados
        assert len(rechazadas) == 1, resultados

        assert "invitación vigente" in rechazadas[0][1]

        with TestingSession() as db:
            cantidad = db.scalar(
                select(func.count(InvitacionUsuario.id)).where(
                    InvitacionUsuario.empresa_id == ids["empresa"],
                    InvitacionUsuario.email == email_invitado,
                    InvitacionUsuario.estado == "pendiente",
                )
            )

            assert cantidad == 1

    finally:
        # PASO 5: eliminar exclusivamente los datos
        # creados por esta prueba, en orden de dependencias.
        try:
            if ids["empresa"] is not None:
                with TestingSession() as db:
                    try:
                        db.execute(
                            delete(InvitacionUsuario).where(
                                InvitacionUsuario.empresa_id
                                == ids["empresa"]
                            )
                        )

                        if ids["usuario"] is not None:
                            db.execute(
                                delete(usuarios_roles).where(
                                    usuarios_roles.c.usuario_id
                                    == ids["usuario"]
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

                        if ids["usuario"] is not None:
                            db.execute(
                                delete(Usuario).where(
                                    Usuario.id == ids["usuario"],
                                    Usuario.empresa_id == ids["empresa"],
                                )
                            )

                        db.execute(
                            delete(Empresa).where(
                                Empresa.id == ids["empresa"]
                            )
                        )

                        if (
                            ids["permiso_creado"]
                            and ids["permiso"] is not None
                        ):
                            db.execute(
                                delete(Permiso).where(
                                    Permiso.id == ids["permiso"]
                                )
                            )

                        db.commit()

                    except Exception:
                        db.rollback()
                        raise

        finally:
            engine.dispose()
