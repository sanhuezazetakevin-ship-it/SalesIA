
"""
SalesIA Enterprise
FASE 04 - Seed empresarial de roles y permisos.

Uso:
    python -m scripts.seed_roles_permisos --empresa-id 1
    python -m scripts.seed_roles_permisos --empresa-id 1 --apply

Sin --apply, los cambios se revierten (simulacion).
"""

import argparse

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

import app.models

from app.models.empresa import Empresa
from app.models.rol import Rol
from app.models.permiso import Permiso
from app.models.asociaciones import roles_permisos


# Catalogo global de permisos.
# Las claves son los modulos; los valores son las acciones admitidas.

CATALOGO = {
    "usuarios": (
        "ver", "crear", "editar", "autorizar",
    ),
    "roles": (
        "ver", "asignar", "revocar",
    ),
    "clientes": (
        "ver", "crear", "editar",
    ),
    "productos": (
    "ver", "crear", "editar",
),
"categorias": (
    "ver", "crear", "editar",
),
    "proveedores": (
        "ver", "crear", "editar",
    ),
    "compras": (
        "ver", "crear", "confirmar", "cancelar",
    ),
    "recepciones": (
        "ver", "crear",
    ),
    "pagos_proveedores": (
        "ver", "registrar", "anular",
    ),
    "inventario": (
        "ver", "ajustar",
    ),
    "pedidos": (
        "ver", "crear", "confirmar", "cancelar",
    ),
    "ventas": (
        "ver", "crear", "confirmar",
    ),
    "entregas": (
        "ver", "confirmar",
    ),
    "pagos": (
        "ver", "registrar", "anular",
    ),
    "analitica": (
        "ver", "ejecutar",
    ),
    "reportes": (
        "ver", "generar", "descargar",
    ),
    "auditoria": (
        "ver",
    ),
    "configuracion": (
        "ver", "editar",
    ),
}


def codigos(*modulos):
    """Devuelve todos los permisos de los modulos indicados."""
    return {
        f"{modulo}.{accion}"
        for modulo in modulos
        for accion in CATALOGO[modulo]
    }


TODOS_LOS_PERMISOS = codigos(*CATALOGO.keys())


# Los permisos de cada rol se definen de forma explicita.
# ADMIN_EMPRESA recibe el catalogo completo.
ROLES = {
    "ADMIN_EMPRESA": {
        "descripcion": "Administrador de su empresa",
        "permisos": TODOS_LOS_PERMISOS,
    },
    "GERENTE": {
        "descripcion": "Supervision y gestion empresarial",
        "permisos": (
            codigos(
                "clientes",
                "proveedores",
                "compras",
                "recepciones",
                "pagos_proveedores",
                "productos",
                "categorias",
                "pedidos",
                "ventas",
                "pagos",
                "analitica",
                "reportes",
            )
            | {
                "inventario.ver",
                "entregas.ver",
                "auditoria.ver",
                "configuracion.ver",
            }
        ),
    },
    "VENDEDOR": {
        "descripcion": "Gestion comercial y ventas",
        "permisos": (
            codigos("clientes", "pedidos", "ventas")
            | {
                "productos.ver",
                "proveedores.ver",
                "compras.ver",
                "compras.crear",
                "recepciones.ver",
                "pagos_proveedores.ver",
                "inventario.ver",
                "categorias.ver",
                "entregas.ver",
                "pagos.ver",
                "pagos.registrar",
            }
        ),
    },
    "ALMACENERO": {
        "descripcion": "Gestion de inventario y entregas",
        "permisos": (
            codigos("inventario", "entregas")
            | {
                "productos.ver",
                "proveedores.ver",
                "compras.ver",
                "recepciones.ver",
                "recepciones.crear",
                "pagos_proveedores.ver",
                "categorias.ver",
                "pedidos.ver",
                "ventas.ver",
            }
        ),
    },
    "ANALISTA": {
        "descripcion": "Analisis y reportes empresariales",
        "permisos": (
            codigos("analitica", "reportes")
            | {
                "clientes.ver",
                "proveedores.ver",
                "compras.ver",
                "recepciones.ver",
                "pagos_proveedores.ver",
                "productos.ver",
                "inventario.ver",
                "categorias.ver",
                "pedidos.ver",
                "ventas.ver",
                "pagos.ver",
                "auditoria.ver",
            }
        ),
    },
}


def validar_catalogo():
    for nombre, configuracion in ROLES.items():
        desconocidos = (
            configuracion["permisos"] - TODOS_LOS_PERMISOS
        )

        if desconocidos:
            raise ValueError(
                f"El rol {nombre} contiene permisos desconocidos: "
                f"{sorted(desconocidos)}"
            )


def ejecutar_seed(
    empresa_id: int,
    aplicar: bool,
    *,
    session_factory=None,
):
    validar_catalogo()

    if session_factory is None:
        raise RuntimeError(
            "SEGURIDAD: debe proporcionarse explícitamente "
            "una fábrica de sesiones para ejecutar el seed."
        )

    with session_factory() as db:
        try:
            empresa = db.execute(
                select(Empresa).where(
                    Empresa.id == empresa_id
                )
            ).scalar_one_or_none()

            if empresa is None:
                raise ValueError(
                    f"No existe la empresa con ID {empresa_id}."
                )

            if not empresa.activo:
                raise ValueError(
                    "La empresa existe, pero esta inactiva."
                )

            print(
                f"\nEmpresa: {empresa.razon_social} "
                f"(ID: {empresa.id})"
            )

            print(
                "Modo:",
                "APLICAR" if aplicar else "SIMULACION",
            )

            nuevos_permisos = 0
            nuevos_roles = 0
            nuevas_asignaciones = 0

            # 1. Crear los permisos globales que falten.
            for modulo, acciones in CATALOGO.items():
                for accion in acciones:
                    codigo = f"{modulo}.{accion}"

                    sentencia = (
                        pg_insert(Permiso.__table__)
                        .values(
                            codigo=codigo,
                            descripcion=(
                                f"{modulo}: {accion}"
                            ),
                        )
                        .on_conflict_do_nothing(
                            index_elements=["codigo"]
                        )
                    )

                    resultado = db.execute(
                        sentencia.returning(Permiso.id)
                )

                    if resultado.scalar_one_or_none() is not None:
                        nuevos_permisos += 1

            db.flush()

            permisos = {
                permiso.codigo: permiso.id
                for permiso in db.execute(
                    select(Permiso).where(
                        Permiso.codigo.in_(
                            sorted(TODOS_LOS_PERMISOS)
                        )
                    )
                ).scalars()
            }

            if set(permisos) != TODOS_LOS_PERMISOS:
                raise RuntimeError(
                    "No se pudo recuperar el catalogo completo."
                )

            # 2. Crear los cinco roles de la empresa.
            for nombre, configuracion in ROLES.items():
                sentencia = (
                    pg_insert(Rol.__table__)
                    .values(
                        empresa_id=empresa_id,
                        nombre=nombre,
                        descripcion=configuracion["descripcion"],
                    )
                    .on_conflict_do_nothing(
                        constraint="uq_rol_empresa_nombre"
                    )
                )

                resultado = db.execute(
                sentencia.returning(Rol.id)
                )

                if resultado.scalar_one_or_none() is not None:
                    nuevos_roles += 1

            db.flush()

            roles = {
                rol.nombre: rol.id
                for rol in db.execute(
                    select(Rol).where(
                        Rol.empresa_id == empresa_id,
                        Rol.nombre.in_(list(ROLES)),
                    )
                ).scalars()
            }

            if set(roles) != set(ROLES):
                raise RuntimeError(
                    "No se pudieron recuperar los cinco roles."
                )

            # 3. Insertar solo las asignaciones que falten.
            for nombre, configuracion in ROLES.items():
                rol_id = roles[nombre]

                for codigo in sorted(configuracion["permisos"]):
                    sentencia = (
                        pg_insert(roles_permisos)
                        .values(
                            rol_id=rol_id,
                            permiso_id=permisos[codigo],
                        )
                        .on_conflict_do_nothing(
                            constraint="pk_roles_permisos"
                        )
                    )

                    resultado = db.execute(
                        sentencia.returning(roles_permisos.c.permiso_id)
                    )

                    if resultado.scalar_one_or_none() is not None:
                        nuevas_asignaciones += 1

            db.flush()

            print("\nRESUMEN")
            print("------------------------------")
            print("Permisos del catalogo:", len(permisos))
            print("Roles empresariales:", len(roles))
            print("Permisos nuevos:", nuevos_permisos)
            print("Roles nuevos:", nuevos_roles)
            print("Asignaciones nuevas:", nuevas_asignaciones)

            if aplicar:
                db.commit()
                print("\nSEED APLICADO CORRECTAMENTE.")
            else:
                db.rollback()
                print(
                    "\nSIMULACION COMPLETADA. "
                    "No se guardaron cambios."
                )

        except Exception:
            db.rollback()
            raise


def main():
    raise SystemExit(
        "SEGURIDAD: ejecución directa bloqueada. "
        "Use python -m scripts.preparar_rbac_testing en PostgreSQL Testing."
    )


if __name__ == "__main__":
    main()
