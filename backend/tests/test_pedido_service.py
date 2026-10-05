
"""
SalesIA Enterprise — FASE 08-C.3

Integracion empresarial del servicio de pedidos.

Exclusivamente PostgreSQL Testing mediante db_testing.
La fixture protegida verifica aislamiento y revierte
la transaccion exterior al finalizar cada prueba.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.security import hash_password
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.permiso import Permiso
from app.models.asociaciones import usuarios_roles, roles_permisos
from app.models.cliente import Cliente
from app.models.producto import Producto
from app.models.impuesto import Impuesto
from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle
from app.models.auditoria import Auditoria
from app.models.reserva_stock import ReservaStock
from app.models.movimiento_inventario import MovimientoInventario
from app.models.inventario import Inventario
from app.schemas.pedidos import PedidoCreate

from app.services.pedido_service import (
    PedidoServiceError,
    crear_pedido,
    obtener_pedido,
    listar_pedidos,
    confirmar_pedido,
)

def preparar_empresa(
    db,
    *,
    permisos=("pedidos.crear",),
    con_impuesto=True,
):
    identificador = uuid4().hex

    empresa = Empresa(
        razon_social=f"Pedidos Testing {identificador[:12]}",
        ruc=str(uuid4().int % 10**11).zfill(11),
        moneda_base="PEN",
        activo=True,
    )
    db.add(empresa)
    db.flush()

    usuario = Usuario(
        empresa_id=empresa.id,
        nombre="Operador Pedidos",
        email=f"pedidos-{identificador}@example.com",
        password_hash=hash_password("PedidosTesting#2026"),
        activo=True,
    )
    db.add(usuario)
    db.flush()

    rol = Rol(
        empresa_id=empresa.id,
        nombre=f"PEDIDOS_{identificador[:8]}",
        descripcion="Rol temporal de pruebas",
    )
    db.add(rol)
    db.flush()

    db.execute(
        usuarios_roles.insert().values(
            usuario_id=usuario.id,
            rol_id=rol.id,
            empresa_id=empresa.id,
        )
    )

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

    cliente = Cliente(
        empresa_id=empresa.id,
        nombre="Cliente Empresarial Testing",
        tipo_documento="DNI",
        numero_documento=str(uuid4().int % 10**8).zfill(8),
        activo=True,
    )
    db.add(cliente)

    producto = Producto(
        empresa_id=empresa.id,
        categoria_id=None,
        sku=f"SKU-PED-{identificador[:12]}",
        nombre="Producto de Prueba",
        descripcion="Producto temporal para pedidos",
        tipo_item="PRODUCTO",
        precio_venta=Decimal("118.00"),
        costo_referencia=Decimal("70.00"),
        controla_stock=True,
        activo=True,
    )
    db.add(producto)
    db.flush()

    impuesto = None

    if con_impuesto:
        impuesto = Impuesto(
            empresa_id=empresa.id,
            codigo="IGV",
            nombre="Impuesto General",
            tasa=Decimal("18.0000"),
            incluido_en_precio=True,
            activo=True,
        )
        db.add(impuesto)
        db.flush()

    # Solo confirma el savepoint de db_testing.
    # No confirma la transaccion exterior protegida.
    db.commit()

    return {
        "empresa_id": empresa.id,
        "usuario_id": usuario.id,
        "cliente_id": cliente.id,
        "producto_id": producto.id,
        "impuesto_id": impuesto.id if impuesto else None,
    }


def datos_pedido(escenario, **cambios):
    datos = {
        "cliente_id": escenario["cliente_id"],
        "detalles": [
            {
                "producto_id": escenario["producto_id"],
                "cantidad": "2.000",
                "descuento": "11.80",
            }
        ],
        "observaciones": "Borrador de Testing",
    }
    datos.update(cambios)
    return PedidoCreate.model_validate(datos)


def contar(db, modelo, empresa_id):
    return db.scalar(
        select(func.count())
        .select_from(modelo)
        .where(modelo.empresa_id == empresa_id)
    )


def test_crear_borrador_y_detalle(db_testing):
    db = db_testing
    e = preparar_empresa(db)

    resultado = crear_pedido(
        db,
        usuario_id=e["usuario_id"],
        datos=datos_pedido(e),
    )

    pedido = resultado["pedido"]
    detalles = resultado["detalles"]

    assert pedido.id > 0
    assert pedido.empresa_id == e["empresa_id"]
    assert pedido.usuario_id == e["usuario_id"]
    assert pedido.cliente_id == e["cliente_id"]
    assert pedido.estado == "BORRADOR"
    assert pedido.codigo.startswith("PED-")

    assert len(detalles) == 1
    assert detalles[0].pedido_id == pedido.id
    assert detalles[0].producto_id == e["producto_id"]

    db.expire_all()

    assert db.get(Pedido, pedido.id) is not None
    assert len(
        db.scalars(
            select(PedidoDetalle).where(
                PedidoDetalle.pedido_id == pedido.id
            )
        ).all()
    ) == 1


def test_importes_con_impuestos_incluidos(db_testing):
    db = db_testing
    e = preparar_empresa(db)

    resultado = crear_pedido(
        db,
        usuario_id=e["usuario_id"],
        datos=datos_pedido(e),
    )

    pedido = resultado["pedido"]
    detalle = resultado["detalles"][0]

    # 2 x 118.00 = 236.00
    # Descuento final: 11.80
    # Total: 224.20 (impuesto incluido).
    assert detalle.precio_unitario == Decimal("118.00")
    assert detalle.descuento == Decimal("11.80")
    assert detalle.total == Decimal("224.20")
    assert detalle.subtotal == Decimal("190.00")
    assert detalle.impuesto == Decimal("34.20")

    assert pedido.subtotal == Decimal("190.00")
    assert pedido.impuesto_total == Decimal("34.20")
    assert pedido.total == Decimal("224.20")
    assert pedido.subtotal + pedido.impuesto_total == pedido.total


def test_creacion_registra_auditoria(db_testing):
    db = db_testing
    e = preparar_empresa(db)

    resultado = crear_pedido(
        db,
        usuario_id=e["usuario_id"],
        datos=datos_pedido(e),
    )
    pedido = resultado["pedido"]

    registros = db.scalars(
        select(Auditoria).where(
            Auditoria.empresa_id == e["empresa_id"],
            Auditoria.usuario_id == e["usuario_id"],
            Auditoria.entidad == "pedidos",
            Auditoria.entidad_id == pedido.id,
            Auditoria.accion == "CREAR",
        )
    ).all()

    assert len(registros) == 1
    assert registros[0].datos_nuevos["estado"] == "BORRADOR"
    assert (
        registros[0].datos_nuevos["tasa_impuesto_borrador"]
        == "18.0000"
    )


def test_borrador_no_modifica_inventario(db_testing):
    db = db_testing
    e = preparar_empresa(db)

    crear_pedido(
        db,
        usuario_id=e["usuario_id"],
        datos=datos_pedido(e),
    )

    assert contar(db, ReservaStock, e["empresa_id"]) == 0
    assert contar(db, MovimientoInventario, e["empresa_id"]) == 0


def test_rechaza_usuario_sin_permiso(db_testing):
    db = db_testing
    e = preparar_empresa(db, permisos=())

    with pytest.raises(PedidoServiceError, match="autorizacion"):
        crear_pedido(
            db,
            usuario_id=e["usuario_id"],
            datos=datos_pedido(e),
        )

    assert contar(db, Pedido, e["empresa_id"]) == 0


def test_rechaza_cliente_de_otra_empresa(db_testing):
    db = db_testing
    a = preparar_empresa(db)
    b = preparar_empresa(db)

    datos = datos_pedido(
        a,
        cliente_id=b["cliente_id"],
    )

    with pytest.raises(PedidoServiceError, match="cliente"):
        crear_pedido(
            db,
            usuario_id=a["usuario_id"],
            datos=datos,
        )

    assert contar(db, Pedido, a["empresa_id"]) == 0


def test_rechaza_producto_de_otra_empresa(db_testing):
    db = db_testing
    a = preparar_empresa(db)
    b = preparar_empresa(db)

    datos = datos_pedido(a)
    datos.detalles[0].producto_id = b["producto_id"]

    with pytest.raises(PedidoServiceError, match="productos"):
        crear_pedido(
            db,
            usuario_id=a["usuario_id"],
            datos=datos,
        )

    assert contar(db, Pedido, a["empresa_id"]) == 0


@pytest.mark.parametrize("entidad", ["cliente", "producto"])
def test_rechaza_entidades_inactivas(db_testing, entidad):
    db = db_testing
    e = preparar_empresa(db)

    if entidad == "cliente":
        db.get(Cliente, e["cliente_id"]).activo = False
    else:
        db.get(Producto, e["producto_id"]).activo = False

    db.commit()

    with pytest.raises(PedidoServiceError):
        crear_pedido(
            db,
            usuario_id=e["usuario_id"],
            datos=datos_pedido(e),
        )

    assert contar(db, Pedido, e["empresa_id"]) == 0


def test_rechaza_empresa_sin_impuesto_activo(db_testing):
    db = db_testing
    e = preparar_empresa(db, con_impuesto=False)

    with pytest.raises(PedidoServiceError, match="impuesto"):
        crear_pedido(
            db,
            usuario_id=e["usuario_id"],
            datos=datos_pedido(e),
        )

    assert contar(db, Pedido, e["empresa_id"]) == 0


def test_rechaza_impuestos_activos_ambiguos(db_testing):
    db = db_testing
    e = preparar_empresa(db)

    db.add(
        Impuesto(
            empresa_id=e["empresa_id"],
            codigo="OTRO",
            nombre="Segundo impuesto de prueba",
            tasa=Decimal("10.0000"),
            incluido_en_precio=True,
            activo=True,
        )
    )
    db.commit()

    with pytest.raises(PedidoServiceError, match="impuesto"):
        crear_pedido(
            db,
            usuario_id=e["usuario_id"],
            datos=datos_pedido(e),
        )

    assert contar(db, Pedido, e["empresa_id"]) == 0


def test_rechaza_descuento_superior_al_bruto(db_testing):
    db = db_testing
    e = preparar_empresa(db)

    datos = datos_pedido(e)
    datos.detalles[0].descuento = Decimal("300.00")

    with pytest.raises(PedidoServiceError, match="Importes invalidos"):
        crear_pedido(
            db,
            usuario_id=e["usuario_id"],
            datos=datos,
        )

    assert contar(db, Pedido, e["empresa_id"]) == 0
    assert contar(db, PedidoDetalle, e["empresa_id"]) == 0
    assert contar(db, Auditoria, e["empresa_id"]) == 0


def test_codigo_unico_para_borradores(db_testing):
    db = db_testing
    e = preparar_empresa(db)

    primero = crear_pedido(
        db,
        usuario_id=e["usuario_id"],
        datos=datos_pedido(e),
    )

    segundo = crear_pedido(
        db,
        usuario_id=e["usuario_id"],
        datos=datos_pedido(e),
    )

    assert primero["pedido"].id != segundo["pedido"].id
    assert primero["pedido"].codigo != segundo["pedido"].codigo
    assert contar(db, Pedido, e["empresa_id"]) == 2


# ==========================================================
# FASE 08-C.4 — PRUEBAS DE CONSULTA EMPRESARIAL
# ==========================================================


def test_consultar_pedido_con_detalles(db_testing):
    db = db_testing
    e = preparar_empresa(
        db,
        permisos=("pedidos.crear", "pedidos.ver"),
    )

    creado = crear_pedido(
        db,
        usuario_id=e["usuario_id"],
        datos=datos_pedido(e),
    )

    resultado = obtener_pedido(
        db,
        usuario_id=e["usuario_id"],
        pedido_id=creado["pedido"].id,
    )

    assert resultado["pedido"].id == creado["pedido"].id
    assert resultado["pedido"].empresa_id == e["empresa_id"]
    assert len(resultado["detalles"]) == 1
    assert (
        resultado["detalles"][0].producto_id
        == e["producto_id"]
    )


def test_listar_pedidos_con_filtros(db_testing):
    db = db_testing
    e = preparar_empresa(
        db,
        permisos=("pedidos.crear", "pedidos.ver"),
    )

    creado = crear_pedido(
        db,
        usuario_id=e["usuario_id"],
        datos=datos_pedido(e),
    )

    resultado = listar_pedidos(
        db,
        usuario_id=e["usuario_id"],
        pagina=1,
        limite=10,
        estado="BORRADOR",
        cliente_id=e["cliente_id"],
        busqueda=creado["pedido"].codigo,
    )

    assert resultado["total"] == 1
    assert resultado["pagina"] == 1
    assert resultado["limite"] == 10
    assert resultado["pedidos"][0].id == creado["pedido"].id


def test_consulta_requiere_permiso_ver(db_testing):
    db = db_testing
    e = preparar_empresa(
        db,
        permisos=("pedidos.crear",),
    )

    creado = crear_pedido(
        db,
        usuario_id=e["usuario_id"],
        datos=datos_pedido(e),
    )

    with pytest.raises(PedidoServiceError, match="autorizacion"):
        obtener_pedido(
            db,
            usuario_id=e["usuario_id"],
            pedido_id=creado["pedido"].id,
        )

    with pytest.raises(PedidoServiceError, match="autorizacion"):
        listar_pedidos(
            db,
            usuario_id=e["usuario_id"],
        )


def test_consulta_aislada_entre_empresas(db_testing):
    db = db_testing

    a = preparar_empresa(
        db,
        permisos=("pedidos.crear", "pedidos.ver"),
    )
    b = preparar_empresa(
        db,
        permisos=("pedidos.crear", "pedidos.ver"),
    )

    creado_b = crear_pedido(
        db,
        usuario_id=b["usuario_id"],
        datos=datos_pedido(b),
    )

    with pytest.raises(PedidoServiceError):
        obtener_pedido(
            db,
            usuario_id=a["usuario_id"],
            pedido_id=creado_b["pedido"].id,
        )

    listado_a = listar_pedidos(
        db,
        usuario_id=a["usuario_id"],
    )

    assert listado_a["total"] == 0
    assert listado_a["pedidos"] == []


@pytest.mark.parametrize(
    "filtros",
    [
        {"pagina": 0},
        {"limite": 101},
        {"estado": "INEXISTENTE"},
        {"cliente_id": -1},
        {"busqueda": "X" * 41},
    ],
)
def test_listado_rechaza_filtros_invalidos(
    db_testing,
    filtros,
):
    db = db_testing
    e = preparar_empresa(
        db,
        permisos=("pedidos.ver",),
    )

    with pytest.raises(PedidoServiceError):
        listar_pedidos(
            db,
            usuario_id=e["usuario_id"],
            **filtros,
        )

# ==========================================================
# FASE 08-C.5.3 — HISTORIAL TRIBUTARIO
# ==========================================================


def test_pedido_persiste_tasa_impuesto_historica(db_testing):
    db = db_testing
    e = preparar_empresa(db)

    resultado = crear_pedido(
        db,
        usuario_id=e["usuario_id"],
        datos=datos_pedido(e),
    )

    detalle_id = resultado["detalles"][0].id

    # Forzar una lectura posterior desde PostgreSQL,
    # en lugar de confiar en el objeto previamente cargado.
    db.expire_all()

    detalle = db.get(PedidoDetalle, detalle_id)

    assert detalle is not None
    assert detalle.tasa_impuesto == Decimal("18.0000")

    assert detalle.subtotal == Decimal("190.00")
    assert detalle.impuesto == Decimal("34.20")
    assert detalle.total == Decimal("224.20")


def test_pedido_conserva_tasa_tras_cambiar_configuracion(db_testing):
    db = db_testing
    e = preparar_empresa(db)

    resultado = crear_pedido(
        db,
        usuario_id=e["usuario_id"],
        datos=datos_pedido(e),
    )

    detalle_id = resultado["detalles"][0].id

    # Simulamos un cambio posterior en la configuracion
    # tributaria de la empresa de Testing.
    impuesto = db.get(Impuesto, e["impuesto_id"])
    impuesto.tasa = Decimal("10.0000")
    db.commit()

    db.expire_all()

    detalle = db.get(PedidoDetalle, detalle_id)

    # La tasa y los importes originales no deben cambiar.
    assert detalle.tasa_impuesto == Decimal("18.0000")
    assert detalle.subtotal == Decimal("190.00")
    assert detalle.impuesto == Decimal("34.20")
    assert detalle.total == Decimal("224.20")

    # La configuracion vigente ahora es distinta.
    impuesto = db.get(Impuesto, e["impuesto_id"])
    assert impuesto.tasa == Decimal("10.0000")


# ==========================================================
# FASE 08-C.7 — CONFIRMACION Y RESERVAS
# ==========================================================


def _escenario_confirmacion(db, *, permisos=None):
    if permisos is None:
        permisos = (
            "pedidos.crear",
            "pedidos.ver",
            "pedidos.confirmar",
        )

    e = preparar_empresa(db, permisos=permisos)

    inventario = Inventario(
        empresa_id=e["empresa_id"],
        producto_id=e["producto_id"],
        cantidad_disponible=Decimal("10.000"),
    )
    db.add(inventario)
    db.commit()

    e["inventario_id"] = inventario.id
    return e


def _crear_borrador_confirmacion(db, e, *, cantidad="2.000"):
    datos = datos_pedido(e)
    datos.detalles[0].cantidad = Decimal(cantidad)
    datos.detalles[0].descuento = Decimal("0.00")

    return crear_pedido(
        db,
        usuario_id=e["usuario_id"],
        datos=datos,
    )["pedido"]


def test_confirmacion_reserva_sin_descontar_fisico(db_testing):
    db = db_testing
    e = _escenario_confirmacion(db)
    pedido = _crear_borrador_confirmacion(db, e)

    confirmado = confirmar_pedido(
        db,
        usuario_id=e["usuario_id"],
        pedido_id=pedido.id,
    )

    assert confirmado.estado == "CONFIRMADO"

    reservas = db.scalars(
        select(ReservaStock).where(
            ReservaStock.empresa_id == e["empresa_id"],
            ReservaStock.pedido_id == pedido.id,
        )
    ).all()

    assert len(reservas) == 1
    assert reservas[0].estado == "ACTIVA"
    assert reservas[0].cantidad_reservada == Decimal("2.000")

    db.expire_all()
    inventario = db.get(Inventario, e["inventario_id"])
    assert inventario.cantidad_disponible == Decimal("10.000")

    assert contar(
        db, MovimientoInventario, e["empresa_id"]
    ) == 0


def test_confirmacion_registra_auditoria(db_testing):
    db = db_testing
    e = _escenario_confirmacion(db)
    pedido = _crear_borrador_confirmacion(db, e)

    confirmar_pedido(
        db,
        usuario_id=e["usuario_id"],
        pedido_id=pedido.id,
    )

    auditorias = db.scalars(
        select(Auditoria).where(
            Auditoria.empresa_id == e["empresa_id"],
            Auditoria.entidad == "pedidos",
            Auditoria.entidad_id == pedido.id,
            Auditoria.accion == "CONFIRMAR",
        )
    ).all()

    assert len(auditorias) == 1
    assert auditorias[0].datos_nuevos["estado"] == "CONFIRMADO"


def test_no_permite_confirmar_dos_veces(db_testing):
    db = db_testing
    e = _escenario_confirmacion(db)
    pedido = _crear_borrador_confirmacion(db, e)

    confirmar_pedido(
        db,
        usuario_id=e["usuario_id"],
        pedido_id=pedido.id,
    )

    with pytest.raises(PedidoServiceError):
        confirmar_pedido(
            db,
            usuario_id=e["usuario_id"],
            pedido_id=pedido.id,
        )

    assert contar(db, ReservaStock, e["empresa_id"]) == 1


def test_rechaza_stock_insuficiente(db_testing):
    db = db_testing
    e = _escenario_confirmacion(db)
    pedido = _crear_borrador_confirmacion(
        db, e, cantidad="11.000"
    )

    with pytest.raises(PedidoServiceError, match="Stock insuficiente"):
        confirmar_pedido(
            db,
            usuario_id=e["usuario_id"],
            pedido_id=pedido.id,
        )

    db.expire_all()
    assert db.get(Pedido, pedido.id).estado == "BORRADOR"
    assert contar(db, ReservaStock, e["empresa_id"]) == 0
    assert (
        db.get(Inventario, e["inventario_id"]).cantidad_disponible
        == Decimal("10.000")
    )


def test_reservas_previas_reducen_disponibilidad(db_testing):
    db = db_testing
    e = _escenario_confirmacion(db)

    primero = _crear_borrador_confirmacion(
        db, e, cantidad="7.000"
    )
    segundo = _crear_borrador_confirmacion(
        db, e, cantidad="4.000"
    )

    confirmar_pedido(
        db,
        usuario_id=e["usuario_id"],
        pedido_id=primero.id,
    )

    with pytest.raises(PedidoServiceError, match="Stock insuficiente"):
        confirmar_pedido(
            db,
            usuario_id=e["usuario_id"],
            pedido_id=segundo.id,
        )

    db.expire_all()

    assert db.get(Pedido, primero.id).estado == "CONFIRMADO"
    assert db.get(Pedido, segundo.id).estado == "BORRADOR"
    assert contar(db, ReservaStock, e["empresa_id"]) == 1


def test_cambio_de_impuesto_impide_confirmacion(db_testing):
    db = db_testing
    e = _escenario_confirmacion(db)
    pedido = _crear_borrador_confirmacion(db, e)

    impuesto = db.get(Impuesto, e["impuesto_id"])
    impuesto.tasa = Decimal("10.0000")
    db.commit()

    with pytest.raises(
        PedidoServiceError,
        match="configuracion tributaria",
    ):
        confirmar_pedido(
            db,
            usuario_id=e["usuario_id"],
            pedido_id=pedido.id,
        )

    assert contar(db, ReservaStock, e["empresa_id"]) == 0


def test_confirmacion_requiere_permiso(db_testing):
    db = db_testing
    e = _escenario_confirmacion(
        db,
        permisos=("pedidos.crear", "pedidos.ver"),
    )
    pedido = _crear_borrador_confirmacion(db, e)

    with pytest.raises(PedidoServiceError, match="autorizacion"):
        confirmar_pedido(
            db,
            usuario_id=e["usuario_id"],
            pedido_id=pedido.id,
        )

    assert contar(db, ReservaStock, e["empresa_id"]) == 0


def test_no_confirma_pedido_de_otra_empresa(db_testing):
    db = db_testing
    a = _escenario_confirmacion(db)
    b = _escenario_confirmacion(db)

    pedido_b = _crear_borrador_confirmacion(db, b)

    with pytest.raises(PedidoServiceError):
        confirmar_pedido(
            db,
            usuario_id=a["usuario_id"],
            pedido_id=pedido_b.id,
        )

    assert contar(db, ReservaStock, b["empresa_id"]) == 0


def test_producto_sin_control_stock_no_genera_reserva(db_testing):
    db = db_testing
    e = _escenario_confirmacion(db)

    producto = db.get(Producto, e["producto_id"])
    producto.controla_stock = False
    db.commit()

    pedido = _crear_borrador_confirmacion(db, e)

    resultado = confirmar_pedido(
        db,
        usuario_id=e["usuario_id"],
        pedido_id=pedido.id,
    )

    assert resultado.estado == "CONFIRMADO"
    assert contar(db, ReservaStock, e["empresa_id"]) == 0
    assert contar(db, MovimientoInventario, e["empresa_id"]) == 0
