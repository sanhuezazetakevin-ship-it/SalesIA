"""Ventas históricas sintéticas para el dashboard de NovaTech (solo Supabase TESTING).

Desde backend, con DATABASE_URL apuntando a TESTING:
  python seed_novatech_ventas_historicas.py --empresa-id 1234 --ventas 2000
  python seed_novatech_ventas_historicas.py --empresa-id 1234 --ventas 2000 --apply

Requiere productos NVM-P-* y clientes NVM del seed masivo y un usuario activo NovaTech.
No modifica stock ni crea pedidos/entregas; NO simula el proceso operativo completo.
"""
import argparse
import calendar
import random
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select, insert
from app.database.connection import SessionLocal, engine
from app.models.empresa import Empresa
from app.models.producto import Producto
from app.models.cliente import Cliente
from app.models.usuario import Usuario
from app.models.venta import Venta
from app.models.venta_detalle import VentaDetalle
from app.models.pago import Pago
from sqlalchemy.exc import OperationalError, DBAPIError
import time

PROJECT = 'dotqtobseniupdycsohb'
START = datetime(2026, 1, 1, tzinfo=timezone.utc)
END = datetime(2026, 10, 14, 23, 59, 59, tzinfo=timezone.utc)
PER_MONTH = [0.68, 0.76, 0.93, 0.86, 1.12, 1.03, 1.22, 1.15, 1.40, 1.16]
METHODS = ['EFECTIVO', 'TARJETA', 'TRANSFERENCIA', 'YAPE', 'PLIN']
PREFIX = 'NVH26-'


def cash(x):
    return Decimal(str(x)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--empresa-id', required=True, type=int)
    parser.add_argument('--ventas', type=int, default=2000)
    parser.add_argument('--seed', type=int, default=20261014)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--lote', type=int, default=20, help='Ventas por transacción (1 a 50)')
    args = parser.parse_args()
    if not 1 <= args.lote <= 50:
        parser.error('--lote debe estar entre 1 y 50')
    if args.empresa_id == 3170 or args.empresa_id < 1:
        parser.error('No se permite SalesIA Testing ni IDs inválidos')
    if not 100 <= args.ventas <= 10000:
        parser.error('--ventas debe estar entre 100 y 10000')
    project = (engine.url.username or '').split('.')[-1]
    if project != PROJECT:
        raise SystemExit(f'BLOQUEADO: requiere Supabase TESTING {PROJECT}; conexión actual: {project}')
    rng = random.Random(args.seed)
    with SessionLocal() as db:
        db.expire_on_commit = False
        company = db.get(Empresa, args.empresa_id)
        if not company or not company.activo or 'novatech' not in company.razon_social.lower().replace(' ', ''):
            raise SystemExit('BLOQUEADO: empresa destino no es NovaTech activa')
        products = list(db.scalars(select(Producto).where(Producto.empresa_id == company.id, Producto.sku.like('NVM-P-%'), Producto.activo.is_(True))))
        customers = list(db.scalars(select(Cliente).where(Cliente.empresa_id == company.id, Cliente.email.like('nvm.cliente%@example.com'), Cliente.activo.is_(True))))
        users = list(db.scalars(select(Usuario).where(Usuario.empresa_id == company.id, Usuario.activo.is_(True))))
        if len(products) < 25 or len(customers) < 10 or not users:
            raise SystemExit(f'Faltan datos NovaTech: productos={len(products)} (mín.25), clientes={len(customers)} (mín.10), usuarios activos={len(users)} (mín.1). Ejecuta antes el seed masivo y valida el administrador de NovaTech.')
        existing = set(db.scalars(select(Venta.codigo).where(Venta.empresa_id == company.id, Venta.codigo.like(PREFIX + '%'))))
        weights = [int(1000 * w) for w in PER_MONTH]
        dates = []
        for _ in range(args.ventas):
            month = rng.choices(range(1, 11), weights=weights, k=1)[0]
            day_max = 14 if month == 10 else calendar.monthrange(2026, month)[1]
            day = rng.randint(1, day_max)
            hour = rng.choices(range(9, 22), weights=[1,2,3,5,6,6,5,4,4,4,3,2,1], k=1)[0]
            dates.append(datetime(2026, month, day, hour, rng.randint(0, 59), rng.randint(0, 59), tzinfo=timezone.utc))
        dates.sort()
        pending = [(i, date) for i, date in enumerate(dates, 1) if f'{PREFIX}{i:06d}' not in existing]
        print(f'Proyecto: {project} | Empresa: {company.id} {company.razon_social}')
        print(f'Periodo: {START.date()} a {END.date()} | Productos: {len(products)} | Clientes activos: {len(customers)}')
        print(f'Ventas objetivo: {args.ventas} | Ya existentes con prefijo: {args.ventas-len(pending)} | Nuevas: {len(pending)}')
        if not args.apply:
            print('SIMULACIÓN: no se escribieron registros. Agrega --apply para ejecutar.')
            return
        totals = {'ventas': 0, 'detalles': 0, 'pagos': 0}
        # Transacciones independientes: un lote fallido no borra los anteriores.
        # Reintentar el comando reanuda los códigos faltantes.
        try:
            for batch_start in range(0, len(pending), args.lote):
                batch = pending[batch_start:batch_start + args.lote]
                vrows, detail_map, pay_map = [], {}, {}
                for i, dt in batch:
                    code = f'{PREFIX}{i:06d}'
                    k = rng.choices([1,2,3,4], weights=[45,34,16,5], k=1)[0]
                    chosen = rng.sample(products, k)
                    lines = []
                    for product in chosen:
                        quantity = Decimal(rng.choices([1,2,3,4,5,8], weights=[47,25,14,7,5,2], k=1)[0])
                        unit = cash(product.precio_venta)
                        gross = cash(unit * quantity)
                        discount = cash(gross * Decimal(str(rng.choice([0,0,0,0.03,0.05,0.08,0.10]))))
                        total = gross - discount
                        lines.append({'empresa_id':company.id,'producto_id':product.id,'descripcion':product.nombre[:255],
                                      'cantidad':quantity,'precio_unitario':unit,'descuento':discount,
                                      'subtotal':total,'impuesto':Decimal('0.00'),'total':total,'tasa_impuesto':Decimal('0.0000')})
                    total_sale = sum((line['total'] for line in lines), Decimal('0.00'))
                    payment_type = rng.choices(['PAGADO','PARCIAL','PENDIENTE'],weights=[77,16,7],k=1)[0]
                    payments = []
                    if payment_type == 'PAGADO':
                        if rng.random() < 0.22 and total_sale > 2:
                            first = cash(total_sale * Decimal(str(rng.uniform(0.20,0.70))))
                            payments = [first, total_sale-first]
                        else:
                            payments = [total_sale]
                    elif payment_type == 'PARCIAL':
                        payments = [cash(total_sale * Decimal(str(rng.uniform(0.15,0.85))))]
                    detail_map[code] = lines
                    pay_map[code] = (payments, dt, users[0].id)
                    vrows.append({'empresa_id':company.id,'pedido_id':None,'cliente_id':rng.choice(customers).id,
                                  'usuario_id':rng.choice(users).id,'codigo':code,'estado':'CONFIRMADA',
                                  'estado_pago':payment_type,'subtotal':total_sale,'impuesto_total':Decimal('0.00'),
                                  'total':total_sale,'observaciones':'HISTÓRICO SINTÉTICO NOVATECH - DEMOSTRACIÓN; no operacional',
                                  'created_at':dt})
                inserted = db.execute(insert(Venta).returning(Venta.id, Venta.codigo), vrows).all()
                drows, prows = [], []
                for venta_id, code in inserted:
                    for row in detail_map[code]:
                        drows.append({'venta_id':venta_id, **row})
                    amounts, dt, registrar = pay_map[code]
                    for j, amount in enumerate(amounts, 1):
                        prows.append({'empresa_id': company.id,'venta_id':venta_id,'registrado_por_id':registrar,
                                      'codigo':f'NVHP-{code.removeprefix(PREFIX)}-{j}',
                                      'monto':amount,'medio_pago':rng.choice(METHODS),'estado':'REGISTRADO',
                                      'observaciones':'PAGO SINTÉTICO PARA DASHBOARD - DEMOSTRACIÓN',
                                      'created_at':min(dt + timedelta(days=rng.randint(0, 3)), END)})
                if drows:
                    db.execute(insert(VentaDetalle), drows)
                if prows:
                    db.execute(insert(Pago), prows)
                totals['ventas'] += len(inserted)
                totals['detalles'] += len(drows)
                totals['pagos'] += len(prows)
                db.commit()
                print(f"CONFIRMADAS {totals['ventas']} ventas / {totals['detalles']} líneas / {totals['pagos']} pagos", flush=True)
            
        except Exception:
            db.rollback()
            print('Carga interrumpida. Los lotes previamente confirmados se conservan.')
            print('Puedes ejecutar el MISMO comando para continuar sin duplicar ventas.')
            raise
        print('CARGA COMPLETADA:', totals)
        print('ATENCIÓN: ventas históricas sintéticas; no se generaron movimientos de inventario, pedidos ni entregas.')

if __name__ == '__main__':
    main()
