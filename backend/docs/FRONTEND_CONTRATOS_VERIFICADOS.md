# SalesIA Enterprise — Contratos de frontend verificados en backend(5).zip

**Origen:** inspección estática de `app/main.py`, archivos `app/api/routes/*.py` y modelos de Dashboard y PDF. **No se modificó la lógica del backend.** Las rutas listadas provienen del código; los parámetros y esquemas finales deben contrastarse con `/openapi.json` cuando se ejecute FastAPI.

## Resumen

- Existen **88 rutas HTTP** declaradas por los routers del backend, más `/` y `/health`.
- Los routers de autenticación, clientes, productos, categorías, pedidos, ventas, pagos, entregas, proveedores, compras, Dashboard, Analytics, insights, notificaciones, reportes, roles y auditoría están conectados desde `app/main.py`.
- El código usa JWT y dependencias de usuario activo. **No se debe introducir una conexión de Supabase directamente en React.**
- No está demostrado aquí el contrato final del reconocimiento facial; no prometer integración facial sin pruebas E2E.

## Contratos visuales verificados

**GET `/api/dashboard/comercial`**: parámetros requeridos `fecha_inicio` y `fecha_fin` (ISO 8601 `YYYY-MM-DD`), `limite` opcional de 1 a 20 (predeterminado 10); JWT requerido. Respuesta `DashboardComercialResponse`: `periodo`, `periodo_anterior`, `moneda`, `zona_horaria`, `criterio_estado`, `kpis`, `kpis_periodo_anterior`, `variacion_porcentual_ventas`, `pedidos_por_estado`, `productos_destacados`, `clientes_destacados`, `vendedores_destacados`. Campos de KPIs: `cantidad_ventas` (entero), `total_ventas` (string decimal), `ticket_promedio` (string decimal o null). Los totales de rankings también son strings decimales.

**GET `/api/dashboard/ventas/serie`**: `fecha_inicio`, `fecha_fin` requeridos; `agrupacion=dia|mes` (predeterminado `dia`); JWT requerido. Respuesta: `fecha_inicio`, `fecha_fin`, `agrupacion`, `criterio_estado`, `zona_horaria`, `moneda` y `puntos`, donde cada punto contiene `fecha` (ISO), `cantidad_ventas` (entero) y `total_ventas` (string decimal). Usar gráfica lineal y tooltip con PEN.

**GET `/api/reportes/pdf-directo`**: `tipo`, `fecha_inicio`, `fecha_fin`, JWT. Devuelve `application/pdf` y cabecera Content-Disposition de descarga. Consumir como `blob` y verificar código HTTP. Esta ruta genera bajo demanda; no usar como sustituto de los endpoints antiguos con almacenamiento de archivos.

**GET `/api/analytics/resumen`, `/api/analytics/distribuciones`, `/api/analytics/probabilidades`, `/api/analytics/semana08`**: APIs presentes. Consultar `/openapi.json` para parámetros y esquema completo (no se copian campos no verificados).

**GET `/api/mejoras/dashboard`, `/api/mejoras/inventario`, `/api/mejoras/clientes`**: mejoras visuales presentes. Hay rutas distintas para notificaciones persistentes en `/api/mejoras/notificaciones-persistentes`; no confundir con un posible resumen de alertas en otras rutas.

## Reglas frontend

1. Configurar `VITE_API_BASE_URL` en `.env.local` con la URL real de FastAPI. No incluir contraseñas de base de datos ni `JWT_SECRET_KEY`.
2. Consultar `/openapi.json` de la **misma versión** desplegada. Crear tipos TypeScript a partir de los esquemas, evitando inferir campos.
3. Enviar `Authorization: Bearer <token>` cuando el endpoint lo requiere; manejar `401`, `403`, `422` y errores de red por separado. El login puede requerir formato `application/x-www-form-urlencoded`: verificarlo en Swagger.
4. Para importes monetarios, preservar string decimal y utilizar conversión numérica únicamente en la capa de visualización; no sumar dinero con `Number` en operaciones contables.
5. Implementar estados `loading`, `empty`, `error` y `success`; ningún gráfico debe tratar `null` como cero sin justificación.
6. Filtros de fecha y agregación deben actualizar el fetch de datos; respetar UTC y moneda PEN que devuelve la API.
7. Validar el flujo completo pedido → venta → pago/entrega → dashboard → PDF, con usuarios de prueba de dos empresas.
8. La selección de una barra puede abrir un panel de detalle; **el drill-down exige un endpoint apropiado y autorización**, no asumir que cualquier API de gráfico suministra detalles por transacción.
9. Para PDF: validar respuesta, crear ObjectURL temporal desde Blob, iniciar descarga y liberar con `URL.revokeObjectURL`.
10. Evitar cargas innecesarias de muchos gráficos simultáneos y cancelar peticiones al cambiar filtros.

## Limitaciones de la auditoría

Esta es una auditoría de código y contratos, no prueba de integración frontend; no se ejecutó toda la suite en esta sesión. La regresión `664 passed` y las `2 passed` del PDF corresponden a los resultados que reportó el propietario del proyecto en su equipo. Antes de integrar, generar OpenAPI real y hacer pruebas por endpoint.

## Inventario completo

El archivo `FRONTEND_INVENTARIO_ENDPOINTS.csv` contiene el listado exacto de los decoradores HTTP encontrados, su módulo, ruta, parámetros formales y response_model declarado, cuando existe.

| Módulo | Método | Ruta | Modelo declarado |
|---|---|---|---|
| analytics | GET | `/api/analytics/resumen` | `AnalyticsResumenResponse` |
| analytics_distribuciones | GET | `/api/analytics/distribuciones` | `AnalyticsDistribucionesResponse` |
| analytics_historial | POST | `/api/analytics/historial/estadisticos` | `AnalisisGuardado` |
| analytics_historial | POST | `/api/analytics/historial/probabilidades` | `AnalisisGuardado` |
| analytics_historial | GET | `/api/analytics/historial` | `HistorialListado` |
| analytics_historial | GET | `/api/analytics/historial/{tipo}/{analisis_id}` | `AnalisisGuardado` |
| analytics_probabilidades | GET | `/api/analytics/probabilidades` | `AnalyticsProbabilidadesResponse` |
| auditoria | GET | `/api/auditoria` | `HistorialAuditoria` |
| auth | POST | `/api/auth/login` | `LoginResponse` |
| auth | POST | `/api/auth/refresh` | `TokenResponse` |
| auth | POST | `/api/auth/logout` | `LogoutResponse` |
| auth | GET | `/api/auth/me` | `MeResponse` |
| categorias | POST | `/api/categorias` | `CategoriaResponse` |
| categorias | GET | `/api/categorias` | `CategoriaListadoResponse` |
| categorias | GET | `/api/categorias/{categoria_id}` | `CategoriaResponse` |
| categorias | PATCH | `/api/categorias/{categoria_id}` | `CategoriaResponse` |
| categorias | DELETE | `/api/categorias/{categoria_id}` | `CategoriaResponse` |
| clientes | POST | `/api/clientes` | `ClienteResponse` |
| clientes | GET | `/api/clientes` | `ClienteListadoResponse` |
| clientes | GET | `/api/clientes/{cliente_id}` | `ClienteResponse` |
| clientes | PATCH | `/api/clientes/{cliente_id}` | `ClienteResponse` |
| clientes | DELETE | `/api/clientes/{cliente_id}` | `ClienteResponse` |
| dashboard | GET | `/api/dashboard/ventas/serie` | `SerieVentasResponse` |
| dashboard | GET | `/api/dashboard/comercial` | `DashboardComercialResponse` |
| entregas | POST | `/api/entregas/ventas/{venta_id}/confirmar` | `EntregaConMovimientosResponse` |
| entregas | GET | `/api/entregas/ventas/{venta_id}` | `EntregaConMovimientosResponse` |
| entregas | GET | `/api/entregas/{entrega_id}` | `EntregaConMovimientosResponse` |
| insights | POST | `/api/insights/generar` | `list[InsightResponse]` |
| insights | GET | `/api/insights` | `InsightsListado` |
| insights | GET | `/api/insights/{insight_id}` | `InsightResponse` |
| insights | PATCH | `/api/insights/{insight_id}/estado` | `InsightResponse` |
| mejoras145 | GET | `/api/mejoras/dashboard` | `No declarado` |
| mejoras145 | GET | `/api/mejoras/inventario` | `No declarado` |
| mejoras145 | GET | `/api/mejoras/clientes` | `No declarado` |
| mejoras145 | GET | `/api/mejoras/notificaciones` | `No declarado` |
| mejoras145 | GET | `/api/mejoras/seguridad` | `No declarado` |
| notificaciones145 | POST | `/api/mejoras/notificaciones-persistentes/sincronizar` | `No declarado` |
| notificaciones145 | GET | `/api/mejoras/notificaciones-persistentes` | `No declarado` |
| notificaciones145 | PATCH | `/api/mejoras/notificaciones-persistentes/{notificacion_id}/leida` | `No declarado` |
| ordenes_compra | POST | `/api/compras/ordenes` | `OrdenCompraRespuesta` |
| ordenes_compra | GET | `/api/compras/ordenes` | `OrdenCompraPagina` |
| ordenes_compra | GET | `/api/compras/ordenes/{orden_id}` | `OrdenCompraRespuesta` |
| ordenes_compra | POST | `/api/compras/ordenes/{orden_id}/confirmar` | `OrdenCompraRespuesta` |
| ordenes_compra | POST | `/api/compras/ordenes/{orden_id}/cancelar` | `OrdenCompraRespuesta` |
| pagos | POST | `/api/pagos/ventas/{venta_id}` | `PagoResponse` |
| pagos | GET | `/api/pagos/ventas/{venta_id}/resumen` | `ResumenPagosResponse` |
| pagos | POST | `/api/pagos/{pago_id}/anular` | `PagoResponse` |
| pagos_proveedores | POST | `/api/compras/pagos` | `PagoProveedorRespuesta` |
| pagos_proveedores | GET | `/api/compras/pagos` | `PagoProveedorPagina` |
| pagos_proveedores | GET | `/api/compras/pagos/{pago_id}` | `PagoProveedorRespuesta` |
| pagos_proveedores | POST | `/api/compras/pagos/{pago_id}/anular` | `PagoProveedorRespuesta` |
| pedidos | POST | `/api/pedidos` | `PedidoConDetallesResponse` |
| pedidos | GET | `/api/pedidos` | `PedidoListadoResponse` |
| pedidos | GET | `/api/pedidos/{pedido_id}` | `PedidoConDetallesResponse` |
| pedidos | POST | `/api/pedidos/{pedido_id}/confirmar` | `PedidoResponse` |
| pedidos | POST | `/api/pedidos/{pedido_id}/cancelar` | `PedidoResponse` |
| productos | POST | `/api/productos` | `ProductoResponse` |
| productos | GET | `/api/productos` | `ProductoListadoResponse` |
| productos | GET | `/api/productos/{producto_id}` | `ProductoResponse` |
| productos | PATCH | `/api/productos/{producto_id}` | `ProductoResponse` |
| productos | DELETE | `/api/productos/{producto_id}` | `ProductoResponse` |
| proveedores | POST | `/api/proveedores` | `ProveedorRespuesta` |
| proveedores | GET | `/api/proveedores` | `ProveedorPagina` |
| proveedores | GET | `/api/proveedores/{proveedor_id}` | `ProveedorRespuesta` |
| proveedores | PATCH | `/api/proveedores/{proveedor_id}` | `ProveedorRespuesta` |
| proveedores | POST | `/api/proveedores/{proveedor_id}/desactivar` | `ProveedorRespuesta` |
| recepciones_compra | POST | `/api/compras/recepciones` | `RecepcionRespuesta` |
| recepciones_compra | GET | `/api/compras/recepciones` | `RecepcionPagina` |
| recepciones_compra | GET | `/api/compras/recepciones/{recepcion_id}` | `RecepcionRespuesta` |
| reportes | GET | `/api/reportes/previsualizar` | `No declarado` |
| reportes | POST | `/api/reportes/generar` | `No declarado` |
| reportes | GET | `/api/reportes/imprimible` | `No declarado` |
| reportes | GET | `/api/reportes` | `No declarado` |
| reportes | GET | `/api/reportes/pdf-directo` | `No declarado` |
| reportes | GET | `/api/reportes/{reporte_id}` | `No declarado` |
| reportes | GET | `/api/reportes/{reporte_id}/descargar` | `No declarado` |
| roles | GET | `/api/roles` | `list[RolResponse]` |
| roles | GET | `/api/roles/{rol_id}/permisos` | `RolPermisosResponse` |
| roles | POST | `/api/roles/asignaciones` | `AsignacionRolResponse` |
| roles | DELETE | `/api/roles/asignaciones` | `RevocacionRolResponse` |
| semana08 | GET | `/api/analytics/semana08` | `No declarado` |
| usuarios | POST | `/api/invitaciones` | `CrearInvitacionResponse` |
| usuarios | POST | `/api/auth/register-invitation` | `RegistroInvitacionResponse` |
| usuarios | GET | `/api/usuarios/pendientes` | `list[UsuarioPendienteResponse]` |
| usuarios | POST | `/api/usuarios/{usuario_id}/aprobar` | `AprobarUsuarioResponse` |
| ventas | POST | `/api/ventas/desde-pedido/{pedido_id}` | `VentaConDetallesResponse` |
| ventas | GET | `/api/ventas` | `VentaListadoResponse` |
| ventas | GET | `/api/ventas/{venta_id}` | `VentaConDetallesResponse` |
