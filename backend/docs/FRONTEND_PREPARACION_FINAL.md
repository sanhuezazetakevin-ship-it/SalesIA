# SalesIA Enterprise — preparación antes de recibir React

Base revisada: `backend(5).zip`. Esta entrega conserva los módulos existentes y añade una suite de contratos sin tocar servicios, modelos ni migraciones.

## 1. Ejecución de pruebas

Desde Windows CMD, dentro de `backend` y con el entorno Python que ya funcionó:

```cmd
python -m pytest tests/test_frontend_contract_ready.py -q --tb=short
```

Después, si hay tiempo:

```cmd
python -m pytest tests/test_dashboard_comercial_http.py tests/test_dashboard_http_contrato.py tests/test_reportes_pdf_directo.py tests/test_railway_pdf_http_pg_real.py -q --tb=short
```

No ejecutar migraciones ni modificar Supabase de producción para esta entrega. No afirmar que toda la integración frontend está probada hasta disponer del proyecto React.

## 2. Contratos concretos confirmados en código

- `POST /api/auth/login` — JSON `{ "email": "...", "password": "..." }`; devuelve `access_token`, `refresh_token`, `token_type`, `expires_in` y `usuario`.
- `GET /api/dashboard/comercial?fecha_inicio=YYYY-MM-DD&fecha_fin=YYYY-MM-DD` — requiere Bearer JWT, devuelve `kpis`, `kpis_periodo_anterior`, `variacion_porcentual_ventas`, `productos_destacados`, `clientes_destacados`, `vendedores_destacados`, `pedidos_por_estado`, `moneda` (`PEN`) y `zona_horaria` (`UTC`). `limite` es opcional de 1 a 20.
- `GET /api/dashboard/ventas/serie?fecha_inicio=...&fecha_fin=...&agrupacion=dia` — `agrupacion` acepta `dia` o `mes`; devuelve `puntos` con `fecha`, `cantidad_ventas`, `total_ventas`.
- `GET /api/analytics/resumen?fecha_inicio=...&fecha_fin=...` — consultar Swagger para esquema exacto.
- `GET /api/analytics/distribuciones?fecha_inicio=...&fecha_fin=...&variable=importe_venta&intervalos=5` — variable `importe_venta` o `estado_pago`; intervalos 1–20.
- `GET /api/reportes/pdf-directo?tipo=VENTAS&fecha_inicio=...&fecha_fin=...` — tipo: `VENTAS`, `ESTADISTICO`, `INVENTARIO`, `CLIENTES` o `RENDIMIENTO`. Responde `application/pdf` binario. Usar `response.blob()`, no `response.json()`.
- `GET /health` — comprobación básica de servicio.

## 3. Gráficos interactivos prioritarios

1. Serie de ventas por fecha: línea, tooltip con fecha y soles, control día/mes. Usar `puntos` de `/api/dashboard/ventas/serie`.
2. KPIs y ranking: tarjetas y barras para `productos_destacados`, `clientes_destacados` y `vendedores_destacados` de `/api/dashboard/comercial`.
3. Distribución estadística: columnas/histograma según el JSON real de `/api/analytics/distribuciones`.
4. PDF: botón con fechas y tipo; descargar `Blob` autenticado, mostrar errores claros y deshabilitar el botón mientras se genera.

**Regla monetaria:** `total_ventas`, `ticket_promedio`, `variacion_porcentual_ventas` y otros importes del Dashboard son strings decimales por diseño. Convertir solo para gráficos; evitar usar `Number`/float como fuente de verdad para operaciones monetarias.

**Regla de permisos:** JWT en `Authorization: Bearer <token>`; manejar 401 (sesión) y 403 (acceso denegado) de forma distinta. Jamás incluir `DATABASE_URL` ni `JWT_SECRET_KEY` en frontend ni `VITE_*`.

## 4. Checklist para mañana

- [ ] Acceso a `/docs` y `/openapi.json` desde el equipo del frontend.
- [ ] Validar login y `GET /api/auth/me` con usuario de prueba.
- [ ] Comprobar CORS para la URL exacta de Vite (por ejemplo, `http://localhost:5173`).
- [ ] Comparar DTOs TypeScript con schemas de OpenAPI actual, no rutas supuestas.
- [ ] Probar Dashboard con fechas y con dataset vacío.
- [ ] Probar que ninguna respuesta incluya datos de otra empresa.
- [ ] Probar el PDF con Bearer y verificar descarga PDF.
- [ ] Revisar errores 401, 403, 422, y conexión perdida.
- [ ] Realizar el flujo pedido → venta → pago → inventario → Analytics → PDF con datos de prueba.

## 5. Evidencia y límites

La regresión de 664 pruebas fue informada por el desarrollador sobre una versión previa. Las dos pruebas PG del PDF también fueron aprobadas por él. Las **nuevas siete pruebas de contratos de este paquete no se pudieron ejecutar en el entorno que armó el ZIP por falta de `psycopg` y acceso a repositorios Python**; deben ejecutarse en Windows antes de considerarse aprobadas.
