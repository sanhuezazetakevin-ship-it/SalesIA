# SalesIA Enterprise — Fase 3, consola funcional de pruebas

## Alcance
Se preservan el diseño monocromático y las pantallas originales. Se agrega la pestaña **7. Módulos Comerciales (Pruebas)** con clientes, categorías, productos, pedidos, ventas, pagos y consulta/confirmación de entregas. El backend del ZIP original no fue modificado.

## Entorno
1. Usar una base Supabase de testing verificada; confirmar `ENVIRONMENT=testing` y que `DATABASE_URL` se refiere al proyecto correcto. La app se conecta a `http://localhost:8000` (o `VITE_API_BASE_URL`).
2. Ejecutar en frontend `npm ci`, `npm run build`, `npm run dev`.
3. Iniciar FastAPI desde backend con su `.env` privado y `.venv` local.
4. Iniciar sesión como usuario autorizado. Las operaciones de escritura exigen permisos; una respuesta 403 es válida al usar roles insuficientes.

## Secuencia sugerida
- Lectura: actualizar listados de clientes, categorías, productos, pedidos y ventas.
- Crear una categoría de testing.
- Crear un cliente de testing con nombre y, opcionalmente, tipo/número de documento.
- Crear un producto de testing (usar `SERVICIO` sin control de stock para comprobaciones iniciales, o productos con inventario configurado para flujos físicos).
- Crear pedido con IDs de cliente y producto, cantidad > 0 y descuento >= 0. El backend calcula precios, impuestos y totales.
- Consultar el pedido. Confirmar el pedido si corresponde. Crear una venta desde el pedido confirmado, según las reglas de negocio del backend.
- Consultar pagos de la venta; registrar un pago con monto válido. La petición envía cabecera `Idempotency-Key` por operación.
- Consultar una entrega; confirmar una entrega únicamente si stock y reservas de pruebas han sido preparados. Puede afectar el inventario físico.
- Opcionalmente: editar nombres, desactivar catálogo, cancelar pedidos, anular pagos, previa confirmación.

## Advertencias
- Las operaciones crean/modifican datos de Supabase Testing. No ejecutar contra producción.
- No existen en esta pantalla interfaces completas de ajuste/inicialización de inventario, ni operaciones de venta directa; no se inventan endpoints.
- El listado usa las primeras 100 filas; no representa un listado de paginación completa.
- No publicar `.env`, JWT, refresh tokens ni respuestas con información personal en capturas.
- Antes de `git add`, verificar cambios y excluir `tsconfig.tsbuildinfo`, `node_modules`, `dist` y scripts de administración local.
- Los contratos de pago incluyen una clave de idempotencia única por clic; ante un fallo de red con resultado desconocido no reintentar manualmente sin comprobar primero el resumen de pagos.

## Verificaciones técnicas
- TypeScript: `tsc -b --pretty false` OK durante preparación.
- Compilación completa Vite, pruebas HTTP e integración con PostgreSQL: pendientes de ejecutarse en el PC de Windows.


## Formularios operativos estilo ERP

- Clientes: selector DNI/RUC/CE/PASAPORTE, nombre, documento, correo, teléfono y dirección; edición de estos campos. Tipo y número de documento se envían juntos.
- Categorías: nombre, descripción y edición.
- Productos: SKU, nombre, descripción, tipo, categoría de una lista, precio, costo y control de stock; edición.
- Pedidos: seleccionar cliente y producto desde listas, cantidad, descuento y observaciones. El backend determina los importes.
- Ventas y pagos: selector de pedidos confirmados y ventas disponibles, sin ingreso manual de IDs.
- Los selectores dependen de catálogos cargados; se limitan a los primeros 100 registros por colección en esta versión de pruebas.
- No se implementaron nuevos endpoints ni rediseño visual. Operaciones destructivas requieren confirmación.
