# MVP-01-D — Variables estadísticas y distribuciones

## Instalación
Copiar `app/` y `tests/` del ZIP dentro de `backend/`. No elimina ni reemplaza la ruta `/api/analytics/resumen`.

Abrir `app/main.py` e incluir **una sola vez**:

```python
from app.api.routes.analytics_distribuciones import router as analytics_distribuciones_router
```

Junto a los routers existentes agregar:

```python
app.include_router(analytics_distribuciones_router)
```

## Pruebas

```cmd
python -m pytest tests/test_analytics_distribuciones_calculos.py -v --tb=short
python -m pytest tests/test_analytics_calculos.py tests/test_analytics_resumen_integracion.py tests/test_analytics_distribuciones_calculos.py -q
```

## API
GET `/api/analytics/distribuciones?fecha_inicio=2026-10-01&fecha_fin=2026-10-31&variable=importe_venta&intervalos=5`

`variable=estado_pago` devuelve categorías PENDIENTE, PARCIAL, PAGADO en ventas CONFIRMADAS. La categoría de pago NO representa un cobro contabilizado.

Datos UTC, periodo inclusivo, solo ventas CONFIRMADAS, permiso `ventas.ver` y empresa autenticada, límite 50000 ventas y periodo <=367 días. La clasificación *cuantitativa continua* se usa para importes monetarios (escala monetaria discreta al céntimo en almacenamiento).

**Nota**: estas son nueve pruebas unitarias. El bloque se considerará cerrado tras agregar y superar pruebas HTTP/Testing de aislamiento, JWT y exactitud de distribución.

No se ejecutan migraciones ni se requieren claves Supabase en este paquete.
