/**
 * Suite de Pruebas de Integración Frontend — SalesIA Enterprise
 * Ejecuta y verifica cada contrato de extremo a extremo tal como los consume
 * el código de React en el navegador.
 */

const VITE_URL = 'http://localhost:5173';
const API_URL = 'http://localhost:8000';

const CREDENCIALES_DEMO = {
  email: 'admin@salesia.com',
  password: 'admin123456',
};

const resultados = [];

function registrarResultado(seccion, prueba, exito, detalle = '') {
  resultados.push({ seccion, prueba, exito, detalle });
  const icono = exito ? '✓' : '✗';
  console.log(`  [${icono}] ${prueba}: ${detalle}`);
}

async function ejecutarPruebas() {
  console.log('\n============================================================');
  console.log('   SALESIA ENTERPRISE — BATERÍA DE PRUEBAS FRONTEND');
  console.log('============================================================\n');

  // 1. SERVICIOS Y CONECTIVIDAD
  console.log('1. Conectividad y Verificación de Servidores');
  try {
    const resVite = await fetch(VITE_URL);
    const html = await resVite.text();
    const contieneRoot = html.includes('id="root"');
    registrarResultado(
      'Servidores',
      'Vite Dev Server (http://localhost:5173)',
      resVite.status === 200 && contieneRoot,
      `HTTP ${resVite.status} — HTML servido correctamente (${html.length} bytes)`
    );
  } catch (err) {
    registrarResultado('Servidores', 'Vite Dev Server', false, `Fallo de conexión: ${err.message}`);
  }

  try {
    const resHealth = await fetch(`${API_URL}/health`);
    const dataHealth = await resHealth.json();
    registrarResultado(
      'Servidores',
      'FastAPI Backend (/health)',
      resHealth.status === 200 && dataHealth.status === 'ok',
      `HTTP ${resHealth.status} — servicio: "${dataHealth.service}"`
    );
  } catch (err) {
    registrarResultado('Servidores', 'FastAPI Backend', false, `Fallo de conexión: ${err.message}`);
  }

  try {
    const resCors = await fetch(`${API_URL}/health`, {
      headers: { Origin: VITE_URL },
    });
    const allowOrigin = resCors.headers.get('access-control-allow-origin');
    const allowCreds = resCors.headers.get('access-control-allow-credentials');
    registrarResultado(
      'Servidores',
      'Protocolo CORS para origen Vite',
      resCors.ok && (allowOrigin === VITE_URL || allowOrigin === '*'),
      `Access-Control-Allow-Origin: "${allowOrigin}", Credentials: "${allowCreds}"`
    );
  } catch (err) {
    registrarResultado('Servidores', 'Protocolo CORS', false, err.message);
  }

  // 2. AUTENTICACIÓN Y SEGURIDAD HTTP
  console.log('\n2. Autenticación y Manejo de Protocolo 401/403');
  let token = null;

  try {
    const resLogin = await fetch(`${API_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(CREDENCIALES_DEMO),
    });
    const dataLogin = await resLogin.json();
    token = dataLogin.access_token;
    registrarResultado(
      'Autenticación',
      'Inicio de Sesión (POST /api/auth/login)',
      resLogin.status === 200 && !!token,
      `Token recibido (expira en ${dataLogin.expires_in}s), Usuario: "${dataLogin.usuario?.nombre}"`
    );
  } catch (err) {
    registrarResultado('Autenticación', 'Inicio de Sesión', false, err.message);
  }

  try {
    const resMe = await fetch(`${API_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' },
    });
    const dataMe = await resMe.json();
    registrarResultado(
      'Autenticación',
      'Identidad y Aislamiento (GET /api/auth/me)',
      resMe.status === 200 && dataMe.empresa_id === 1,
      `Usuario #${dataMe.id} (${dataMe.email}), Empresa ID: #${dataMe.empresa_id}, Activo: ${dataMe.activo}`
    );
  } catch (err) {
    registrarResultado('Autenticación', 'Identidad', false, err.message);
  }

  try {
    const res401 = await fetch(`${API_URL}/api/auth/me`, {
      headers: { Accept: 'application/json' },
    });
    registrarResultado(
      'Autenticación',
      'Rechazo Seguro 401 sin Bearer Token',
      res401.status === 401,
      `HTTP ${res401.status} ${res401.statusText} (Rechazo correcto de sesión no autenticada)`
    );
  } catch (err) {
    registrarResultado('Autenticación', 'Rechazo Seguro 401', false, err.message);
  }

  try {
    const resTokenInvalido = await fetch(`${API_URL}/api/auth/me`, {
      headers: { Authorization: 'Bearer token_invalido_falso_123', Accept: 'application/json' },
    });
    registrarResultado(
      'Autenticación',
      'Rechazo Seguro 401 con Token Falsificado',
      resTokenInvalido.status === 401,
      `HTTP ${resTokenInvalido.status} (Firma o sesión rechazada exitosamente)`
    );
  } catch (err) {
    registrarResultado('Autenticación', 'Rechazo Token Falso', false, err.message);
  }

  const authHeaders = {
    Authorization: `Bearer ${token}`,
    Accept: 'application/json',
  };

  // 3. DASHBOARD COMERCIAL Y SERIES TEMPORALES
  console.log('\n3. Dashboard Comercial y Series Temporales');
  try {
    const resDash = await fetch(
      `${API_URL}/api/dashboard/comercial?fecha_inicio=2026-01-01&fecha_fin=2026-12-31&limite=5`,
      { headers: authHeaders }
    );
    const dataDash = await resDash.json();
    const kpisOk = dataDash.kpis && typeof dataDash.kpis.total_ventas === 'string';
    registrarResultado(
      'Dashboard',
      'KPIs Ejecutivos (GET /api/dashboard/comercial)',
      resDash.status === 200 && kpisOk,
      `Ventas: ${dataDash.kpis?.cantidad_ventas}, Total: PEN ${dataDash.kpis?.total_ventas}, Ticket Promedio: PEN ${dataDash.kpis?.ticket_promedio}`
    );

    const rankingsOk =
      Array.isArray(dataDash.productos_destacados) &&
      Array.isArray(dataDash.clientes_destacados);
    registrarResultado(
      'Dashboard',
      'Rankings de Rendimiento (Top Productos / Clientes)',
      rankingsOk,
      `Top Productos: ${dataDash.productos_destacados?.length}, Top Clientes: ${dataDash.clientes_destacados?.length}`
    );
  } catch (err) {
    registrarResultado('Dashboard', 'KPIs Ejecutivos', false, err.message);
  }

  try {
    const resSerie = await fetch(
      `${API_URL}/api/dashboard/ventas/serie?fecha_inicio=2026-01-01&fecha_fin=2026-12-31&agrupacion=dia`,
      { headers: authHeaders }
    );
    const dataSerie = await resSerie.json();
    const puntosOk = Array.isArray(dataSerie.puntos) && dataSerie.puntos.length > 0;
    registrarResultado(
      'Dashboard',
      'Serie Temporal SVG (GET /api/dashboard/ventas/serie)',
      resSerie.status === 200 && puntosOk,
      `${dataSerie.puntos?.length} puntos temporales calculados (Moneda: ${dataSerie.moneda})`
    );
  } catch (err) {
    registrarResultado('Dashboard', 'Serie Temporal', false, err.message);
  }

  // 4. OPERACIÓN COMERCIAL
  console.log('\n4. Operaciones Comerciales (Clientes, Catálogo, Ventas)');
  try {
    const resClientes = await fetch(`${API_URL}/api/clientes?pagina=1&limite=10`, { headers: authHeaders });
    const dataClientes = await resClientes.json();
    registrarResultado(
      'Comercial',
      'Catálogo de Clientes (GET /api/clientes)',
      resClientes.status === 200 && Array.isArray(dataClientes.clientes),
      `Total registrados: ${dataClientes.total}, Primer cliente: "${dataClientes.clientes?.[0]?.nombre}"`
    );
  } catch (err) {
    registrarResultado('Comercial', 'Clientes', false, err.message);
  }

  try {
    const resProds = await fetch(`${API_URL}/api/productos?pagina=1&limite=10`, { headers: authHeaders });
    const dataProds = await resProds.json();
    registrarResultado(
      'Comercial',
      'Catálogo de Productos (GET /api/productos)',
      resProds.status === 200 && Array.isArray(dataProds.productos),
      `Total productos: ${dataProds.total}, SKU: "${dataProds.productos?.[0]?.sku}", Precio: PEN ${dataProds.productos?.[0]?.precio_venta}`
    );
  } catch (err) {
    registrarResultado('Comercial', 'Productos', false, err.message);
  }

  try {
    const resVentas = await fetch(`${API_URL}/api/ventas?pagina=1&limite=10`, { headers: authHeaders });
    const dataVentas = await resVentas.json();
    registrarResultado(
      'Comercial',
      'Registro de Ventas (GET /api/ventas)',
      resVentas.status === 200 && Array.isArray(dataVentas.ventas),
      `Total ventas registradas: ${dataVentas.total}, Código: "${dataVentas.ventas?.[0]?.codigo}", Estado: ${dataVentas.ventas?.[0]?.estado}`
    );
  } catch (err) {
    registrarResultado('Comercial', 'Ventas', false, err.message);
  }

  // 5. MOTOR ESTADÍSTICO Y ANALYTICS (SEMANAS 07 Y 08)
  console.log('\n5. Motor Estadístico y Analytics (Semanas 07 y 08)');
  try {
    const resResumen = await fetch(
      `${API_URL}/api/analytics/resumen?fecha_inicio=2026-01-01&fecha_fin=2026-12-31`,
      { headers: authHeaders }
    );
    const dataResumen = await resResumen.json();
    registrarResultado(
      'Analytics',
      'Media y Mediana (GET /api/analytics/resumen)',
      resResumen.status === 200 && dataResumen.cantidad_ventas > 0,
      `Media (Ticket Promedio): PEN ${dataResumen.ticket_promedio}, Mediana: PEN ${dataResumen.mediana_ventas}`
    );
  } catch (err) {
    registrarResultado('Analytics', 'Media y Mediana', false, err.message);
  }

  try {
    const resDist = await fetch(
      `${API_URL}/api/analytics/distribuciones?fecha_inicio=2026-01-01&fecha_fin=2026-10-11&variable=importe_venta&intervalos=5`,
      { headers: authHeaders }
    );
    const dataDist = await resDist.json();
    const listaDist = dataDist.distribucion || dataDist.intervalos || [];
    registrarResultado(
      'Analytics',
      'Histograma de Frecuencias (GET /api/analytics/distribuciones)',
      resDist.status === 200 && Array.isArray(listaDist) && listaDist.length > 0,
      `${listaDist.length} intervalos calculados para variable "${dataDist.variable}"`
    );
  } catch (err) {
    registrarResultado('Analytics', 'Histograma', false, err.message);
  }

  try {
    const resBayes = await fetch(
      `${API_URL}/api/analytics/probabilidades?fecha_inicio=2026-01-01&fecha_fin=2026-10-11&umbral_importe=100.00`,
      { headers: authHeaders }
    );
    const dataBayes = await resBayes.json();
    const bayesOk = typeof dataBayes.bayes_importe_alto_dado_pagado === 'string';
    registrarResultado(
      'Analytics',
      'Probabilidades y Teorema de Bayes (GET /api/analytics/probabilidades)',
      resBayes.status === 200 && bayesOk,
      `P(Pagado): ${dataBayes.probabilidad_pagado}, P(Alto): ${dataBayes.probabilidad_importe_alto}, Bayes P(Alto|Pagado): ${dataBayes.bayes_importe_alto_dado_pagado}`
    );
  } catch (err) {
    registrarResultado('Analytics', 'Teorema de Bayes', false, err.message);
  }

  try {
    const resS08 = await fetch(
      `${API_URL}/api/analytics/semana08?fecha_inicio=2026-01-01&fecha_fin=2026-10-11&media_hipotetica=1500&alfa=0.05`,
      { headers: authHeaders }
    );
    const dataS08 = await resS08.json();
    const contraste = dataS08.resultados?.contraste || dataS08.contraste;
    const contrasteOk = contraste && typeof contraste.valor_p === 'number';
    registrarResultado(
      'Analytics',
      'Semana 08: Contraste t de Student (GET /api/analytics/semana08)',
      resS08.status === 200 && contrasteOk,
      `t: ${contraste?.estadistico_t}, p-valor: ${contraste?.valor_p}, Decisión: ${contraste?.rechazar_hipotesis_nula ? 'RECHAZA H0' : 'NO RECHAZA H0'}`
    );
  } catch (err) {
    registrarResultado('Analytics', 'Semana 08 Contraste', false, err.message);
  }

  // 6. GENERACIÓN Y DESCARGA DE REPORTES PDF DIRECTOS
  console.log('\n6. Emisión de Reportes PDF en Memoria (Sección 6 del PDF)');
  const tiposReporte = ['VENTAS', 'ESTADISTICO', 'INVENTARIO', 'CLIENTES', 'RENDIMIENTO'];

  for (const tipo of tiposReporte) {
    try {
      const resPdf = await fetch(
        `${API_URL}/api/reportes/pdf-directo?tipo=${tipo}&fecha_inicio=2026-01-01&fecha_fin=2026-12-31`,
        { headers: { Authorization: `Bearer ${token}`, Accept: 'application/pdf' } }
      );

      const contentType = resPdf.headers.get('content-type') || '';
      const buffer = await resPdf.arrayBuffer();
      const bytes = new Uint8Array(buffer);
      // Validar cabecera mágica de PDF (%PDF-)
      const esPdfValido =
        bytes.length > 500 &&
        bytes[0] === 0x25 && // %
        bytes[1] === 0x50 && // P
        bytes[2] === 0x44 && // D
        bytes[3] === 0x46; // F

      registrarResultado(
        'Reportes PDF',
        `Descarga Binaria PDF (${tipo})`,
        resPdf.status === 200 && contentType.includes('application/pdf') && esPdfValido,
        `HTTP ${resPdf.status} — ${bytes.length} bytes binarios recibidos, cabecera mágica %PDF verificada`
      );
    } catch (err) {
      registrarResultado('Reportes PDF', `Descarga Binaria PDF (${tipo})`, false, err.message);
    }
  }

  // RESUMEN FINAL
  const total = resultados.length;
  const aprobadas = resultados.filter((r) => r.exito).length;
  const fallidas = total - aprobadas;

  console.log('\n============================================================');
  console.log(`   RESUMEN FINAL: ${aprobadas} / ${total} PRUEBAS APROBADAS (${fallidas} fallos)`);
  console.log('============================================================\n');

  return fallidas === 0;
}

ejecutarPruebas()
  .then((exito) => {
    process.exit(exito ? 0 : 1);
  })
  .catch((err) => {
    console.error('Error fatal durante la ejecución:', err);
    process.exit(1);
  });
