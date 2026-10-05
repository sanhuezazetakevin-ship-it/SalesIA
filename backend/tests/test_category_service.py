
"""
SalesIA Enterprise — FASE 07-C.1

Pruebas empresariales del servicio de Categorias.
Exclusivamente PostgreSQL Testing mediante db_testing.
"""

from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.permiso import Permiso
from app.models.categoria import Categoria
from app.models.producto import Producto
from app.models.auditoria import Auditoria
from app.models.asociaciones import usuarios_roles, roles_permisos

from app.schemas.categorias import CategoriaCreate, CategoriaUpdate

from app.services.category_service import (
    CategoriaServiceError,
    crear_categoria,
    obtener_categoria,
    listar_categorias,
    actualizar_categoria,
    desactivar_categoria,
)


PERMISOS = (
    "categorias.ver",
    "categorias.crear",
    "categorias.editar",
)


def preparar_escenario(db, *, permisos=PERMISOS):
    identificador = uuid4().hex

    empresa = Empresa(
        razon_social=f"Categorias Testing {identificador[:12]}",
        ruc=str(uuid4().int % 10**11).zfill(11),
        moneda_base="PEN",
        activo=True,
    )
    db.add(empresa)
    db.flush()

    rol = Rol(
        empresa_id=empresa.id,
        nombre=f"CAT_TEST_{identificador[:8]}",
        descripcion="Rol temporal para pruebas de categorias",
    )
    db.add(rol)
    db.flush()

    for codigo in permisos:
        permiso = db.scalar(
            select(Permiso).where(Permiso.codigo == codigo)
        )

        if permiso is None:
            permiso = Permiso(
                codigo=codigo,
                descripcion=f"Permiso temporal {codigo}",
            )
            db.add(permiso)
            db.flush()

        db.execute(
            roles_permisos.insert().values(
                rol_id=rol.id,
                permiso_id=permiso.id,
            )
        )

    usuario = Usuario(
        empresa_id=empresa.id,
        nombre="Operador Categorias Testing",
        email=f"categorias-{identificador}@example.com",
        password_hash="hash-ficticio-no-utilizable",
        activo=True,
    )
    db.add(usuario)
    db.flush()

    db.execute(
        usuarios_roles.insert().values(
            usuario_id=usuario.id,
            rol_id=rol.id,
            empresa_id=empresa.id,
        )
    )

    # El commit solo libera el savepoint. La fixture mantiene
    # su transaccion exterior y realiza rollback al finalizar.
    db.commit()

    return {
        "empresa_id": empresa.id,
        "usuario_id": usuario.id,
    }


def nueva_categoria(nombre="Electronica"):
    return CategoriaCreate(
        nombre=nombre,
        descripcion="Categoria empresarial de prueba",
    )


def test_crear_categoria_con_auditoria(db_testing):
    escenario = preparar_escenario(db_testing)

    categoria = crear_categoria(
        db_testing,
        usuario_id=escenario["usuario_id"],
        datos=nueva_categoria(),
    )

    assert categoria.id > 0
    assert categoria.empresa_id == escenario["empresa_id"]
    assert categoria.activo is True

    auditorias = db_testing.scalars(
        select(Auditoria).where(
            Auditoria.empresa_id == escenario["empresa_id"],
            Auditoria.entidad == "categorias",
            Auditoria.entidad_id == categoria.id,
            Auditoria.accion == "CREAR",
        )
    ).all()

    assert len(auditorias) == 1


def test_sin_permiso_crear_no_registra_categoria(db_testing):
    escenario = preparar_escenario(
        db_testing,
        permisos=("categorias.ver",),
    )

    with pytest.raises(CategoriaServiceError):
        crear_categoria(
            db_testing,
            usuario_id=escenario["usuario_id"],
            datos=nueva_categoria(),
        )

    cantidad = db_testing.scalar(
        select(func.count(Categoria.id)).where(
            Categoria.empresa_id == escenario["empresa_id"]
        )
    )
    assert cantidad == 0


def test_nombre_duplicado_en_misma_empresa(db_testing):
    escenario = preparar_escenario(db_testing)

    primera = crear_categoria(
        db_testing,
        usuario_id=escenario["usuario_id"],
        datos=nueva_categoria(),
    )

    with pytest.raises(
        CategoriaServiceError,
        match="ya existe",
    ):
        crear_categoria(
            db_testing,
            usuario_id=escenario["usuario_id"],
            datos=nueva_categoria(),
        )

    cantidad = db_testing.scalar(
        select(func.count(Categoria.id)).where(
            Categoria.empresa_id == escenario["empresa_id"],
            Categoria.nombre == "Electronica",
        )
    )

    assert primera.id > 0
    assert cantidad == 1


def test_consulta_aislada_entre_empresas(db_testing):
    empresa_a = preparar_escenario(db_testing)
    empresa_b = preparar_escenario(db_testing)

    categoria_b = crear_categoria(
        db_testing,
        usuario_id=empresa_b["usuario_id"],
        datos=nueva_categoria(),
    )

    with pytest.raises(CategoriaServiceError):
        obtener_categoria(
            db_testing,
            usuario_id=empresa_a["usuario_id"],
            categoria_id=categoria_b.id,
        )

    listado = listar_categorias(
        db_testing,
        usuario_id=empresa_a["usuario_id"],
    )

    assert listado["total"] == 0
    assert listado["categorias"] == []


def test_listado_busqueda_filtro_y_paginacion(db_testing):
    escenario = preparar_escenario(db_testing)

    for nombre in (
        "Electronica",
        "Ferreteria",
        "Libreria",
    ):
        crear_categoria(
            db_testing,
            usuario_id=escenario["usuario_id"],
            datos=nueva_categoria(nombre),
        )

    busqueda = listar_categorias(
        db_testing,
        usuario_id=escenario["usuario_id"],
        busqueda="ferre",
    )

    assert busqueda["total"] == 1
    assert busqueda["categorias"][0].nombre == "Ferreteria"

    pagina = listar_categorias(
        db_testing,
        usuario_id=escenario["usuario_id"],
        pagina=2,
        limite=2,
    )

    assert pagina["total"] == 3
    assert len(pagina["categorias"]) == 1

    with pytest.raises(CategoriaServiceError):
        listar_categorias(
            db_testing,
            usuario_id=escenario["usuario_id"],
            limite=101,
        )


def test_actualizar_categoria_registra_cambios(db_testing):
    escenario = preparar_escenario(db_testing)

    categoria = crear_categoria(
        db_testing,
        usuario_id=escenario["usuario_id"],
        datos=nueva_categoria(),
    )

    resultado = actualizar_categoria(
        db_testing,
        usuario_id=escenario["usuario_id"],
        categoria_id=categoria.id,
        datos=CategoriaUpdate(nombre="Tecnologia"),
    )

    assert resultado.nombre == "Tecnologia"
    assert resultado.descripcion == "Categoria empresarial de prueba"

    auditorias = db_testing.scalars(
        select(Auditoria).where(
            Auditoria.empresa_id == escenario["empresa_id"],
            Auditoria.entidad == "categorias",
            Auditoria.entidad_id == categoria.id,
            Auditoria.accion == "ACTUALIZAR",
        )
    ).all()

    assert len(auditorias) == 1
    assert auditorias[0].datos_anteriores == {
        "nombre": "Electronica",
    }
    assert auditorias[0].datos_nuevos == {
        "nombre": "Tecnologia",
    }


def test_baja_logica_y_segunda_desactivacion(db_testing):
    escenario = preparar_escenario(db_testing)

    categoria = crear_categoria(
        db_testing,
        usuario_id=escenario["usuario_id"],
        datos=nueva_categoria(),
    )

    categoria_id = categoria.id

    resultado = desactivar_categoria(
        db_testing,
        usuario_id=escenario["usuario_id"],
        categoria_id=categoria_id,
    )

    assert resultado.activo is False

    db_testing.expire_all()
    conservada = db_testing.get(Categoria, categoria_id)

    assert conservada is not None
    assert conservada.activo is False

    with pytest.raises(
        CategoriaServiceError,
        match="ya se encuentra inactiva",
    ):
        desactivar_categoria(
            db_testing,
            usuario_id=escenario["usuario_id"],
            categoria_id=categoria_id,
        )

    auditorias = db_testing.scalars(
        select(Auditoria).where(
            Auditoria.empresa_id == escenario["empresa_id"],
            Auditoria.entidad == "categorias",
            Auditoria.entidad_id == categoria_id,
            Auditoria.descripcion ==
            "Desactivacion empresarial de categoria.",
        )
    ).all()

    assert len(auditorias) == 1


def test_categoria_con_producto_activo_no_se_desactiva(db_testing):
    escenario = preparar_escenario(db_testing)

    categoria = crear_categoria(
        db_testing,
        usuario_id=escenario["usuario_id"],
        datos=nueva_categoria(),
    )

    producto = Producto(
        empresa_id=escenario["empresa_id"],
        categoria_id=categoria.id,
        sku=f"TEST-{uuid4().hex[:12]}",
        nombre="Producto temporal",
        tipo_item="PRODUCTO",
        precio_venta="25.00",
        costo_referencia="10.00",
        controla_stock=True,
        activo=True,
    )

    db_testing.add(producto)
    db_testing.commit()

    with pytest.raises(
        CategoriaServiceError,
        match="productos activos",
    ):
        desactivar_categoria(
            db_testing,
            usuario_id=escenario["usuario_id"],
            categoria_id=categoria.id,
        )

    db_testing.expire_all()
    assert db_testing.get(Categoria, categoria.id).activo is True
