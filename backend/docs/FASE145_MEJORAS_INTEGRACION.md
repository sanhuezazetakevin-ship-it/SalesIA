# SalesIA — FASE 14.5: integración frontend y validación

## Alcance entregado

Cinco endpoints de **solo lectura** con datos explicativos listos para representación en React/Recharts/Chart.js. No devuelven imágenes: `grafico.tipo`, `grafico.etiquetas` y `grafico.valores` constituyen el contrato del gráfico. Cuando la serie esté vacía, mostrar "Aún no hay datos suficientes". Los valores numéricos respaldan los gráficos y son indispensables para accesibilidad y trazabilidad; no se deben mostrar sin contexto.

- `GET /api/mejoras/dashboard?fecha_inicio=2026-09-01&fecha_fin=2026-09-30` — KPIs comparativos, estado de pedidos, productos destacados, interpretación.
- `GET /api/mejoras/inventario?fecha_inicio=...&fecha_fin=...&horizonte=14&limite=30` — consumo promedio simple, cobertura y riesgo (NO modelo ML entrenado).
- `GET /api/mejoras/clientes?fecha_inicio=...&fecha_fin=...&limite=50` — segmentación descriptiva por frecuencia y recencia dentro del rango elegido, no RFM histórico global.
- `GET /api/mejoras/notificaciones?fecha_inicio=...&fecha_fin=...` — alertas derivadas sobre pedidos borrador y productos sin stock (NO se guardan ni marcan leídas).
- `GET /api/mejoras/seguridad?fecha_inicio=...&fecha_fin=...` — conteos por resultado de autenticación sin detalles sensibles; requiere permiso `auditoria.ver`.

Todas las rutas requieren `Authorization: Bearer <access_token>` con sesión vigente. Las primeras cuatro exigen `ventas.ver`. El `empresa_id` nunca se toma del frontend: se resuelve usando la identidad autenticada. El servidor aplica filtros de tenant en cada consulta, incluso en joins de ventas y detalles. Las fechas tienen un máximo de 367 días, no permiten fechas futuras, y se interpretan en UTC.

## Código de ejemplo React

```ts
const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/mejoras/dashboard?fecha_inicio=2026-09-01&fecha_fin=2026-09-30`, {
  headers: { Authorization: `Bearer ${token}` },
});
if (!response.ok) throw new Error(`HTTP ${response.status}`);
const data = await response.json();
// data.graficos[0] -> { tipo:'barra', etiquetas:['BORRADOR',...], valores:[0,...] }
```

Recomendación UI: etiqueta en lenguaje cotidiano, línea de explicación, leyenda accesible y tabla accesible expandible. No presentar predicciones de demanda como certezas. Respetar los estados `sin_datos` y advertencias.

## Qué queda fuera y debe implementarse antes de afirmar que está en producción

- **Caché Redis**, colas asíncronas de exportación, controles de tasa distribuidos y observabilidad gestionada **no están integrados**. Requieren infraestructura y pruebas de concurrencia.
- Las notificaciones son **alertas derivadas**, sin almacenamiento, suscripciones ni estados leído/no leído.
- La predicción usa un **promedio histórico simple**, no un modelo ML entrenado ni intervalos de confianza estadística.
- La segmentación es por compras en ventana, no un RFM longitudinal ni un modelo de churn.
- La seguridad agrega un tablero de eventos, **no** un motor automático antifraude ni protección de fuerza bruta. Conservar los controles JWT/RBAC existentes. Implementar limitación de tasas en proxy de despliegue y validar IPs confiables.

## Pruebas

```bat
python -m pytest tests/test_fase145_calculos.py tests/test_fase145_contratos.py -q --tb=short
python -m pytest tests/ -q --tb=short
```

Además: probar manualmente usuarios con y sin permisos; dos empresas A y B; que no aparezcan productos/ventas/eventos de B en consultas de A; respuestas sin datos y rangos inválidos; carga sobre datos reales; revisar `/docs`. No ejecutar migraciones: esta iteración no añade tablas.
