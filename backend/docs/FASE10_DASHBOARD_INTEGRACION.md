# SalesIA Enterprise — FASE 10: Dashboard empresarial

## Entrega
Se amplía el backend existente, manteniendo intactos los endpoints Analytics de MVP-01 y el endpoint de series validado previamente. Se agregan KPIs, comparación de períodos, pedidos por estado, ranking de productos, clientes y usuarios vendedores. Las consultas son de solo lectura.

### Endpoints

**GET `/api/dashboard/ventas/serie`** (ya implementado y validado en la entrega anterior)

- Obligatorios: `fecha_inicio`, `fecha_fin` (`YYYY-MM-DD`).
- Opcional: `agrupacion=dia|mes` (predeterminado: `dia`).
- Resultado: `puntos[]` con `fecha`, `cantidad_ventas`, `total_ventas`.
- Fechas UTC, ventas `CONFIRMADA`, incluye períodos sin ventas.

**GET `/api/dashboard/comercial`** (nuevo)

- Obligatorios: `fecha_inicio`, `fecha_fin` (`YYYY-MM-DD`).
- Opcional: `limite` (1–20, predeterminado 10).
- Duración máxima del rango solicitado: 367 días inclusivos.
- Respuesta:
  - `periodo` y `periodo_anterior` (ventana previa de igual duración).
  - `moneda=PEN`, `zona_horaria=UTC`, `criterio_estado=CONFIRMADA`.
  - `kpis`: `cantidad_ventas`, `total_ventas`, `ticket_promedio`.
  - `kpis_periodo_anterior`, `variacion_porcentual_ventas` (null si base=0).
  - `pedidos_por_estado`: `BORRADOR`, `CONFIRMADO`, `COMPLETADO`, `CANCELADO`.
  - `productos_destacados`: `producto_id`, `nombre`, `unidades`, `total_ventas`.
  - `clientes_destacados`: `cliente_id`, `nombre`, `cantidad_ventas`, `total_ventas`.
  - `vendedores_destacados`: `usuario_id`, `cantidad_ventas`, `total_ventas`.

Los valores de dinero y variación se serializan como cadenas decimales para no introducir errores de coma flotante. `cantidad_ventas` cuenta ventas confirmadas, **no cobros**. El ranking de productos usa importes de las líneas de venta; si hubiera inconsistencias históricas, la suma del ranking no necesariamente coincidirá con el total agregado de cabeceras. `vendedores_destacados` agrupa por `Venta.usuario_id` y no proporciona nombres: el frontend puede consultar sus datos según los permisos que tenga el usuario.

### Seguridad

Ambos endpoints requieren autenticación del proyecto y permiso `ventas.ver`. `empresa_id` se obtiene exclusivamente del usuario autenticado; nunca se admite como filtro enviado por el cliente. Los rankings relacionan entidades también por `empresa_id`. Respuestas esperadas: `401` para credenciales ausentes/no válidas según el middleware existente, `403` para permisos insuficientes, `422` para rango o parámetros inválidos, según sea aplicable.

### Uso desde React / TypeScript

```ts
const params = new URLSearchParams({
  fecha_inicio: '2026-10-01',
  fecha_fin: '2026-10-31',
  limite: '10',
});
const response = await fetch(`${API_BASE_URL}/api/dashboard/comercial?${params}`, {
  headers: { Authorization: `Bearer ${accessToken}` },
});
if (!response.ok) throw new Error(`Dashboard HTTP ${response.status}`);
const data = await response.json();
```

La pantalla puede mostrar tarjetas KPI, gráfico temporal desde `/ventas/serie`, barras por productos/clientes, y gráfico de pedidos por estado. Si `variacion_porcentual_ventas` es `null`, mostrar “sin base comparativa”, no “0%”. Convertir valores monetarios a formato de pantalla con precaución, preservando el decimal original para cálculos de negocio.

### Validación en Windows

1. Respaldar carpeta `backend` y reemplazar el código por el ZIP. Conservar el `.env` local (no incluido).
2. Activar `.venv` y comprobar conectividad con la base **testing** antes de ejecutar pruebas de integración.
3. Ejecutar:

```cmd
python -m pytest tests/test_dashboard_comercial_calculos.py tests/test_dashboard_comercial_http.py tests/test_dashboard_series_calculos.py tests/test_dashboard_http_contrato.py -q --tb=short
python -m pytest tests/ -q --tb=short
```

4. Iniciar `uvicorn app.main:app --reload`, abrir `/docs` y verificar ambos endpoints con un token de usuario autorizado. Comprobar con dos empresas distintas que sus métricas nunca se mezclan; comprobar usuario sin `ventas.ver`, datos sin ventas, períodos con anulaciones, cambio porcentual con base cero y ranking con empate.
5. No se ha ejecutado esta entrega frente a PostgreSQL/Supabase real en el entorno de generación. No desplegar en producción sin validar conexión, integración, permisos y rendimiento.

### Migraciones

No se introducen nuevas tablas ni columnas. **No ejecutar `alembic upgrade head` específicamente por esta fase** sin revisar primero las migraciones pendientes del proyecto en su conjunto.

### Alcance y límites

- Los resultados son por tiempo de creación en UTC, no por fecha de cobro ni fecha de entrega.
- No incluye datos predictivos adicionales; la API `/api/analytics` de MVP-01 permanece disponible para visualizaciones avanzadas.
- Ventas CONFIRMADA se mantienen alineadas con la definición ya utilizada por Analytics. No se deduce que una venta confirmada sea un pago registrado.
- Pendiente antes del cierre final: pruebas de integración con base real y regresión completa en entorno del proyecto. El resultado previo de 565 pruebas corresponde a la versión **anterior** a esta ampliación.
