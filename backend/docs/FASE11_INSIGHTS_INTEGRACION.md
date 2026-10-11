# SalesIA Enterprise — FASE 11: Insights empresariales

## Objetivo

Generar **observaciones descriptivas y determinísticas**, no predicciones automáticas, desde los análisis que el backend ya ha calculado y persistido. Cada observación conserva evidencia numérica, su origen y versión de regla. No se reciben métricas calculadas en el frontend.

## Dependencias

Reutiliza `insights`, `analisis_estadisticos`, `analisis_probabilidad` del esquema existente. **No hay migraciones nuevas**. Usa los permisos del seed actual `analitica.ver` (lectura) y `analitica.ejecutar` (generación y actualización de estado). El administrador debe comprobar que su usuario tiene esos permisos en testing.

## API HTTP (prefijo `/api`)

Todos los endpoints requieren `Authorization: Bearer <access_token>`.

1. `POST /api/insights/generar` — cuerpo `{"tipo":"estadistico","analisis_id":123}` o `tipo=probabilidad`; respuesta `201`, array de insights. El análisis debe pertenecer a la empresa y estar `COMPLETADO`. Si ya existen insights para ese análisis, devuelve los existentes, sin crear duplicados; esto es idempotente, aunque usa `201` en ambas situaciones. El bloqueo por fila del análisis serializa generaciones concurrentes.
2. `GET /api/insights?limite=20&estado=NUEVO&tipo=VENTAS` — respuesta `200`, `{ "items": [...], "limite": 20 }`; filtros opcionales, límite 1–100.
3. `GET /api/insights/{insight_id}` — respuesta `200` o `404`.
4. `PATCH /api/insights/{insight_id}/estado` — cuerpo `{"estado":"REVISADO"}` o `{"estado":"DESCARTADO"}`; respuesta `200`.

El objeto de respuesta incluye `id`, `empresa_id`, `analisis_estadistico_id`, `analisis_probabilidad_id`, `tipo_insight`, `prioridad`, `titulo`, `descripcion`, `recomendacion`, `estado`, `datos_soporte`, `created_at`, `updated_at`. Fechas ISO 8601.

Errores comunes: `401` falta autenticación, `403` permisos insuficientes, `404` análisis o insight no encontrado **en la empresa del usuario**, `422` petición inválida o análisis no completado.

## Reglas implementadas (versión 11.1)

- `SIN_VENTAS`: no existen ventas confirmadas en análisis guardado. Prioridad BAJA.
- `TICKET_DESCRIPTIVO`: muestra media, mediana, cantidad y total de ventas confirmadas. Prioridad BAJA. No afirma tendencias.
- `MUESTRA_VACIA`: falta muestra para calcular probabilidad. Prioridad BAJA.
- `FRECUENCIA_PAGADO`: frecuencia de ventas confirmadas con estado `PAGADO` basada en conteos. Prioridad MEDIA cuando la proporción es inferior a 0.50; en otro caso BAJA. No es una predicción futura.

Un insight persiste el tipo e ID del análisis fuente, el número de versión y la evidencia numérica. El cálculo de probabilidades rechaza inconsistencias entre conteos y frecuencia. No cambia la lógica de Analytics ni Dashboard.

## Flujo del frontend

1. Obtener un token válido del login existente.
2. Guardar previamente el análisis mediante `POST /api/analytics/historial/estadisticos` o `/probabilidades` (usando fechas según su contrato); utilizar el ID devuelto.
3. Ejecutar `POST /api/insights/generar` con tipo e ID; mostrar tarjetas con título, descripción, prioridad, recomendación y evidencias.
4. Implementar filtros por estado y tipo, vista de detalle y acciones `REVISADO` / `DESCARTADO`.
5. Probar estados de carga, resultado vacío, fallos `401/403/404/422` y separación de empresas.

Nunca incluir credenciales Supabase ni `DATABASE_URL` en Vite. El frontend solo necesita la URL del backend y token JWT, respetando CORS configurado en FastAPI.

## Verificación local

```cmd
python -m pytest tests/test_insights_reglas.py tests/test_insights_http.py -q --tb=short
python -m pytest tests/ -q --tb=short
python -m uvicorn app.main:app --reload
```

Revisar `http://127.0.0.1:8000/docs` y probar contra **PostgreSQL de testing**, nunca contra producción. Registrar evidencia de generación, historial, cambios de estado y aislamiento entre dos empresas. Ejecutar pruebas de regresión completas antes de declarar cierre oficial.

## Limitaciones deliberadas

Las reglas son descriptivas, no identifican causas de cambios ni generan predicciones. No se agregan modelos de IA ni permisos. No se borran registros; el historial conserva trazabilidad. `updated_at` se actualiza mediante SQLAlchemy al modificar el estado.
