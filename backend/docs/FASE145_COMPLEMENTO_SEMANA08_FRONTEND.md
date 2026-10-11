# SalesIA Enterprise — FASE 14.5 ampliada: integración y criterios

## Alcance realizado

- Mantiene el backend de `BACKEND(3).zip` (hasta FASE 14) y el avance 14.5.
- `GET /api/mejoras/dashboard`: tarjetas y gráficos comparativos, explicaciones no técnicas.
- `GET /api/mejoras/inventario`: consumo histórico simple, horizonte y advertencia. **No es ML entrenado.**
- `GET /api/mejoras/clientes`: **RFM histórico** hasta fecha final, con clientes activos sin compras, datos para gráfica, umbrales declarados, límite de 100 clientes por petición. El gráfico corresponde a la selección (no a toda la empresa si hay más clientes).
- `GET /api/mejoras/seguridad`: visualización agregada de eventos de acceso, requiere `auditoria.ver`.
- `GET /api/mejoras/notificaciones`: alertas calculadas, sin persistir (ruta previa compatible).
- `POST /api/mejoras/notificaciones-persistentes/sincronizar?fecha_inicio=YYYY-MM-DD&fecha_fin=YYYY-MM-DD`: genera alertas existentes y las guarda sin duplicados por empresa+clave, permiso `ventas.ver`. Ejecutar manualmente o mediante scheduler protegido. No envía correos/push.
- `GET /api/mejoras/notificaciones-persistentes?solo_no_leidas=true&limite=50`: historial de la empresa, permiso `ventas.ver`.
- `PATCH /api/mejoras/notificaciones-persistentes/{notificacion_id}/leida`: solo puede marcar alertas de su empresa, permiso `ventas.ver`.
- `GET /api/analytics/semana08?fecha_inicio=YYYY-MM-DD&fecha_fin=YYYY-MM-DD&media_hipotetica=150&alfa=0.05`: estadísticas sobre ventas confirmadas en la empresa autenticada, requiere `analitica.ver`. Los dos últimos parámetros son opcionales. Sin `media_hipotetica` no se realiza contraste de hipótesis.

## Semana 08: operación y explicación

- Varianza y desviación estándar tanto poblacionales como muestrales; estas últimas requieren al menos dos observaciones.
- Histograma empírico, tabla de probabilidades de estados de pago; probabilidades son frecuencias observadas y no pronósticos.
- Esperanza empírica: media aritmética de importes confirmados. No es pronóstico de ventas futuras.
- Prueba t bilateral de una muestra con scipy (si se solicita media hipotética). **Condiciones importantes:** independencia y validez del procedimiento deben verificarse; la interfaz debe presentar advertencias. El valor p no mide la probabilidad de que H0 sea verdadera. Con datos constantes o insuficientes se devuelve un estado explicativo sin valor p.
- Tope 50000 ventas y rango máximo 367 días, fechas UTC. Solo ventas `CONFIRMADA`; **ventas ≠ cobros**.
- Valores de dinero redondeados para visualización; usar el módulo financiero original para cantidades contables exactas.

## Frontend: evitar estadísticas crudas sin contexto

Renderizar cada respuesta con: título comprensible, gráfico (Recharts), unidades PEN o conteo, fechas del intervalo, leyenda, comparación/interpretación, avisos y estado vacío. **Nunca fabricar datos** cuando `sin_datos=true`. No presentar la prueba t como una certeza. Para móvil usar barras horizontales cuando las etiquetas son largas.

| Campo | Gráfico propuesto | Mensaje para usuario |
| --- | --- | --- |
| `resultados.histograma` | Barras | «Así se distribuyen los importes de tus ventas» |
| `distribucion_estados_pago` | Barras apiladas o normales | «Proporción de ventas según estado de pago» |
| `resultados.desviacion_poblacional` | Tarjeta + histograma | «Cuánto varían los importes» |
| `resultados.contraste` | Panel con explicación y p-valor | «Evidencia respecto a una media de referencia» |
| `mejoras/clientes.grafico` | Barras por segmento | «Cómo se agrupan los clientes según sus compras» |
| `mejoras/inventario.items[].grafico` | Barras | «Existencias frente a demanda orientativa» |
| Notificaciones persistentes | Lista con iconos y filtros; indicador de leídas | «Eventos que requieren revisión» |

## Instalación, orden obligatorio y pruebas

1. Crear respaldo del backend actual. Sustituir el código, **manteniendo `.env` fuera del ZIP**.
2. Asegurar `scipy`, `psycopg`, FastAPI, SQLAlchemy, Alembic y las dependencias previas del proyecto. `python -m pip install scipy` solo si no está instalado.
3. **En DATABASE_URL de la base de testing**, verificar `alembic current` y `alembic heads`; confirmar que el head previo sea `746fcabdf249`. Después `alembic upgrade head` y comprobar que existe `notificaciones_empresariales`. Nunca ejecutar a ciegas sobre producción.
4. `python -m pytest tests/test_semana08_calculos.py tests/test_fase145_rfm.py tests/test_fase145_calculos.py tests/test_fase145_contratos.py -q --tb=short`
5. Probar JWT, permiso correcto, ausencia de permiso, empresa A/B, sincronización repetida, marcado de alertas de otra empresa (esperado 404), inventario vacío, clientes sin compras, fechas inválidas, datos constantes, valor p, Swagger `/docs`.
6. `python -m pytest tests/ -q --tb=short` con PostgreSQL testing antes de declarar cierre.

## Limitaciones y actividades futuras **sin implementar**

- No se añadió Redis, workers/colas ni rate limiting distribuido (requieren infraestructura y pruebas de concurrencia; configurarlos sin controles puede crear una falsa garantía).
- No existe un modelo predictivo ML entrenado ni mediciones de error del pronóstico. La proyección actual es una regla descriptiva.
- No se conectó el frontend React ni se renderizaron visualizaciones finales.
- No se ejecutó aquí la migración sobre PostgreSQL de testing, las pruebas HTTP ni la regresión de toda la suite.
- No se añadió un sistema de entrega push/correo a las notificaciones; su sincronización es bajo demanda.
- La generación de alertas persistentes solo reconoce los tipos derivados que ya ofrecía 14.5.

## Datos multiempresa

Los servicios toman `empresa_id` del usuario autenticado y filtran consultas por empresa. La restricción única `(empresa_id, clave)` protege las notificaciones. Se necesitan **pruebas reales de aislamiento** con dos empresas en PostgreSQL de testing antes del despliegue.
