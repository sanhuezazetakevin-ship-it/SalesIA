# SalesIA — MVP-01-F.1 Persistencia de análisis

## Alcance
- Agrega **únicamente** `app/services/analytics_historial_service.py` y `tests/test_analytics_historial_validaciones.py`.
- Reutiliza las tablas `analisis_estadisticos` y `analisis_probabilidad`, sus CHECK y JSONB existentes.
- **No modifica** modelos, `main.py`, migraciones, rutas o permisos. No se exponen endpoints de escritura.
- Las funciones **no hacen commit**. El servicio llamador administra la transacción. `db.flush()` obtiene el ID sin confirmarla.
- `guardar_estadistico()` permite resultados JSON del resumen o distribuciones bajo tipo `VENTAS`.
- `guardar_probabilidad()` utiliza tipo `OTRO` y etiqueta `ANALISIS_DESCRIPTIVO`: el cálculo Bayes aquí es una frecuencia empírica, **no una predicción entrenada**.
- Los modelos no incluyen un campo `usuario_id`; se conserva el ID del ejecutor en un JSON de trazabilidad. Para trazabilidad fuerte o referencias, deberá diseñarse una migración futura.
- Se reutiliza `ventas.ver` como validación básica interna, **pero no se debe habilitar un POST HTTP con ese permiso de lectura**. Diseñar permiso de escritura específico antes de exponer creación de historial.
- Todas las consultas de historial filtran `empresa_id` en SQL. Rechazan tipos e IDs inválidos.
- El guardado no está enlazado todavía con los endpoints existentes: el historial se generará desde un orquestador autorizado en MVP-01-F.2.
- Se recomienda revisar datos existentes y CHECK de ambos modelos antes de ejecutar escrituras en Testing.

## Pruebas unitarias sin DB
```cmd
python -m pytest tests/test_analytics_historial_validaciones.py -v --tb=short
```

## Integración futura (MVP-01-F.2)
Ejecutar con `db_testing` comprobando antes que `TEST_DATABASE_URL` es Supabase Testing, **distinta de DATABASE_URL principal**. Crear escenarios multiempresa, guardar dentro de transacción rollback, verificar columnas obligatorias, aislamiento, commit y lectura. Nunca ejecutar escritura contra `DATABASE_URL`.
