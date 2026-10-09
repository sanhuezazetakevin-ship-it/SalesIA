"""SalesIA FASE 09-F.2-B — auditoría SQL solo lectura (exclusivamente TESTING).

Ejecución: python -m scripts.auditoria_integridad_compras_testing
No usa SessionLocal ni engine de la aplicación; no modifica datos.
"""
from __future__ import annotations

import sys
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.core.config import settings
from scripts.verificar_aislamiento_real import obtener_referencia_supabase


class AuditoriaError(RuntimeError):
    pass


# Cada consulta devuelve exactamente una fila con el recuento de infracciones.
# Todas operan sobre tablas del esquema 008; sin modificaciones DDL/DML.
CHECKS = [
    ('01 proveedor inexistente o de otra empresa', '''
        SELECT count(*) FROM ordenes_compra o
        LEFT JOIN proveedores p ON p.id=o.proveedor_id AND p.empresa_id=o.empresa_id
        WHERE p.id IS NULL
    '''),
    ('02 detalle de compra sin orden/producto válido', '''
        SELECT count(*) FROM orden_compra_detalles d
        LEFT JOIN ordenes_compra o ON o.id=d.orden_id AND o.empresa_id=d.empresa_id
        LEFT JOIN productos p ON p.id=d.producto_id AND p.empresa_id=d.empresa_id
        WHERE o.id IS NULL OR p.id IS NULL
    '''),
    ('03 cantidad o importe inválido en detalle de compra', '''
        SELECT count(*) FROM orden_compra_detalles d
        WHERE d.cantidad_solicitada <= 0 OR d.precio_unitario < 0
          OR d.subtotal < 0 OR d.total < 0 OR d.impuesto < 0
    '''),
    ('04 total de orden distinto de subtotal + impuesto', '''
        SELECT count(*) FROM ordenes_compra o
        WHERE o.subtotal < 0 OR o.impuesto_total < 0 OR o.total < 0
           OR o.total <> o.subtotal + o.impuesto_total
    '''),
    ('05 detalle de recepción sin orden/línea válida', '''
        SELECT count(*) FROM recepcion_compra_detalles d
        LEFT JOIN recepciones_compra r
          ON r.id=d.recepcion_id AND r.orden_id=d.orden_id AND r.empresa_id=d.empresa_id
        LEFT JOIN orden_compra_detalles oc
          ON oc.id=d.orden_detalle_id AND oc.orden_id=d.orden_id AND oc.empresa_id=d.empresa_id
        WHERE r.id IS NULL OR oc.id IS NULL OR d.cantidad_recibida <= 0
    '''),
    ('06 sobrerrecepción acumulada por línea', '''
        SELECT count(*) FROM (
          SELECT d.id
          FROM orden_compra_detalles d
          LEFT JOIN recepcion_compra_detalles r
            ON r.orden_detalle_id=d.id AND r.orden_id=d.orden_id AND r.empresa_id=d.empresa_id
          GROUP BY d.id,d.cantidad_solicitada
          HAVING COALESCE(sum(r.cantidad_recibida),0) > d.cantidad_solicitada
        ) x
    '''),
    ('07 recepción sin orden correspondiente', '''
        SELECT count(*) FROM recepciones_compra r
        LEFT JOIN ordenes_compra o ON o.id=r.orden_id AND o.empresa_id=r.empresa_id
        WHERE o.id IS NULL
    '''),
    ('08 pago sin orden correspondiente o monto inválido', '''
        SELECT count(*) FROM pagos_proveedores p
        LEFT JOIN ordenes_compra o ON o.id=p.orden_id AND o.empresa_id=p.empresa_id
        WHERE o.id IS NULL OR p.monto <= 0
    '''),
    ('09 sobrepago acumulado de pagos registrados', '''
        SELECT count(*) FROM (
          SELECT o.id
          FROM ordenes_compra o LEFT JOIN pagos_proveedores p
            ON p.orden_id=o.id AND p.empresa_id=o.empresa_id AND p.estado='REGISTRADO'
          GROUP BY o.id,o.total
          HAVING COALESCE(sum(p.monto),0) > o.total
        ) x
    '''),
    ('10 estado de pago no coincide con pagos registrados', '''
        SELECT count(*) FROM (
          SELECT o.id,o.estado_pago,o.total,COALESCE(sum(p.monto),0) pagado
          FROM ordenes_compra o LEFT JOIN pagos_proveedores p
            ON p.orden_id=o.id AND p.empresa_id=o.empresa_id AND p.estado='REGISTRADO'
          GROUP BY o.id,o.estado_pago,o.total
        ) x
        WHERE (pagado=0 AND estado_pago <> 'PENDIENTE')
           OR (pagado>0 AND pagado<total AND estado_pago <> 'PARCIAL')
           OR (pagado=total AND pagado>0 AND estado_pago <> 'PAGADO')
           OR (pagado>total)
    '''),
    ('11 estado de recepción no coincide con cantidades', '''
        WITH pendientes AS (
          SELECT o.id,o.estado,
            count(d.id) AS lineas,
            count(d.id) FILTER (WHERE COALESCE(r.recibido,0)=d.cantidad_solicitada) AS completas,
            COALESCE(sum(COALESCE(r.recibido,0)),0) AS recibido
          FROM ordenes_compra o
          LEFT JOIN orden_compra_detalles d ON d.orden_id=o.id AND d.empresa_id=o.empresa_id
          LEFT JOIN (
            SELECT orden_detalle_id,empresa_id,orden_id,sum(cantidad_recibida) recibido
            FROM recepcion_compra_detalles GROUP BY orden_detalle_id,empresa_id,orden_id
          ) r ON r.orden_detalle_id=d.id AND r.orden_id=d.orden_id AND r.empresa_id=d.empresa_id
          GROUP BY o.id,o.estado
        )
        SELECT count(*) FROM pendientes
        WHERE (recibido>0 AND completas=lineas AND estado <> 'RECIBIDA')
           OR (recibido>0 AND completas<lineas AND estado <> 'PARCIALMENTE_RECIBIDA')
           OR (recibido=0 AND estado IN ('RECIBIDA','PARCIALMENTE_RECIBIDA'))
    '''),
    ('12 movimiento ligado a recepción inexistente o de otra empresa', '''
        SELECT count(*) FROM movimientos_inventario m
        LEFT JOIN recepciones_compra r
          ON r.id=m.recepcion_compra_id AND r.empresa_id=m.empresa_id
        WHERE m.recepcion_compra_id IS NOT NULL AND r.id IS NULL
    '''),
    ('13 movimientos recepción no corresponden al detalle con stock', '''
        WITH previsto AS (
          SELECT r.id AS recepcion_id,r.empresa_id,d.producto_id,
                 sum(rd.cantidad_recibida) AS cantidad
          FROM recepciones_compra r
          JOIN recepcion_compra_detalles rd ON rd.recepcion_id=r.id AND rd.empresa_id=r.empresa_id
          JOIN orden_compra_detalles d ON d.id=rd.orden_detalle_id AND d.empresa_id=rd.empresa_id
          WHERE d.controla_stock_snapshot IS TRUE
          GROUP BY r.id,r.empresa_id,d.producto_id
        ), real AS (
          SELECT m.recepcion_compra_id AS recepcion_id,m.empresa_id,m.producto_id,
                 sum(m.cantidad_delta) AS cantidad,
                 count(*) AS registros,
                 bool_and(m.tipo_movimiento='ENTRADA' AND m.motivo='RECEPCION_COMPRA') AS valido
          FROM movimientos_inventario m WHERE m.recepcion_compra_id IS NOT NULL
          GROUP BY m.recepcion_compra_id,m.empresa_id,m.producto_id
        )
        SELECT count(*) FROM previsto p FULL JOIN real r
          ON r.recepcion_id=p.recepcion_id AND r.empresa_id=p.empresa_id AND r.producto_id=p.producto_id
        WHERE p.recepcion_id IS NULL OR r.recepcion_id IS NULL
           OR r.cantidad<>p.cantidad OR r.registros<>1 OR r.valido IS NOT TRUE
    '''),
]

REQUIRED = {
    'ordenes_compra': {'id','empresa_id','proveedor_id','subtotal','impuesto_total','total','estado','estado_pago'},
    'orden_compra_detalles': {'id','empresa_id','orden_id','producto_id','cantidad_solicitada','precio_unitario','subtotal','total','impuesto','controla_stock_snapshot'},
    'proveedores': {'id','empresa_id'}, 'productos': {'id','empresa_id'},
    'recepciones_compra': {'id','empresa_id','orden_id'},
    'recepcion_compra_detalles': {'id','empresa_id','orden_id','recepcion_id','orden_detalle_id','cantidad_recibida'},
    'pagos_proveedores': {'id','empresa_id','orden_id','monto','estado'},
    'movimientos_inventario': {'empresa_id','producto_id','recepcion_compra_id','cantidad_delta','tipo_movimiento','motivo'},
}


def main() -> int:
    print('=== SALESIA 09-F.2-B | AUDITORIA SOLO LECTURA | TESTING ===')
    if not settings.DATABASE_URL or not settings.TEST_DATABASE_URL:
        raise AuditoriaError('Faltan DATABASE_URL o TEST_DATABASE_URL.')
    principal = obtener_referencia_supabase(settings.DATABASE_URL)
    testing = obtener_referencia_supabase(settings.TEST_DATABASE_URL)
    if principal == testing:
        raise AuditoriaError('TESTING y PRINCIPAL son el mismo proyecto Supabase: BLOQUEADO.')
    url = make_url(settings.TEST_DATABASE_URL)
    if url.get_backend_name() != 'postgresql':
        raise AuditoriaError('TEST_DATABASE_URL debe usar PostgreSQL.')
    print('Aislamiento Supabase: OK | Base principal: BLOQUEADA')
    engine = create_engine(url, pool_pre_ping=True, connect_args={'connect_timeout': 10})
    errores = 0
    try:
        with engine.connect() as conn:
            # Modo lectura en la transacción, incluyendo las comprobaciones de metadatos.
            conn.execute(text('SET TRANSACTION READ ONLY'))
            conn.execute(text("SET LOCAL statement_timeout = '30000ms'"))
            ro = conn.scalar(text('SHOW transaction_read_only'))
            if ro != 'on':
                raise AuditoriaError('Transacción no quedó en modo READ ONLY.')
            version = conn.scalar(text('SELECT version_num FROM alembic_version'))
            if version != '746fcabdf249':
                raise AuditoriaError(f'Revisión Alembic inesperada: {version!r}.')
            rows = conn.execute(text('''
                SELECT table_name,column_name FROM information_schema.columns
                WHERE table_schema=current_schema()
            ''')).all()
            columnas = {}
            for tabla, columna in rows:
                columnas.setdefault(tabla, set()).add(columna)
            for tabla, necesarias in REQUIRED.items():
                faltantes = necesarias - columnas.get(tabla, set())
                if faltantes:
                    raise AuditoriaError(f'Estructura incompatible: {tabla}, faltan: {sorted(faltantes)}')
            print('Transacción: READ ONLY | Alembic: 746fcabdf249 (head)')
            print('Tablas y columnas requeridas: OK')
            print('--- VERIFICACIONES DE INTEGRIDAD ---')
            for nombre, consulta in CHECKS:
                numero = int(conn.scalar(text(consulta)))
                estado = 'OK' if numero == 0 else 'FALLO'
                print(f'{estado}: {nombre} | incidencias={numero}')
                errores += numero
            print(f'RESUMEN: {len(CHECKS)} comprobaciones, {errores} incidencias')
            # connection.close() provoca rollback de la transacción de lectura.
    finally:
        engine.dispose()
    if errores:
        print('RESULTADO: AUDITORIA CON INCIDENCIAS (sin cambios en la base)')
        return 1
    print('RESULTADO: AUDITORIA APROBADA (sin cambios en la base)')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print(f'RESULTADO: AUDITORIA NO COMPLETADA ({type(exc).__name__}: {exc})')
        sys.exit(1)
