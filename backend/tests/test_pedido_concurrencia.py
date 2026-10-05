"""SalesIA FASE 08-C.8: concurrencia real contra Supabase TESTING.

ADVERTENCIA: crea registros CONFIRMADOS temporalmente en TEST_DATABASE_URL.
No utiliza db_testing: dos conexiones independientes deben ver datos confirmados.
La limpieza usa exclusivamente identificadores de esta prueba, nunca DELETE global.
No ejecutar junto a otras pruebas en paralelo.
"""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.asociaciones import roles_permisos, usuarios_roles
from app.models.auditoria import Auditoria
from app.models.cliente import Cliente
from app.models.empresa import Empresa
from app.models.impuesto import Impuesto
from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario
from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle
from app.models.permiso import Permiso
from app.models.producto import Producto
from app.models.reserva_stock import ReservaStock
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.schemas.pedidos import PedidoCreate
from app.services.pedido_service import (
    PedidoServiceError,
    confirmar_pedido,
    crear_pedido,
)
from scripts.verificar_aislamiento_real import obtener_referencia_supabase


def _motor_testing():
    principal = obtener_referencia_supabase(settings.DATABASE_URL)
    testing = obtener_referencia_supabase(settings.TEST_DATABASE_URL)
    if not principal or not testing or principal == testing:
        pytest.fail("SEGURIDAD: no se ha comprobado el aislamiento Supabase")
    return create_engine(settings.TEST_DATABASE_URL, pool_pre_ping=True)


def _preparar(db, marca):
    """Una transaccion inicial; si falla, el caller hace rollback."""
    empresa = Empresa(
        razon_social=f"Concurrencia {marca[:12]}",
        ruc=str(uuid4().int % 10**11).zfill(11),
        moneda_base="PEN", activo=True,
    )
    db.add(empresa)
    db.flush()
    usuario = Usuario(
        empresa_id=empresa.id, nombre="Operador Concurrencia",
        email=f"concurrencia-{marca}@example.com",
        password_hash=hash_password("ConcurrenciaTesting#2026"), activo=True,
    )
    rol = Rol(
        empresa_id=empresa.id, nombre=f"CONC_{marca[:8]}",
        descripcion="Rol temporal de concurrencia",
    )
    db.add_all([usuario, rol])
    db.flush()
    db.execute(usuarios_roles.insert().values(
        usuario_id=usuario.id, rol_id=rol.id, empresa_id=empresa.id,
    ))
    permisos_creados = []
    for codigo in ("pedidos.crear", "pedidos.confirmar"):
        permiso = db.scalar(select(Permiso).where(Permiso.codigo == codigo))
        if permiso is None:
            permiso = Permiso(codigo=codigo, descripcion=f"Temporal {codigo}")
            db.add(permiso)
            db.flush()
            permisos_creados.append(permiso.id)
        db.execute(roles_permisos.insert().values(
            rol_id=rol.id, permiso_id=permiso.id,
        ))
    cliente = Cliente(
        empresa_id=empresa.id, nombre="Cliente concurrencia",
        tipo_documento="DNI", numero_documento=str(uuid4().int % 10**8).zfill(8),
        activo=True,
    )
    producto = Producto(
        empresa_id=empresa.id, categoria_id=None,
        sku=f"CONC-{marca[:12]}", nombre="Producto concurrente",
        descripcion="Stock compartido", tipo_item="PRODUCTO",
        precio_venta=Decimal("118.00"), costo_referencia=Decimal("70.00"),
        controla_stock=True, activo=True,
    )
    impuesto = Impuesto(
        empresa_id=empresa.id, codigo="IGV", nombre="IGV temporal",
        tasa=Decimal("18.0000"), incluido_en_precio=True, activo=True,
    )
    db.add_all([cliente, producto, impuesto])
    db.flush()
    inventario = Inventario(
        empresa_id=empresa.id, producto_id=producto.id,
        cantidad_disponible=Decimal("10.000"),
    )
    db.add(inventario)
    db.flush()
    return dict(
        empresa_id=empresa.id, usuario_id=usuario.id, rol_id=rol.id,
        cliente_id=cliente.id, producto_id=producto.id,
        inventario_id=inventario.id, permisos_creados=permisos_creados,
    )


def _crear_borrador(db, escenario, cantidad):
    datos = PedidoCreate.model_validate(dict(
        cliente_id=escenario["cliente_id"],
        detalles=[dict(
            producto_id=escenario["producto_id"],
            cantidad=str(cantidad), descuento="0.00",
        )],
    ))
    return crear_pedido(
        db, usuario_id=escenario["usuario_id"], datos=datos,
    )["pedido"].id


def _confirmar_en_sesion(engine, escenario, pedido_id, barrera):
    with Session(engine) as db:
        barrera.wait(timeout=20)
        try:
            confirmado = confirmar_pedido(
                db, usuario_id=escenario["usuario_id"], pedido_id=pedido_id,
            )
            return ("CONFIRMADO", confirmado.id)
        except PedidoServiceError as exc:
            return ("RECHAZADO", str(exc))


def _limpiar(engine, escenario):
    """Limpieza delimitada por empresa, rol y permisos creados por el test."""
    empresa_id = escenario["empresa_id"]
    rol_id = escenario["rol_id"]
    with Session(engine) as db:
        try:
            # Solo se eliminan filas asociadas a la empresa temporal.
            for modelo in (
                Auditoria, ReservaStock, PedidoDetalle, Pedido,
                MovimientoInventario, Inventario, Impuesto,
                Producto, Cliente,
            ):
                db.execute(delete(modelo).where(modelo.empresa_id == empresa_id))
            db.execute(delete(usuarios_roles).where(
                usuarios_roles.c.empresa_id == empresa_id
            ))
            db.execute(delete(roles_permisos).where(
                roles_permisos.c.rol_id == rol_id
            ))
            db.execute(delete(Rol).where(Rol.id == rol_id, Rol.empresa_id == empresa_id))
            db.execute(delete(Usuario).where(Usuario.id == escenario["usuario_id"], Usuario.empresa_id == empresa_id))
            db.execute(delete(Empresa).where(Empresa.id == empresa_id))
            for permiso_id in escenario["permisos_creados"]:
                # No eliminar un permiso compartido por otras pruebas/roles.
                if db.scalar(select(func.count()).select_from(roles_permisos).where(
                    roles_permisos.c.permiso_id == permiso_id
                )) == 0:
                    db.execute(delete(Permiso).where(Permiso.id == permiso_id))
            db.commit()
        except Exception:
            db.rollback()
            raise
    with Session(engine) as db:
        assert db.get(Empresa, empresa_id) is None, "Quedo la empresa temporal sin limpiar"
        assert db.scalar(select(func.count()).select_from(Pedido).where(
            Pedido.empresa_id == empresa_id
        )) == 0
        assert db.scalar(select(func.count()).select_from(ReservaStock).where(
            ReservaStock.empresa_id == empresa_id
        )) == 0


def test_dos_pedidos_simultaneos_no_sobrevenden():
    engine = _motor_testing()
    escenario = None
    try:
        marca = uuid4().hex
        with Session(engine) as db:
            try:
                escenario = _preparar(db, marca)
                db.commit()  # Necesario para visibilidad entre conexiones independientes.
            except Exception:
                db.rollback()
                raise
        with Session(engine) as db:
            pedido_a = _crear_borrador(db, escenario, "7.000")
            pedido_b = _crear_borrador(db, escenario, "6.000")

        barrera = Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            futuro_a = ejecutor.submit(
                _confirmar_en_sesion, engine, escenario, pedido_a, barrera,
            )
            futuro_b = ejecutor.submit(
                _confirmar_en_sesion, engine, escenario, pedido_b, barrera,
            )
            resultados = [futuro_a.result(timeout=60), futuro_b.result(timeout=60)]

        assert sorted(r[0] for r in resultados) == ["CONFIRMADO", "RECHAZADO"], resultados
        assert "Stock insuficiente" in next(r[1] for r in resultados if r[0] == "RECHAZADO")

        with Session(engine) as db:
            pedidos = db.scalars(select(Pedido).where(
                Pedido.id.in_((pedido_a, pedido_b)),
                Pedido.empresa_id == escenario["empresa_id"],
            )).all()
            assert sorted(p.estado for p in pedidos) == ["BORRADOR", "CONFIRMADO"]
            reservas = db.scalars(select(ReservaStock).where(
                ReservaStock.empresa_id == escenario["empresa_id"],
                ReservaStock.estado == "ACTIVA",
            )).all()
            assert len(reservas) == 1
            assert sum((r.cantidad_reservada for r in reservas), Decimal(0)) in (
                Decimal("6.000"), Decimal("7.000"),
            )
            assert sum((r.cantidad_reservada for r in reservas), Decimal(0)) <= Decimal("10.000")
            inventario = db.get(Inventario, escenario["inventario_id"])
            assert inventario.cantidad_disponible == Decimal("10.000")
            assert db.scalar(select(func.count()).select_from(MovimientoInventario).where(
                MovimientoInventario.empresa_id == escenario["empresa_id"],
            )) == 0
    finally:
        try:
            if escenario is not None:
                _limpiar(engine, escenario)
        finally:
            engine.dispose()
