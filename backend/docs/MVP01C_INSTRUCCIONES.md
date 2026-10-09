# MVP-01-C — Prueba integrada de Analytics

Copiar `tests/test_analytics_resumen_integracion.py` a la misma ubicación en el backend.
Se reutilizan `tests/conftest.py::db_testing`, `tests.test_venta_service.preparar_venta` y
`tests.test_pedido_service._escenario_confirmacion` del backend existente.

El archivo crea datos mediante la fixture de Testing con SAVEPOINT y rollback al concluir.
No sustituye `get_current_active_user` ni la validación JWT; únicamente `get_db`.

Ejecutar:

    python -m pytest tests/test_analytics_resumen_integracion.py -v --tb=short

Tras aprobar, ejecutar:

    python -m pytest tests/test_analytics_calculos.py tests/test_analytics_resumen_integracion.py -q --tb=short

Nota: las pruebas no requieren migración, seed ni limpieza manual de datos.
No ejecutar con DATABASE_URL principal; la fixture comprueba aislamiento Supabase.
