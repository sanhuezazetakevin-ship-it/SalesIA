
"""
SalesIA Enterprise
FASE 05-A.6

Aislamiento multiempresa utilizando PostgreSQL Testing.

Los registros de prueba deben revertirse mediante
la fixture db_testing de tests/conftest.py.
"""

from uuid import uuid4

from sqlalchemy import select

from app.models.empresa import Empresa
from app.models.usuario import Usuario


def crear_empresa(db, identificador: int) -> Empresa:
    empresa = Empresa(
        razon_social=f"Empresa Testing {identificador}",
        ruc=f"{identificador:011d}",
        moneda_base="PEN",
        activo=True,
    )

    db.add(empresa)
    db.flush()

    return empresa


def crear_usuario(db, empresa: Empresa, identificador: str) -> Usuario:
    usuario = Usuario(
        empresa_id=empresa.id,
        nombre=f"Usuario Testing {identificador}",
        email=f"tenant-{identificador}-{uuid4().hex}@example.com",
        password_hash="hash-ficticio-no-utilizable",
        activo=True,
    )

    db.add(usuario)
    db.flush()

    return usuario


def obtener_usuario_de_empresa(
    db,
    *,
    usuario_id: int,
    empresa_id: int,
) -> Usuario | None:
    """
    La consulta exige simultáneamente el identificador
    del recurso y el de la empresa autenticada.
    """

    return db.scalar(
        select(Usuario).where(
            Usuario.id == usuario_id,
            Usuario.empresa_id == empresa_id,
        )
    )


def test_empresa_a_no_accede_usuario_empresa_b(db_testing):
    db = db_testing

    empresa_a = crear_empresa(db, 81000000001)
    empresa_b = crear_empresa(db, 82000000002)

    usuario_a = crear_usuario(db, empresa_a, "A")
    usuario_b = crear_usuario(db, empresa_b, "B")

    resultado_a = obtener_usuario_de_empresa(
        db,
        usuario_id=usuario_a.id,
        empresa_id=empresa_a.id,
    )

    resultado_ajeno = obtener_usuario_de_empresa(
        db,
        usuario_id=usuario_b.id,
        empresa_id=empresa_a.id,
    )

    assert resultado_a is not None
    assert resultado_a.id == usuario_a.id
    assert resultado_ajeno is None


def test_empresa_b_no_accede_usuario_empresa_a(db_testing):
    db = db_testing

    empresa_a = crear_empresa(db, 83000000003)
    empresa_b = crear_empresa(db, 84000000004)

    usuario_a = crear_usuario(db, empresa_a, "A")
    usuario_b = crear_usuario(db, empresa_b, "B")

    resultado_b = obtener_usuario_de_empresa(
        db,
        usuario_id=usuario_b.id,
        empresa_id=empresa_b.id,
    )

    resultado_ajeno = obtener_usuario_de_empresa(
        db,
        usuario_id=usuario_a.id,
        empresa_id=empresa_b.id,
    )

    assert resultado_b is not None
    assert resultado_b.id == usuario_b.id
    assert resultado_ajeno is None


def test_listado_filtrado_por_empresa(db_testing):
    db = db_testing

    empresa_a = crear_empresa(db, 85000000005)
    empresa_b = crear_empresa(db, 86000000006)

    usuario_a = crear_usuario(db, empresa_a, "A")
    usuario_b = crear_usuario(db, empresa_b, "B")

    usuarios_empresa_a = db.scalars(
        select(Usuario).where(
            Usuario.empresa_id == empresa_a.id
        )
    ).all()

    ids = {usuario.id for usuario in usuarios_empresa_a}

    assert usuario_a.id in ids
    assert usuario_b.id not in ids


def test_empresa_id_incorrecto_no_devuelve_registro(db_testing):
    db = db_testing

    empresa_a = crear_empresa(db, 87000000007)
    empresa_b = crear_empresa(db, 88000000008)

    usuario_a = crear_usuario(db, empresa_a, "A")

    resultado = obtener_usuario_de_empresa(
        db,
        usuario_id=usuario_a.id,
        empresa_id=empresa_b.id,
    )

    assert resultado is None
