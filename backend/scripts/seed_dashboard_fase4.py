"""Carga reproducible para dashboard SalesIA; ejecutar EXCLUSIVAMENTE en TEST_DATABASE_URL.

No crea usuarios ni modifica registros existentes; no ejecuta en producción.
"""
import argparse
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, select, func
from sqlalchemy.engine import make_url
from scripts.verificar_aislamiento_real import obtener_referencia_supabase, ErrorAislamiento
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.cliente import Cliente
from app.models.categoria import Categoria
from app.models.producto import Producto
from app.models.inventario import Inventario
from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle
from app.models.venta import Venta
from app.models.venta_detalle import VentaDetalle
from app.models.pago import Pago

MARK = 'F4DEMO26'
CENTS = Decimal('0.01')


def money(x):
    return Decimal(str(x)).quantize(CENTS)


def main():
    parser = argparse.ArgumentParser(description='Seed de dashboard para BD de PRUEBAS aislada')
    parser.add_argument('--empresa-id', type=int, required=True)
    parser.add_argument('--usuario-id', type=int, required=True, help='Usuario existente de esa empresa')
    parser.add_argument('--aplicar', action='store_true', help='Sin esta opción solo verifica el destino')
    args = parser.parse_args()
    load_dotenv(Path(__file__).resolve().parents[1] / '.env')
    test_url = os.getenv('TEST_DATABASE_URL', '').strip()
    main_url = os.getenv('DATABASE_URL', '').strip()
    if not test_url or not main_url:
        raise SystemExit('ERROR: define TEST_DATABASE_URL y DATABASE_URL. Sin cambios.')
    test_parsed, main_parsed = make_url(test_url), make_url(main_url)
    if test_parsed.get_backend_name() != 'postgresql':
        raise SystemExit('ERROR: únicamente se admite PostgreSQL de pruebas.')
    # El pooler de Supabase puede usar un mismo host y base `postgres` para
    # varios proyectos. El identificador fiable es la referencia Supabase.
    try:
        referencia_principal = obtener_referencia_supabase(main_url)
        referencia_testing = obtener_referencia_supabase(test_url)
    except ErrorAislamiento as exc:
        raise SystemExit(f'ERROR: no se pudo verificar el aislamiento Supabase: {exc}. Sin cambios.') from exc
    if referencia_principal == referencia_testing:
        raise SystemExit('ERROR: ambas URLs corresponden al mismo proyecto Supabase. Sin cambios.')
    print('[OK] Proyectos Supabase diferentes (identificados por referencia).')
    if os.getenv('SALESIA_ALLOW_DEMO_SEED', '') != 'YES':
        raise SystemExit('ERROR: define SALESIA_ALLOW_DEMO_SEED=YES para habilitar la carga de pruebas.')
    engine = create_engine(test_url, pool_pre_ping=True)
    try:
        with Session(engine) as db:
            empresa = db.get(Empresa, args.empresa_id)
            usuario = db.get(Usuario, args.usuario_id)
            if not empresa or not empresa.activo:
                raise SystemExit('ERROR: empresa inexistente o inactiva en TEST_DATABASE_URL.')
            if not usuario or usuario.empresa_id != args.empresa_id or not usuario.activo:
                raise SystemExit('ERROR: usuario inexistente, inactivo o pertenece a otra empresa.')
            existe = db.scalar(select(func.count()).select_from(Venta).where(
                Venta.empresa_id == args.empresa_id, Venta.codigo.like(f'{MARK}-%')))
            print(f'Destino verificado: empresa={empresa.id}, usuario={usuario.id}; ventas demo existentes={existe}.')
            if not args.aplicar:
                print('SIMULACION: no se insertó nada. Añade --aplicar para ejecutar.')
                return
            if existe:
                print('Carga ya aplicada: no se crean registros duplicados.')
                return
            # Asegurar que no existe un intento parcial identificado por el prefijo.
            for model, field in ((Producto, Producto.sku), (Pedido, Pedido.codigo), (Pago, Pago.codigo)):
                if db.scalar(select(func.count()).select_from(model).where(model.empresa_id == args.empresa_id, field.like(f'{MARK}-%'))):
                    raise SystemExit('ERROR: existen datos demo parciales; revisa antes de volver a ejecutar.')
            eid, uid = empresa.id, usuario.id
            categorias = []
            for i, nombre in enumerate(['Computadoras', 'Monitores', 'Periféricos', 'Redes', 'Almacenamiento', 'Accesorios', 'Impresión', 'Oficina'], 1):
                cat = db.scalar(select(Categoria).where(Categoria.empresa_id == eid, Categoria.nombre == f'Demo F4 {nombre}'))
                if not cat:
                    cat = Categoria(empresa_id=eid, nombre=f'Demo F4 {nombre}', activo=True)
                    db.add(cat)
                    db.flush()
                categorias.append(cat)
            clientes = []
            for i in range(1, 51):
                nro = f'{77000000+i:08d}'
                cli = db.scalar(select(Cliente).where(Cliente.empresa_id == eid, Cliente.tipo_documento == 'DNI', Cliente.numero_documento == nro))
                if cli is None:
                    cli = Cliente(empresa_id=eid, nombre=f'Cliente Demostración F4 {i:03d}', tipo_documento='DNI',
                                  numero_documento=nro, email=f'cliente-f4-{i:03d}@example.invalid', activo=True)
                    db.add(cli)
                    db.flush()
                clientes.append(cli)
            productos = []
            for i in range(1, 41):
                precio = money(60 + i * 19 + (i % 4) * 14)
                prod = Producto(empresa_id=eid, categoria_id=categorias[(i - 1) % 8].id,
                                sku=f'{MARK}-SKU-{i:03d}', nombre=f'Producto demostración F4 {i:03d}',
                                descripcion='Solo datos de ejemplo para validar dashboard', tipo_item='PRODUCTO',
                                precio_venta=precio, costo_referencia=money(precio * Decimal('0.7')),
                                controla_stock=True, activo=True)
                db.add(prod)
                db.flush()
                db.add(Inventario(empresa_id=eid, producto_id=prod.id, cantidad_disponible=Decimal(1000)))
                productos.append(prod)
            hoy = datetime.now(timezone.utc).date()
            inicio = hoy - timedelta(days=175)
            pedidos = []
            for i in range(1, 101):
                prod = productos[(i * 7) % len(productos)]
                cli = clientes[(i * 3) % len(clientes)]
                cantidad = Decimal(1 + i % 4)
                total = money(prod.precio_venta * cantidad)
                fecha = datetime.combine(inicio + timedelta(days=(i * 173 // 100)), datetime.min.time(), timezone.utc) + timedelta(hours=9 + i % 9)
                estado = ['BORRADOR', 'CONFIRMADO', 'COMPLETADO', 'CANCELADO'][i % 4]
                pedido = Pedido(empresa_id=eid, cliente_id=cli.id, usuario_id=uid, codigo=f'{MARK}-PED-{i:04d}',
                                estado=estado, subtotal=total, impuesto_total=Decimal(0), total=total,
                                observaciones='Datos sintéticos de validación Fase 4', created_at=fecha)
                db.add(pedido)
                db.flush()
                db.add(PedidoDetalle(empresa_id=eid, pedido_id=pedido.id, producto_id=prod.id,
                                     descripcion=prod.nombre, cantidad=cantidad, precio_unitario=prod.precio_venta,
                                     descuento=Decimal(0), subtotal=total, impuesto=Decimal(0), total=total))
                pedidos.append((pedido, prod, cli, cantidad, total, fecha))
            pagos_count = 0
            for i, (pedido, prod, cli, cantidad, total, fecha) in enumerate(pedidos[:75], 1):
                # Ventas directas de demostración: no afectan las reservas ni el inventario operativo.
                estado_pago = ['PENDIENTE', 'PARCIAL', 'PAGADO'][i % 3]
                v = Venta(empresa_id=eid, usuario_id=uid, cliente_id=cli.id, pedido_id=None,
                          codigo=f'{MARK}-VEN-{i:04d}', estado='CONFIRMADA', estado_pago=estado_pago,
                          subtotal=total, impuesto_total=Decimal(0), total=total,
                          observaciones='Venta sintética F4 sin movimientos de stock', created_at=fecha)
                db.add(v)
                db.flush()
                db.add(VentaDetalle(empresa_id=eid, venta_id=v.id, producto_id=prod.id,
                                    descripcion=prod.nombre, cantidad=cantidad, precio_unitario=prod.precio_venta,
                                    descuento=Decimal(0), subtotal=total, impuesto=Decimal(0), total=total))
                if estado_pago != 'PENDIENTE':
                    montos = [total] if estado_pago == 'PAGADO' else [money(total / 2)]
                    for j, monto in enumerate(montos, 1):
                        db.add(Pago(empresa_id=eid, venta_id=v.id, registrado_por_id=uid,
                                    codigo=f'{MARK}-PAG-{i:04d}-{j}', monto=monto,
                                    medio_pago=['EFECTIVO', 'YAPE', 'TRANSFERENCIA'][i % 3],
                                    estado='REGISTRADO', created_at=fecha + timedelta(hours=j)))
                        pagos_count += 1
            db.commit()
            print(f'OK: 8 categorías, 50 clientes, 40 productos e inventarios, 100 pedidos, 75 ventas, {pagos_count} pagos.')
            print(f'Rango: {inicio.isoformat()} a {hoy.isoformat()} (UTC). Filtra el dashboard dentro de ese rango.')
            print('NOTA: no se crearon entregas ni movimientos físicos; ventas directas sintéticas para analítica.')
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
