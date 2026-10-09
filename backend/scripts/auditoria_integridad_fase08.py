"""SalesIA Enterprise - FASE 08-G.2. Auditoria de integridad (solo lectura).

Ejecutar desde backend:
    python -m scripts.auditoria_integridad_fase08

Solo se conecta a TEST_DATABASE_URL tras verificar aislamiento Supabase.
No aplica migraciones ni modifica registros.
"""

from sqlalchemy import create_engine, text
from app.core.config import settings
from scripts.verificar_aislamiento_real import obtener_referencia_supabase


CONSULTAS = {
    "Inventarios negativos": """
        SELECT COUNT(*) FROM inventario WHERE cantidad_disponible < 0
    """,
    "Pagos invalidos": """
        SELECT COUNT(*) FROM pagos
        WHERE monto <= 0 OR estado NOT IN ('REGISTRADO', 'ANULADO')
    """,
    "Entregas duplicadas": """
        SELECT COUNT(*) FROM (
          SELECT empresa_id, venta_id FROM entregas
          GROUP BY empresa_id, venta_id HAVING COUNT(*) > 1
        ) d
    """,
    "Reservas superiores al stock": """
        SELECT COUNT(*) FROM (
          SELECT i.id, i.empresa_id, i.cantidad_disponible,
                 COALESCE(SUM(r.cantidad_reservada)
                   FILTER (WHERE r.estado='ACTIVA'), 0) reservado
          FROM inventario i
          LEFT JOIN reservas_stock r
            ON r.inventario_id=i.id AND r.empresa_id=i.empresa_id
          GROUP BY i.id, i.empresa_id, i.cantidad_disponible
        ) q WHERE reservado > cantidad_disponible
    """,
    "Pagos superiores al total de venta": """
        SELECT COUNT(*) FROM (
          SELECT v.id, v.empresa_id, v.total,
                 COALESCE(SUM(p.monto) FILTER (WHERE p.estado='REGISTRADO'), 0) abonado
          FROM ventas v LEFT JOIN pagos p
            ON p.venta_id=v.id AND p.empresa_id=v.empresa_id
          GROUP BY v.id, v.empresa_id, v.total
        ) q WHERE abonado > total
    """,
    "Estados de pago inconsistentes": """
        SELECT COUNT(*) FROM (
          SELECT v.id, v.empresa_id, v.total, v.estado_pago,
                 COALESCE(SUM(p.monto) FILTER (WHERE p.estado='REGISTRADO'), 0) abonado
          FROM ventas v LEFT JOIN pagos p
            ON p.venta_id=v.id AND p.empresa_id=v.empresa_id
          GROUP BY v.id, v.empresa_id, v.total, v.estado_pago
        ) q WHERE estado_pago IS DISTINCT FROM CASE
          WHEN abonado=total THEN 'PAGADO'
          WHEN abonado>0 THEN 'PARCIAL'
          ELSE 'PENDIENTE' END
    """,
    "Reservas consumidas sin entrega confirmada": """
        SELECT COUNT(*) FROM reservas_stock r
        WHERE r.estado='CONSUMIDA' AND NOT EXISTS (
          SELECT 1 FROM ventas v JOIN entregas e
            ON e.venta_id=v.id AND e.empresa_id=v.empresa_id
          WHERE v.pedido_id=r.pedido_id AND v.empresa_id=r.empresa_id
            AND e.estado='CONFIRMADA'
        )
    """,
    "Reservas activas de entregas confirmadas": """
        SELECT COUNT(*) FROM reservas_stock r
        JOIN ventas v ON v.pedido_id=r.pedido_id AND v.empresa_id=r.empresa_id
        JOIN entregas e ON e.venta_id=v.id AND e.empresa_id=v.empresa_id
        WHERE e.estado='CONFIRMADA' AND r.estado='ACTIVA'
    """,
    "Movimientos de salida invalidos": """
        SELECT COUNT(*) FROM movimientos_inventario m
        WHERE m.tipo_movimiento='SALIDA'
          AND (m.cantidad_delta >= 0 OR m.entrega_id IS NULL OR NOT EXISTS (
            SELECT 1 FROM entregas e
            WHERE e.id=m.entrega_id AND e.empresa_id=m.empresa_id
              AND e.estado='CONFIRMADA'))
    """,
    "Cantidades entregadas distintas de salidas": """
        SELECT COUNT(*) FROM (
          SELECT e.id, vd.producto_id, vd.cantidad,
            COALESCE((SELECT SUM(-m.cantidad_delta)
              FROM movimientos_inventario m
              WHERE m.entrega_id=e.id AND m.empresa_id=e.empresa_id
                AND m.producto_id=vd.producto_id AND m.tipo_movimiento='SALIDA'), 0) salida
          FROM entregas e
          JOIN venta_detalles vd ON vd.venta_id=e.venta_id AND vd.empresa_id=e.empresa_id
          JOIN productos p ON p.id=vd.producto_id AND p.empresa_id=vd.empresa_id
          WHERE e.estado='CONFIRMADA' AND p.controla_stock=TRUE
        ) q WHERE salida <> cantidad
    """,
    "Entregas confirmadas sin auditoria": """
        SELECT COUNT(*) FROM entregas e
        WHERE e.estado='CONFIRMADA' AND NOT EXISTS (
          SELECT 1 FROM auditoria a
          WHERE a.empresa_id=e.empresa_id AND a.entidad='entregas'
            AND a.entidad_id=e.id AND a.accion='CONFIRMAR')
    """,
}


def main():
    print('=' * 52)
    print('SALESIA ENTERPRISE - FASE 08-G.2')
    print('AUDITORIA INTEGRAL DE INTEGRIDAD (SOLO LECTURA)')
    print('=' * 52)
    principal_url = settings.DATABASE_URL
    testing_url = settings.TEST_DATABASE_URL
    principal = obtener_referencia_supabase(principal_url) if principal_url else None
    testing = obtener_referencia_supabase(testing_url) if testing_url else None
    if not principal or not testing or principal == testing:
        raise RuntimeError('SEGURIDAD: aislamiento Supabase no verificado; auditoria cancelada.')
    print('Aislamiento Supabase: OK')
    print('Base principal: BLOQUEADA')
    engine = create_engine(testing_url, pool_pre_ping=True)
    resultados = {}
    try:
        with engine.connect() as db:
            with db.begin():
                db.execute(text('SET TRANSACTION READ ONLY'))
                print('\nRESULTADOS')
                print('-' * 52)
                for nombre, sql in CONSULTAS.items():
                    numero = db.execute(text(sql)).scalar_one()
                    resultados[nombre] = numero
                    print(f'{nombre}: {numero}')
    finally:
        engine.dispose()
    print('-' * 52)
    total = sum(resultados.values())
    print(f'Consultas ejecutadas: {len(resultados)}')
    print(f'Inconsistencias detectadas: {total}')
    print('AUDITORIA: APROBADA' if total == 0 else 'AUDITORIA: REVISAR INCONSISTENCIAS')


if __name__ == '__main__':
    main()
