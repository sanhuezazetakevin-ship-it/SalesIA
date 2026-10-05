
"""
SalesIA Enterprise
FASE 05-F.5C

Prueba protegida del seed RBAC.

Utiliza exclusivamente TEST_DATABASE_URL.
Todas las escrituras ocurren dentro de una
transaccion exterior que se revierte al finalizar.
"""

from uuid import uuid4

import pytest

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.empresa import Empresa
from app.models.rol import Rol
from app.models.permiso import Permiso
from app.models.asociaciones import roles_permisos

from scripts.verificar_aislamiento_real import (
    obtener_referencia_supabase,
)

from scripts.seed_roles_permisos import (
    ejecutar_seed,
    validar_catalogo,
    TODOS_LOS_PERMISOS,
    ROLES,
)


def test_seed_rechaza_ejecucion_sin_factory():
    with pytest.raises(RuntimeError, match="SEGURIDAD"):
        ejecutar_seed(
            empresa_id=1,
            aplicar=False,
        )


def test_seed_rbac_simulacion_aplicacion_e_idempotencia():
    # 1. Verificacion obligatoria de aislamiento.
    assert settings.TEST_DATABASE_URL, (
        "TEST_DATABASE_URL no configurada."
    )

    principal = obtener_referencia_supabase(
        settings.DATABASE_URL
    )

    testing = obtener_referencia_supabase(
        settings.TEST_DATABASE_URL
    )

    assert principal and testing and principal != testing, (
        "SEGURIDAD: Testing y produccion no estan "
        "correctamente diferenciados."
    )

    validar_catalogo()

    engine = create_engine(
        settings.TEST_DATABASE_URL,
        pool_pre_ping=True,
    )

    try:
        with engine.connect() as connection:
            # Ningun commit de las sesiones internas puede
            # confirmar esta transaccion exterior.
            transaccion_exterior = connection.begin()

            TestingSession = sessionmaker(
                bind=connection,
                autoflush=False,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            )

            try:
                identificador = uuid4().hex

                # 2. Crear empresa temporal de Testing.
                with TestingSession() as db:
                    permisos_antes = set(
                        db.scalars(
                            select(Permiso.codigo)
                        ).all()
                    )

                    empresa = Empresa(
                        razon_social=(
                            f"Empresa Seed RBAC {identificador[:12]}"
                        ),
                        ruc=str(
                            80000000000
                            + int(identificador[:8], 16)
                            % 10000000000
                        ),
                        moneda_base="PEN",
                        activo=True,
                    )

                    db.add(empresa)
                    db.flush()

                    empresa_id = empresa.id
                    db.commit()

                # 3. Simulacion: debe ejecutar rollback.
                ejecutar_seed(
                    empresa_id=empresa_id,
                    aplicar=False,
                    session_factory=TestingSession,
                )

                with TestingSession() as db:
                    roles_simulados = db.scalar(
                        select(func.count(Rol.id)).where(
                            Rol.empresa_id == empresa_id
                        )
                    )

                    permisos_despues_simulacion = set(
                        db.scalars(
                            select(Permiso.codigo)
                        ).all()
                    )

                    assert roles_simulados == 0
                    assert (
                        permisos_despues_simulacion
                        == permisos_antes
                    )

                # 4. Aplicacion protegida.
                # El commit afecta solo al savepoint,
                # NO a la transaccion exterior.
                ejecutar_seed(
                    empresa_id=empresa_id,
                    aplicar=True,
                    session_factory=TestingSession,
                )

                with TestingSession() as db:
                    roles = db.scalars(
                        select(Rol).where(
                            Rol.empresa_id == empresa_id
                        )
                    ).all()

                    assert {rol.nombre for rol in roles} == set(ROLES)

                    permisos_actuales = set(
                        db.scalars(
                            select(Permiso.codigo)
                        ).all()
                    )

                    assert TODOS_LOS_PERMISOS.issubset(
                        permisos_actuales
                    )

                    asignaciones = set(
                        db.execute(
                            select(
                                Rol.nombre,
                                Permiso.codigo,
                            )
                            .select_from(Rol)
                            .join(
                                roles_permisos,
                                roles_permisos.c.rol_id == Rol.id,
                            )
                            .join(
                                Permiso,
                                Permiso.id ==
                                roles_permisos.c.permiso_id,
                            )
                            .where(Rol.empresa_id == empresa_id)
                        ).all()
                    )

                    esperadas = {
                        (nombre, codigo)
                        for nombre, configuracion in ROLES.items()
                        for codigo in configuracion["permisos"]
                    }

                    assert asignaciones == esperadas

                    cantidad_roles = len(roles)
                    cantidad_asignaciones = len(asignaciones)

                # 5. Segunda aplicacion: idempotencia.
                ejecutar_seed(
                    empresa_id=empresa_id,
                    aplicar=True,
                    session_factory=TestingSession,
                )

                with TestingSession() as db:
                    assert db.scalar(
                        select(func.count(Rol.id)).where(
                            Rol.empresa_id == empresa_id
                        )
                    ) == cantidad_roles

                    assert db.scalar(
                        select(func.count())
                        .select_from(roles_permisos)
                        .join(
                            Rol,
                            Rol.id == roles_permisos.c.rol_id,
                        )
                        .where(Rol.empresa_id == empresa_id)
                    ) == cantidad_asignaciones

                    assert cantidad_roles == 5

            finally:
                # 6. Reversion de toda la prueba.
                # Incluye empresa, roles, relaciones
                # y permisos globales creados temporalmente.
                transaccion_exterior.rollback()

    finally:
        engine.dispose()
