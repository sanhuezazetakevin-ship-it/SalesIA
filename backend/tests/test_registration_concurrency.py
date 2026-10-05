
"""
SalesIA Enterprise
FASE 05-B.4-B

Prueba de concurrencia del registro mediante invitación.
Exclusivamente PostgreSQL Testing.
"""

import hashlib
import secrets

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import uuid4

from sqlalchemy import create_engine, delete, func, select, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.invitacion_usuario import InvitacionUsuario
from app.services.registration_service import (
    RegistroInvitacionError,
    registrar_con_invitacion,
)
from scripts.verificar_aislamiento_real import (
    obtener_referencia_supabase,
)


def crear_engine_testing():
    if not settings.TEST_DATABASE_URL:
        raise AssertionError("TEST_DATABASE_URL no configurada.")

    principal = obtener_referencia_supabase(settings.DATABASE_URL)
    testing = obtener_referencia_supabase(settings.TEST_DATABASE_URL)

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


def test_registro_simultaneo_misma_invitacion():
    engine = crear_engine_testing()

    TestingSession = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    sufijo = uuid4().hex
    correo = f"registro-conc-{sufijo}@example.com"
    correo_admin = f"admin-conc-{sufijo}@example.com"

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    ids = {
        "empresa": None,
        "administrador": None,
        "invitacion": None,
    }

    try:
        # Comprobar el estado inicial de Testing.
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
                cantidad = conexion.execute(
                    text(f"SELECT COUNT(*) FROM public.{tabla}")
                ).scalar_one()

                assert cantidad == 0, (
                    f"Testing no está limpio: {tabla}={cantidad}"
                )

        # Preparación: datos confirmados para ambas conexiones.
        with TestingSession() as db:
            try:
                empresa = Empresa(
                    razon_social=f"Registro Concurrente {sufijo}",
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
                    nombre="Administrador Temporal",
                    email=correo_admin,
                    password_hash="hash-ficticio-no-utilizable",
                    activo=True,
                )

                db.add(administrador)
                db.flush()
                ids["administrador"] = administrador.id

                invitacion = InvitacionUsuario(
                    empresa_id=empresa.id,
                    invitado_por_id=administrador.id,
                    email=correo,
                    token_hash=token_hash,
                    estado="pendiente",
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

        # Dos sesiones independientes comienzan coordinadamente.
        barrera = Barrier(2, timeout=20)

        def intentar_registro():
            with TestingSession() as db:
                barrera.wait()

                try:
                    resultado = registrar_con_invitacion(
                        db,
                        token=token,
                        nombre="Usuario Concurrente",
                        email=correo,
                        password="ClaveConcurrenteSegura2026!",
                    )

                    return ("creado", resultado)

                except RegistroInvitacionError as exc:
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
        assert "no está disponible" in rechazados[0]

        # Comprobar el resultado persistido.
        with TestingSession() as db:
            usuarios = db.scalars(
                select(Usuario).where(
                    Usuario.empresa_id == ids["empresa"],
                    Usuario.email == correo,
                )
            ).all()

            assert len(usuarios) == 1
            assert usuarios[0].activo is False

            invitacion = db.get(
                InvitacionUsuario,
                ids["invitacion"],
            )

            assert invitacion.estado == "aceptada"

            assert creados[0]["usuario_id"] == usuarios[0].id
            assert creados[0]["estado"] == "pendiente_aprobacion"

    finally:
        # Eliminar exclusivamente los datos de esta prueba.
        # Primero las invitaciones, después los usuarios y la empresa.
        try:
            if ids["empresa"] is not None:
                with TestingSession() as db:
                    try:
                        db.execute(
                            delete(InvitacionUsuario).where(
                                InvitacionUsuario.id
                                == ids["invitacion"],
                                InvitacionUsuario.empresa_id
                                == ids["empresa"],
                            )
                        ) if ids["invitacion"] is not None else None

                        db.execute(
                            delete(Usuario).where(
                                Usuario.empresa_id == ids["empresa"],
                                Usuario.email == correo,
                            )
                        )

                        if ids["administrador"] is not None:
                            db.execute(
                                delete(Usuario).where(
                                    Usuario.id
                                    == ids["administrador"],
                                    Usuario.empresa_id
                                    == ids["empresa"],
                                )
                            )

                        db.execute(
                            delete(Empresa).where(
                                Empresa.id == ids["empresa"]
                            )
                        )

                        db.commit()

                    except Exception:
                        db.rollback()
                        raise

        finally:
            engine.dispose()
