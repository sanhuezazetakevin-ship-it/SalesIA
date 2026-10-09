# SalesIA Enterprise — MVP-01-E.1: núcleo de probabilidades

## Alcance

Funciones matemáticas puras para una población de ventas CONFIRMADAS previamente filtrada por la empresa del usuario y fechas UTC. No agrega endpoints, permisos, migraciones ni consultas SQL. No toca Supabase principal ni Testing.

- Evento A: `importe_total >= umbral_importe_alto` (umbral inclusivo y configurable; predeterminado PEN 100.00 solo para pruebas matemáticas, no es una definición empresarial definitiva).
- Evento B: `estado_pago == PAGADO`.
- Simple: P(A) y P(B).
- Conjunta: P(A ∩ B).
- Condicional: P(B|A).
- Bayes: P(A|B), calculada desde conteos sin redondeo intermedio.
- Variable aleatoria discreta: distribución de estados `PENDIENTE`, `PARCIAL`, `PAGADO`.
- Con denominador cero, se retorna `None` (`null` en JSON). Con población vacía, todas las probabilidades quedan indefinidas.
- Formato: probabilidades como cadenas decimales con cuatro posiciones, sin usar `float`.

**Importante:** este módulo calcula probabilidades empíricas descriptivas, no predicciones de comportamiento futuro. La muestra de ventas puede presentar sesgos.

## Instalación

Desde el ZIP, copiar en el backend respetando la estructura:

```
app/services/analytics_probabilidades_calculos.py
tests/test_analytics_probabilidades_calculos.py
```

No reemplazar `analytics_resumen_service.py`, `analytics_distribuciones_service.py`, ni los routers vigentes. No registrar rutas en `main.py` en esta subfase.

## Comandos Windows CMD

```cmd
python -m pytest tests/test_analytics_probabilidades_calculos.py -v --tb=short
python -m pytest tests/test_analytics_calculos.py tests/test_analytics_resumen_integracion.py tests/test_analytics_distribuciones_calculos.py tests/test_analytics_distribuciones_integracion.py tests/test_analytics_probabilidades_calculos.py -q --tb=short
```

El archivo nuevo contiene 23 casos de prueba parametrizados expandidos, además de las 31 pruebas precedentes; objetivo conjunto: 54 pruebas aprobadas.

## Fase siguiente

MVP-01-E.2: conectar este núcleo con PostgreSQL Testing y crear endpoint JWT/RBAC con filtro por empresa y periodo. Nunca acceder a la base principal desde las pruebas de integración.
