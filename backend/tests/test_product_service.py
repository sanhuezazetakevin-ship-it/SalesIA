
"""
SalesIA Enterprise — FASE 07-C.3

Pruebas empresariales del servicio de Productos.
Exclusivamente PostgreSQL Testing mediante db_testing.
"""

from decimal import Decimal
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

from app.schemas.productos import ProductoCreate, ProductoUpdate
from app.services.product_service import (
    ProductoServiceError,
    crear_producto,
    obtener_producto,
    listar_productos,
    actualizar_producto,
    desactivar_producto,
)


PERMISOS = (
    "productos.ver",
    "productos.crear",
    "productos.editar",
)


def preparar_escenario(db, *, permisos=PERMISOS):
    identificador = uuid4().hex

    empresa = Empresa(
        razon_social=f"Productos Testing {identificador[:12]}",
        ruc=str(uuid4().int % 10**11).zfill(11),
        moneda_base="PEN",
        activo=True,
    )
    db.add(empresa)
    db.flush()

    rol = Rol(
        empresa_id=empresa.id,
        nombre=f"PROD_TEST_{identificador[:8]}",
        descripcion="Rol temporal de productos",
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
        nombre="Operador Productos Testing",
        email=f"productos-{identificador}@example.com",
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
    db.commit()

    return {
        "empresa_id": empresa.id,
        "usuario_id": usuario.id,
    }


def crear_categoria_temporal(db, empresa_id, nombre="General"):
    categoria = Categoria(
        empresa_id=empresa_id,
        nombre=nombre,
        descripcion="Categoria temporal",
        activo=True,
    )
    db.add(categoria)
    db.commit()
    return categoria.id


def datos_producto(
    *,
    sku="SKU-001",
    categoria_id=None,
    precio="125.50",
):
    return ProductoCreate(
        categoria_id=categoria_id,
        sku=sku,
        nombre="Producto Empresarial Testing",
        descripcion="Descripcion temporal",
        tipo_item="PRODUCTO",
        precio_venta=precio,
        costo_referencia="75.25",
        controla_stock=True,
    )


def test_creacion_producto_con_decimal_y_auditoria(db_testing):
    escenario = preparar_escenario(db_testing)

    producto = crear_producto(
        db_testing,
        usuario_id=escenario["usuario_id"],
        datos=datos_producto(),
    )

    assert producto.id > 0
    assert producto.empresa_id == escenario["empresa_id"]
    assert producto.precio_venta == Decimal("125.50")
    assert producto.costo_referencia == Decimal("75.25")
    assert producto.activo is True

    auditorias = db_testing.scalars(
        select(Auditoria).where(
            Auditoria.empresa_id == escenario["empresa_id"],
            Auditoria.entidad == "productos",
            Auditoria.entidad_id == producto.id,
            Auditoria.accion == "CREAR",
        )
    ).all()

    assert len(auditorias) == 1


def test_usuario_sin_permiso_no_crea_producto(db_testing):
    escenario = preparar_escenario(
        db_testing,
        permisos=("productos.ver",),
    )

    with pytest.raises(ProductoServiceError):
        crear_producto(
            db_testing,
            usuario_id=escenario["usuario_id"],
            datos=datos_producto(),
        )

    assert db_testing.scalar(
        select(func.count(Producto.id)).where(
            Producto.empresa_id == escenario["empresa_id"]
        )
    ) == 0


def test_sku_duplicado_en_misma_empresa(db_testing):
    escenario = preparar_escenario(db_testing)

    primero = crear_producto(
        db_testing,
        usuario_id=escenario["usuario_id"],
        datos=datos_producto(),
    )

    with pytest.raises(
        ProductoServiceError,
        match="Ya existe un producto",
    ):
        crear_producto(
            db_testing,
            usuario_id=escenario["usuario_id"],
            datos=datos_producto(),
        )

    assert primero.id > 0

    assert db_testing.scalar(
        select(func.count(Producto.id)).where(
            Producto.empresa_id == escenario["empresa_id"],
            Producto.sku == "SKU-001",
        )
    ) == 1


def test_mismo_sku_en_empresas_distintas(db_testing):
    empresa_a = preparar_escenario(db_testing)
    empresa_b = preparar_escenario(db_testing)

    producto_a = crear_producto(
        db_testing,
        usuario_id=empresa_a["usuario_id"],
        datos=datos_producto(),
    )

    producto_b = crear_producto(
        db_testing,
        usuario_id=empresa_b["usuario_id"],
        datos=datos_producto(),
    )

    assert producto_a.id != producto_b.id
    assert producto_a.sku == producto_b.sku
    assert producto_a.empresa_id != producto_b.empresa_id


def test_producto_rechaza_categoria_de_otra_empresa(db_testing):
    empresa_a = preparar_escenario(db_testing)
    empresa_b = preparar_escenario(db_testing)

    categoria_b = crear_categoria_temporal(
        db_testing,
        empresa_b["empresa_id"],
    )

    with pytest.raises(ProductoServiceError):
        crear_producto(
            db_testing,
            usuario_id=empresa_a["usuario_id"],
            datos=datos_producto(categoria_id=categoria_b),
        )

    assert db_testing.scalar(
        select(func.count(Producto.id)).where(
            Producto.empresa_id == empresa_a["empresa_id"]
        )
    ) == 0


def test_producto_admite_categoria_propia_activa(db_testing):
    escenario = preparar_escenario(db_testing)

    categoria_id = crear_categoria_temporal(
        db_testing,
        escenario["empresa_id"],
    )

    producto = crear_producto(
        db_testing,
        usuario_id=escenario["usuario_id"],
        datos=datos_producto(categoria_id=categoria_id),
    )

    assert producto.categoria_id == categoria_id


def test_consulta_y_listado_aislados(db_testing):
    empresa_a = preparar_escenario(db_testing)
    empresa_b = preparar_escenario(db_testing)

    producto_b = crear_producto(
        db_testing,
        usuario_id=empresa_b["usuario_id"],
        datos=datos_producto(),
    )

    with pytest.raises(ProductoServiceError):
        obtener_producto(
            db_testing,
            usuario_id=empresa_a["usuario_id"],
            producto_id=producto_b.id,
        )

    listado_a = listar_productos(
        db_testing,
        usuario_id=empresa_a["usuario_id"],
    )

    assert listado_a["total"] == 0
    assert listado_a["productos"] == []


def test_busqueda_filtro_y_paginacion(db_testing):
    escenario = preparar_escenario(db_testing)

    for indice in range(1, 4):
        crear_producto(
            db_testing,
            usuario_id=escenario["usuario_id"],
            datos=datos_producto(
                sku=f"SKU-{indice:03d}",
            ),
        )

    resultado = listar_productos(
        db_testing,
        usuario_id=escenario["usuario_id"],
        busqueda="SKU-002",
    )

    assert resultado["total"] == 1
    assert resultado["productos"][0].sku == "SKU-002"

    segunda_pagina = listar_productos(
        db_testing,
        usuario_id=escenario["usuario_id"],
        pagina=2,
        limite=2,
        tipo_item="PRODUCTO",
        activo=True,
    )

    assert segunda_pagina["total"] == 3
    assert len(segunda_pagina["productos"]) == 1


def test_actualizacion_parcial_con_auditoria(db_testing):
    escenario = preparar_escenario(db_testing)

    producto = crear_producto(
        db_testing,
        usuario_id=escenario["usuario_id"],
        datos=datos_producto(),
    )

    resultado = actualizar_producto(
        db_testing,
        usuario_id=escenario["usuario_id"],
        producto_id=producto.id,
        datos=ProductoUpdate(
            nombre="Producto Actualizado",
            precio_venta="150.75",
        ),
    )

    assert resultado.nombre == "Producto Actualizado"
    assert resultado.precio_venta == Decimal("150.75")
    assert resultado.sku == "SKU-001"

    auditorias = db_testing.scalars(
        select(Auditoria).where(
            Auditoria.empresa_id == escenario["empresa_id"],
            Auditoria.entidad == "productos",
            Auditoria.entidad_id == producto.id,
            Auditoria.accion == "ACTUALIZAR",
        )
    ).all()

    assert len(auditorias) == 1
    assert auditorias[0].datos_anteriores["precio_venta"] == "125.50"
    assert auditorias[0].datos_nuevos["precio_venta"] == "150.75"


def test_baja_logica_y_auditoria(db_testing):
    escenario = preparar_escenario(db_testing)

    producto = crear_producto(
        db_testing,
        usuario_id=escenario["usuario_id"],
        datos=datos_producto(),
    )

    producto_id = producto.id

    resultado = desactivar_producto(
        db_testing,
        usuario_id=escenario["usuario_id"],
        producto_id=producto_id,
    )

    assert resultado.activo is False

    db_testing.expire_all()

    conservado = db_testing.get(Producto, producto_id)

    assert conservado is not None
    assert conservado.activo is False

    with pytest.raises(
        ProductoServiceError,
        match="ya se encuentra inactivo",
    ):
        desactivar_producto(
            db_testing,
            usuario_id=escenario["usuario_id"],
            producto_id=producto_id,
        )

    auditorias = db_testing.scalars(
        select(Auditoria).where(
            Auditoria.empresa_id == escenario["empresa_id"],
            Auditoria.entidad == "productos",
            Auditoria.entidad_id == producto_id,
            Auditoria.descripcion ==
            "Desactivacion empresarial de producto.",
        )
    ).all()

    assert len(auditorias) == 1
