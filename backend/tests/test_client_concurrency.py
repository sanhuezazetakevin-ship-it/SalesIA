
"""
SalesIA Enterprise
FASE 06-B.5

Dos solicitudes intentan registrar simultaneamente
un cliente con el mismo documento.

Exclusivamente PostgreSQL Testing.
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
from app.models.cliente import Cliente
from app.models.auditoria import Auditoria
from app.models.asociaciones import usuarios_roles, roles_permisos

from app.schemas.clientes import ClienteCreate
from app.services.client_service import (
    ClienteServiceError,
    crear_cliente,
    desactivar_cliente,
)
from scripts.verificar_aislamiento_real import (
    obtener_referencia_supabase,
)


def crear_engine_testing():
    principal = obtener_referencia_supabase(
        settings.DATABASE_URL
    )

    testing = obtener_referencia_supabase(
        settings.TEST_DATABASE_URL
    )

    if not principal or not testing or principal == testing:
        raise AssertionError(
            "SEGURIDAD: aislamiento de Testing no verificado."
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


def test_registro_concurrente_mismo_documento():
    engine = crear_engine_testing()

    TestingSession = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    identificador = uuid4().hex

    ids = {
        "empresa": None,
        "usuario": None,
        "rol": None,
        "permiso": None,
        "permiso_creado": False,
    }

    documento = "12345678"

    try:
        # 1. Verificar la existencia de las tablas, sin exigir una base vacia.
        # Testing contiene datos de configuracion y seeds persistentes.
        # Cada escenario utiliza identificadores exclusivos y limpieza acotada.
        with engine.connect() as conexion:
            conexion.execute(text("SET TRANSACTION READ ONLY"))
            for tabla in (
                "empresas",
                "usuarios",
                "roles",
                "usuarios_roles",
                "roles_permisos",
                "auditoria",
                "clientes",
            ):
                existe = conexion.execute(
                    text("SELECT to_regclass(:tabla) IS NOT NULL"),
                    {"tabla": f"public.{tabla}"},
                ).scalar_one()
                assert existe, f"Falta la tabla requerida: public.{tabla}"

        # 2. Crear un escenario temporal confirmado.
        with TestingSession() as db:
            try:
                empresa = Empresa(
                    razon_social=f"Cliente Concurrente {identificador}",
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

                rol = Rol(
                    empresa_id=empresa.id,
                    nombre=f"CLIENTES_CONC_{identificador[:8]}",
                    descripcion="Rol temporal de concurrencia",
                )

                db.add(rol)
                db.flush()
                ids["rol"] = rol.id

                permiso = db.scalar(
                    select(Permiso).where(
                        Permiso.codigo == "clientes.crear"
                    )
                )

                if permiso is None:
                    permiso = Permiso(
                        codigo="clientes.crear",
                        descripcion="Crear clientes",
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

                usuario = Usuario(
                    empresa_id=empresa.id,
                    nombre="Operador Concurrente",
                    email=f"operador-{identificador}@example.com",
                    password_hash="hash-ficticio-no-utilizable",
                    activo=True,
                )

                db.add(usuario)
                db.flush()
                ids["usuario"] = usuario.id

                db.execute(
                    insert(usuarios_roles).values(
                        usuario_id=usuario.id,
                        rol_id=rol.id,
                        empresa_id=empresa.id,
                    )
                )

                db.commit()

            except Exception:
                db.rollback()
                raise

        # 3. Ejecutar dos solicitudes simultaneas.
        barrera = Barrier(2, timeout=20)

        def intentar_registro():
            with TestingSession() as db:
                barrera.wait()

                try:
                    cliente = crear_cliente(
                        db,
                        usuario_id=ids["usuario"],
                        datos=ClienteCreate(
                            nombre="Cliente Concurrente",
                            tipo_documento="DNI",
                            numero_documento=documento,
                        ),
                    )

                    return ("creado", cliente.id)

                except ClienteServiceError as exc:
                    return ("rechazado", str(exc))

        with ThreadPoolExecutor(max_workers=2) as executor:
            futuro_a = executor.submit(intentar_registro)
            futuro_b = executor.submit(intentar_registro)

            resultados = [
                futuro_a.result(timeout=75),
                futuro_b.result(timeout=75),
            ]

        creados = [
            valor for estado, valor in resultados
            if estado == "creado"
        ]

        rechazados = [
            valor for estado, valor in resultados
            if estado == "rechazado"
        ]

        assert len(creados) == 1, resultados
        assert len(rechazados) == 1, resultados

        # 4. Comprobar el resultado realmente persistido.
        with TestingSession() as db:
            cantidad_clientes = db.scalar(
                select(func.count(Cliente.id)).where(
                    Cliente.empresa_id == ids["empresa"],
                    Cliente.tipo_documento == "DNI",
                    Cliente.numero_documento == documento,
                )
            )

            assert cantidad_clientes == 1

            auditorias = db.scalars(
                select(Auditoria).where(
                    Auditoria.empresa_id == ids["empresa"],
                    Auditoria.entidad == "clientes",
                    Auditoria.accion == "CREAR",
                )
            ).all()

            assert len(auditorias) == 1
            assert auditorias[0].entidad_id == creados[0]
            assert auditorias[0].usuario_id == ids["usuario"]

    finally:
        # 5. Limpieza exclusivamente de este escenario.
        # Nunca utilizar TRUNCATE ni borrados globales.
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
                            delete(Cliente).where(
                                Cliente.empresa_id == ids["empresa"]
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
                                    roles_permisos.c.rol_id == ids["rol"]
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

                        # El permiso es global; eliminarlo
                        # solo si esta prueba lo creo.
                        if ids["permiso_creado"]:
                            db.execute(
                                delete(Permiso).where(
                                    Permiso.id == ids["permiso"],
                                    Permiso.codigo == "clientes.crear",
                                )
                            )

                        db.commit()

                    except Exception:
                        db.rollback()
                        raise

        finally:
            engine.dispose()


# ==========================================================
# FASE 06-C.5B
# DESACTIVACION CONCURRENTE DEL MISMO CLIENTE
# ==========================================================


def test_desactivacion_concurrente_genera_una_sola_auditoria():
    engine = crear_engine_testing()

    TestingSession = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    identificador = uuid4().hex

    ids = {
        "empresa": None,
        "usuario": None,
        "rol": None,
        "cliente": None,
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
                "auditoria",
                "clientes",
            ):
                existe = conexion.execute(
                    text("SELECT to_regclass(:tabla) IS NOT NULL"),
                    {"tabla": f"public.{tabla}"},
                ).scalar_one()
                assert existe, f"Falta la tabla requerida: public.{tabla}"

        # 2. Crear datos temporales confirmados.
        # Las dos conexiones deben poder consultarlos.
        with TestingSession() as db:
            try:
                empresa = Empresa(
                    razon_social=(
                        f"Desactivacion Concurrente {identificador}"
                    ),
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

                rol = Rol(
                    empresa_id=empresa.id,
                    nombre=f"EDITAR_CLIENTES_{identificador[:8]}",
                    descripcion="Rol temporal de desactivacion",
                )

                db.add(rol)
                db.flush()
                ids["rol"] = rol.id

                permiso = db.scalar(
                    select(Permiso).where(
                        Permiso.codigo == "clientes.editar"
                    )
                )

                if permiso is None:
                    permiso = Permiso(
                        codigo="clientes.editar",
                        descripcion="Editar clientes empresariales",
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

                usuario = Usuario(
                    empresa_id=empresa.id,
                    nombre="Operador Desactivacion Concurrente",
                    email=(
                        f"desactivacion-{identificador}@example.com"
                    ),
                    password_hash="hash-ficticio-no-utilizable",
                    activo=True,
                )

                db.add(usuario)
                db.flush()
                ids["usuario"] = usuario.id

                db.execute(
                    insert(usuarios_roles).values(
                        usuario_id=usuario.id,
                        rol_id=rol.id,
                        empresa_id=empresa.id,
                    )
                )

                cliente = Cliente(
                    empresa_id=empresa.id,
                    nombre="Cliente para desactivacion concurrente",
                    tipo_documento="DNI",
                    numero_documento="12345678",
                    activo=True,
                )

                db.add(cliente)
                db.flush()
                ids["cliente"] = cliente.id

                db.commit()

            except Exception:
                db.rollback()
                raise

        # 3. Ejecutar dos desactivaciones simultaneas.
        barrera = Barrier(2, timeout=20)

        def intentar_desactivar():
            with TestingSession() as db:
                barrera.wait()

                try:
                    cliente = desactivar_cliente(
                        db,
                        usuario_id=ids["usuario"],
                        cliente_id=ids["cliente"],
                    )

                    return (
                        "desactivado",
                        {
                            "cliente_id": cliente.id,
                            "activo": cliente.activo,
                        },
                    )

                except ClienteServiceError as exc:
                    return ("rechazado", str(exc))

        with ThreadPoolExecutor(max_workers=2) as executor:
            futuro_a = executor.submit(intentar_desactivar)
            futuro_b = executor.submit(intentar_desactivar)

            resultados = [
                futuro_a.result(timeout=75),
                futuro_b.result(timeout=75),
            ]

        exitosos = [
            valor
            for estado, valor in resultados
            if estado == "desactivado"
        ]

        rechazados = [
            valor
            for estado, valor in resultados
            if estado == "rechazado"
        ]

        assert len(exitosos) == 1, resultados
        assert len(rechazados) == 1, resultados

        assert exitosos[0]["cliente_id"] == ids["cliente"]
        assert exitosos[0]["activo"] is False

        assert "ya se encuentra inactivo" in rechazados[0]

        # 4. Comprobar el estado realmente persistido.
        with TestingSession() as db:
            cliente = db.scalar(
                select(Cliente).where(
                    Cliente.id == ids["cliente"],
                    Cliente.empresa_id == ids["empresa"],
                )
            )

            # Baja logica: el cliente no se elimina.
            assert cliente is not None
            assert cliente.activo is False

            auditorias = db.scalars(
                select(Auditoria).where(
                    Auditoria.empresa_id == ids["empresa"],
                    Auditoria.usuario_id == ids["usuario"],
                    Auditoria.entidad == "clientes",
                    Auditoria.entidad_id == ids["cliente"],
                    Auditoria.descripcion ==
                    "Desactivacion empresarial de cliente.",
                )
            ).all()

            assert len(auditorias) == 1

            auditoria = auditorias[0]

            assert auditoria.accion == "ACTUALIZAR"
            assert auditoria.datos_anteriores == {
                "activo": True
            }
            assert auditoria.datos_nuevos == {
                "activo": False
            }

    finally:
        # 5. Eliminar exclusivamente los datos de esta prueba.
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
                            delete(Cliente).where(
                                Cliente.empresa_id == ids["empresa"]
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
                                    roles_permisos.c.rol_id == ids["rol"]
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

                        # Los permisos son globales.
                        # Solo se elimina el creado por esta prueba.
                        if ids["permiso_creado"]:
                            db.execute(
                                delete(Permiso).where(
                                    Permiso.id == ids["permiso"],
                                    Permiso.codigo == "clientes.editar",
                                )
                            )

                        db.commit()

                    except Exception:
                        db.rollback()
                        raise

        finally:
            engine.dispose()
