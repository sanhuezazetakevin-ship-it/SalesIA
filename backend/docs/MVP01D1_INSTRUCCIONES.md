# SalesIA Enterprise — MVP-01-D.1

## Instalación

Copiar `tests/test_analytics_distribuciones_integracion.py` dentro de `backend/tests/`. No reemplazar archivos existentes. Este archivo importa los helpers de `tests/test_analytics_resumen_integracion.py` (MVP-01-C), que ya debe estar instalado.

## Seguridad

Las pruebas usan `db_testing` del `tests/conftest.py` existente, que verifica que `DATABASE_URL` y `TEST_DATABASE_URL` no apunten al mismo Supabase. Todos los datos creados dentro de la fixture se revierten mediante la transacción externa de prueba. No ejecutar migraciones y no cambiar `DATABASE_URL`.

## Comandos en Windows CMD

```cmd
python -m pytest tests/test_analytics_distribuciones_integracion.py -v --tb=short
python -m pytest tests/test_analytics_calculos.py tests/test_analytics_resumen_integracion.py tests/test_analytics_distribuciones_calculos.py tests/test_analytics_distribuciones_integracion.py -q --tb=short
```

Se esperan 9 pruebas nuevas y 31 pruebas Analytics en conjunto, si todo funciona correctamente.

## Escenarios

Sin JWT (401); datos vacíos con JWT (200); intervalos y exclusión de ventas no confirmadas; frecuencias por `estado_pago`; límites UTC; separación multiempresa; falta de permiso `ventas.ver` (403); fechas inválidas (422); parámetros inválidos (422).

## Nota estadística

La suma de frecuencias relativas redondeadas a cuatro decimales puede diferir de 1 por redondeo; el total de frecuencias **absolutas** debe coincidir exactamente con `total_observaciones`.
