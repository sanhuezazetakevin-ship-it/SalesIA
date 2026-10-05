
from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import configure_mappers
from sqlalchemy.schema import CreateIndex, CreateTable

import app.models
from app.database.base import Base


EXPECTED_TABLES = {
    "auditoria",
    "analisis_estadisticos",
    "analisis_probabilidad",
    "insights",
    "reportes_generados",
}

EXPECTED_INDEXES = {
    "auditoria": 4,
    "analisis_estadisticos": 4,
    "analisis_probabilidad": 5,
    "insights": 6,
    "reportes_generados": 5,
}

EXPECTED_CHECKS = {
    "auditoria": {
        "ck_auditoria_accion",
        "ck_auditoria_entidad",
        "ck_auditoria_entidad_id",
    },
    "analisis_estadisticos": {
        "ck_analisis_estadistico_tipo",
        "ck_analisis_estadistico_estado",
        "ck_analisis_estadistico_periodo",
        "ck_analisis_estadistico_nombre",
        "ck_analisis_estadistico_resultado_estado",
    },
    "analisis_probabilidad": {
        "ck_analisis_probabilidad_tipo",
        "ck_analisis_probabilidad_estado",
        "ck_analisis_probabilidad_rango",
        "ck_analisis_probabilidad_entidad_id",
        "ck_analisis_probabilidad_modelo",
        "ck_analisis_probabilidad_resultado_estado",
    },
    "insights": {
        "ck_insight_origen_exclusivo",
        "ck_insight_tipo",
        "ck_insight_prioridad",
        "ck_insight_estado",
        "ck_insight_contenido",
    },
    "reportes_generados": {
        "ck_reporte_tipo",
        "ck_reporte_formato",
        "ck_reporte_estado",
        "ck_reporte_nombre",
        "ck_reporte_tamano",
        "ck_reporte_resultado_estado",
        "ck_reporte_error_fallido",
    },
}

EXPECTED_FOREIGN_KEYS = {
    "auditoria": {
        "fk_auditoria_empresa",
        "fk_auditoria_usuario_empresa",
    },
    "analisis_estadisticos": {
        "fk_analisis_estadistico_empresa",
    },
    "analisis_probabilidad": {
        "fk_analisis_probabilidad_empresa",
    },
    "insights": {
        "fk_insight_empresa",
        "fk_insight_analisis_estadistico_empresa",
        "fk_insight_analisis_probabilidad_empresa",
    },
    "reportes_generados": {
        "fk_reporte_empresa",
        "fk_reporte_usuario_empresa",
    },
}


def verify(condition, message):
    if not condition:
        raise AssertionError(message)

    print(f"[OK] {message}")


def constraint_names(table, constraint_type):
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, constraint_type)
    }


def verify_composite_fk(table, name, local, remote):
    matches = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
        and constraint.name == name
    ]

    verify(
        len(matches) == 1,
        f"{table.name}: existe {name}",
    )

    constraint = matches[0]

    local_columns = tuple(
        element.parent.name
        for element in constraint.elements
    )

    remote_columns = tuple(
        element.target_fullname
        for element in constraint.elements
    )

    verify(
        local_columns == local
        and remote_columns == remote,
        f"{table.name}: columnas correctas en {name}",
    )


def verify_unique(table, name, columns):
    matches = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
        and constraint.name == name
    ]

    verify(
        len(matches) == 1
        and tuple(matches[0].columns.keys()) == columns,
        f"{table.name}: UNIQUE {name}",
    )


def main():
    print("\n=== AUDITORIA INTEGRAL 006-F ===\n")

    configure_mappers()
    verify(True, "Configuracion ORM valida")

    metadata = Base.metadata

    verify(
        len(metadata.tables) == 31,
        "31 tablas empresariales registradas",
    )

    verify(
        EXPECTED_TABLES.issubset(metadata.tables.keys()),
        "Cinco tablas nuevas registradas",
    )

    dialect = postgresql.dialect()

    for table_name in sorted(EXPECTED_TABLES):
        table = metadata.tables[table_name]

        print(f"\n--- {table_name} ---")

        checks = constraint_names(
            table,
            CheckConstraint,
        )

        verify(
            EXPECTED_CHECKS[table_name].issubset(checks),
            f"{table_name}: restricciones CHECK",
        )

        foreign_keys = constraint_names(
            table,
            ForeignKeyConstraint,
        )

        verify(
            EXPECTED_FOREIGN_KEYS[table_name].issubset(
                foreign_keys
            ),
            f"{table_name}: claves foraneas",
        )

        verify(
            len(table.indexes) == EXPECTED_INDEXES[table_name],
            f"{table_name}: cantidad de indices",
        )

        index_names = [index.name for index in table.indexes]

        verify(
            len(index_names) == len(set(index_names)),
            f"{table_name}: indices sin nombres duplicados",
        )

        CreateTable(table).compile(dialect=dialect)

        for index in table.indexes:
            CreateIndex(index).compile(dialect=dialect)

        verify(
            True,
            f"{table_name}: compilacion PostgreSQL correcta",
        )

    estadistico = metadata.tables["analisis_estadisticos"]
    probabilidad = metadata.tables["analisis_probabilidad"]
    insights = metadata.tables["insights"]

    verify_unique(
        estadistico,
        "uq_analisis_estadistico_id_empresa",
        ("id", "empresa_id"),
    )

    verify_unique(
        probabilidad,
        "uq_analisis_probabilidad_id_empresa",
        ("id", "empresa_id"),
    )

    verify_composite_fk(
        insights,
        "fk_insight_analisis_estadistico_empresa",
        ("analisis_estadistico_id", "empresa_id"),
        (
            "analisis_estadisticos.id",
            "analisis_estadisticos.empresa_id",
        ),
    )

    verify_composite_fk(
        insights,
        "fk_insight_analisis_probabilidad_empresa",
        ("analisis_probabilidad_id", "empresa_id"),
        (
            "analisis_probabilidad.id",
            "analisis_probabilidad.empresa_id",
        ),
    )

    verify_composite_fk(
        metadata.tables["auditoria"],
        "fk_auditoria_usuario_empresa",
        ("usuario_id", "empresa_id"),
        ("usuarios.id", "usuarios.empresa_id"),
    )

    verify_composite_fk(
        metadata.tables["reportes_generados"],
        "fk_reporte_usuario_empresa",
        ("solicitado_por_id", "empresa_id"),
        ("usuarios.id", "usuarios.empresa_id"),
    )

    verify(
        str(probabilidad.c.probabilidad.type)
        == "NUMERIC(7, 6)",
        "Precision de probabilidad correcta",
    )

    for table_name, column_name in (
        ("auditoria", "datos_anteriores"),
        ("auditoria", "datos_nuevos"),
        ("analisis_estadisticos", "resultados"),
        ("analisis_probabilidad", "datos_entrada"),
        ("analisis_probabilidad", "resultados"),
        ("insights", "datos_soporte"),
        ("reportes_generados", "parametros"),
    ):
        column = metadata.tables[table_name].c[column_name]

        compiled_type = column.type.compile(
            dialect=dialect
        )

        verify(
            compiled_type == "JSONB",
            f"{table_name}.{column_name}: JSONB",
        )

    creation_order = [
        table.name
        for table in metadata.sorted_tables
    ]

    verify(
        creation_order.index("analisis_estadisticos")
        < creation_order.index("insights"),
        "Orden de creacion: estadistico antes de insights",
    )

    verify(
        creation_order.index("analisis_probabilidad")
        < creation_order.index("insights"),
        "Orden de creacion: probabilidad antes de insights",
    )

    print("\n===================================")
    print("AUDITORIA 006-F: APROBADA")
    print("Modelos nuevos: 5")
    print("Tablas ORM totales: 31")
    print("Indices nuevos: 24")
    print("===================================")


if __name__ == "__main__":
    main()
