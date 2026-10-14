import {
  LoginResponse,
  MeResponse,
  DashboardComercialResponse,
  SerieVentasResponse,
  AnalyticsResumenResponse,
  AnalyticsDistribucionesResponse,
  AnalyticsProbabilidadesResponse,
  Semana08Response,
  ClienteListadoResponse,
  ProductoListadoResponse,
  VentaListadoResponse,
  ReporteTipo,
  UsuarioPendiente, InvitacionCreada, RegistroInvitacion, AprobacionUsuario, RolEmpresa, RolPermisos, ResultadoRol,
} from '../types/api';
import type { CatalogItem, PedidoResumen, VentaResumen, ResumenPagos, EntregaResumen } from '../types/commercial';

export interface InsightF7 {id:number;tipo_insight:string;prioridad:string;titulo:string;descripcion:string;recomendacion:string|null;estado:string;created_at:string;analisis_estadistico_id:number|null;analisis_probabilidad_id:number|null;datos_soporte:Record<string,unknown>|null}
export interface NotificacionF7 {id:number;codigo:string;titulo:string;descripcion:string;nivel:string;leida:boolean;created_at:string;leida_at:string|null}
export interface AnalisisF7 {id:number;tipo:string;estado:string;resultados:Record<string,unknown>;created_at:string|null}
export interface EventoAuditoriaF7 {id:number;usuario_id:number|null;accion:string;entidad:string;entidad_id:number|null;descripcion:string|null;origen:string;created_at:string}
export interface AuditoriaF7 {total:number;limite:number;desplazamiento:number;items:EventoAuditoriaF7[]}

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const TOKEN_KEY = 'salesia_access_token';
const REFRESH_KEY = 'salesia_refresh_token';
let refreshInProgress: Promise<string> | null = null;

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export const authStorage = {
  getToken: (): string | null => {
    return localStorage.getItem(TOKEN_KEY);
  },
  setToken: (token: string | null): void => {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  },
  clear: (): void => {
    localStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(REFRESH_KEY);
  },
  getRefreshToken: (): string | null => sessionStorage.getItem(REFRESH_KEY),
  setRefreshToken: (token: string): void => sessionStorage.setItem(REFRESH_KEY, token),
};

async function renewAccessToken(): Promise<string> {
  if (!refreshInProgress) {
    refreshInProgress = (async () => {
      const refreshToken = authStorage.getRefreshToken();
      if (!refreshToken) throw new ApiError(401, 'Sesión expirada. Inicia sesión de nuevo.');
      const response = await fetch(`${BASE_URL}/api/auth/refresh`, {
        method: 'POST',
        headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) throw new ApiError(response.status, 'No fue posible renovar la sesión.');
      const data: { access_token: string; refresh_token: string } = await response.json();
      authStorage.setToken(data.access_token);
      authStorage.setRefreshToken(data.refresh_token);
      return data.access_token;
    })().catch((error) => {
      authStorage.clear();
      throw error;
    }).finally(() => { refreshInProgress = null; });
  }
  return refreshInProgress;
}

async function request<T>(endpoint: string, options: RequestInit = {}, retry = true): Promise<T> {
  const token = authStorage.getToken();
  const headers: Record<string, string> = {
    'Accept': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (options.body && typeof options.body === 'string' && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : 'Error desconocido de red';
    throw new ApiError(0, `Fallo de conexión con el backend en ${BASE_URL}: ${errorMsg}`);
  }

  if (response.status === 401 && retry && endpoint !== '/api/auth/login' && endpoint !== '/api/auth/logout' && endpoint !== '/api/auth/register-invitation' && authStorage.getRefreshToken()) {
    const freshToken = await renewAccessToken();
    return request<T>(endpoint, { ...options, headers: { ...(options.headers as Record<string, string> || {}), Authorization: `Bearer ${freshToken}` } }, false);
  }

  if (!response.ok) {
    let errorDetail = `Error ${response.status}`;
    let errorBody: unknown = null;
    try {
      errorBody = await response.json();
      if (typeof errorBody === 'object' && errorBody !== null && 'detail' in errorBody) {
        const detail = (errorBody as { detail: unknown }).detail;
        if (typeof detail === 'string') {
          errorDetail = detail;
        } else if (Array.isArray(detail)) {
          errorDetail = detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join('; ');
        } else {
          errorDetail = JSON.stringify(detail);
        }
      }
    } catch {
      errorDetail = response.statusText || `HTTP ${response.status}`;
    }

    if (response.status === 401) {
      errorDetail = `[401 No autorizado]: ${errorDetail}`;
    } else if (response.status === 403) {
      errorDetail = `[403 Prohibido]: Permiso insuficiente o empresa bloqueada. ${errorDetail}`;
    } else if (response.status === 422) {
      errorDetail = `[422 Validación]: Parámetros o cuerpo no válidos. ${errorDetail}`;
    }

    throw new ApiError(response.status, errorDetail, errorBody);
  }

  return response.json() as Promise<T>;
}

export interface ReportePreviewF8 { tipo: string; fecha_inicio:string; fecha_fin:string; columnas:string[]; total_filas:number; filas:Array<Array<string | number | boolean | null>>; moneda:string; zona_horaria:string }
export interface ReporteHistorialF8 { id:number; nombre:string; tipo:string; formato:string; estado:string; tamano_bytes:number|null; created_at:string }
export interface ReporteGeneradoF8 { id:number; tipo:string; formato:string; estado:string; tamano_bytes:number|null }

async function descargarBinarioF8(endpoint:string, nombre:string):Promise<void> {
  let token = authStorage.getToken();
  const get = (t:string|null) => fetch(`${BASE_URL}${endpoint}`, { headers: { ...(t ? {Authorization:`Bearer ${t}`} : {}), Accept:'application/octet-stream,application/pdf,*/*' } });
  let response = await get(token);
  if (response.status===401 && authStorage.getRefreshToken()) {
    token = await renewAccessToken();
    response = await get(token);
  }
  if (!response.ok) {
    let detalle = `HTTP ${response.status}`;
    try { const body = await response.json(); detalle = typeof body.detail==='string' ? body.detail : detalle; } catch { /* respuesta no JSON */ }
    throw new ApiError(response.status, detalle);
  }
  const file = await response.blob();
  if (file.size===0) throw new Error('El archivo recibido está vacío.');
  const url = URL.createObjectURL(file);
  const anchor = document.createElement('a');
  anchor.href=url; anchor.download=nombre;
  document.body.appendChild(anchor); anchor.click(); anchor.remove();
  window.setTimeout(()=>URL.revokeObjectURL(url), 1000);
}

export const api = {
  previsualizarReporteF8: (tipo:ReporteTipo, inicio:string, fin:string, limite=100):Promise<ReportePreviewF8> =>
    request(`/api/reportes/previsualizar?tipo=${tipo}&fecha_inicio=${inicio}&fecha_fin=${fin}&limite=${limite}`),
  historialReportesF8: (limite=100):Promise<{items:ReporteHistorialF8[]}> =>
    request(`/api/reportes?limite=${limite}`),
  generarReporteF8: (tipo:ReporteTipo, formato:'CSV'|'XLSX'|'PDF', inicio:string, fin:string):Promise<ReporteGeneradoF8> =>
    request(`/api/reportes/generar?tipo=${tipo}&formato=${formato}&fecha_inicio=${inicio}&fecha_fin=${fin}`, {method:'POST'}),
  descargarReporteGuardadoF8: (id:number, formato:string):Promise<void> =>
    descargarBinarioF8(`/api/reportes/${id}/descargar`, `SalesIA_reporte_${id}.${formato.toLowerCase()}`),

  login: async (email: string, password: string): Promise<LoginResponse> => {
    const data = await request<LoginResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    if (data.access_token) authStorage.setToken(data.access_token);
    if (data.refresh_token) authStorage.setRefreshToken(data.refresh_token);
    return data;
  },

  // Prueba aislada de 401: nunca altera los tokens de la sesión actual.
  testUnauthorized: async (): Promise<number> => {
    const response = await fetch(`${BASE_URL}/api/auth/me`, {
      headers: { Accept: 'application/json' },
    });
    return response.status;
  },

  getMe: async (): Promise<MeResponse> => {
    return request<MeResponse>('/api/auth/me');
  },

  logout: async (): Promise<void> => {
    try {
      await request('/api/auth/logout', { method: 'POST' });
    } catch {
      // Ignorar fallo de red al desloguearse
    } finally {
      authStorage.clear();
    }
  },

  // Administracion de usuarios / RBAC: endpoints reales del backend.
  listarUsuariosPendientes: (): Promise<UsuarioPendiente[]> => request('/api/usuarios/pendientes'),
  crearInvitacion: (email: string): Promise<InvitacionCreada> =>
    request('/api/invitaciones', { method: 'POST', body: JSON.stringify({ email }) }),
  registrarInvitado: (datos: { token: string; nombre: string; email: string; password: string }): Promise<RegistroInvitacion> =>
    request('/api/auth/register-invitation', { method: 'POST', body: JSON.stringify(datos) }),
  aprobarUsuario: (usuarioId: number): Promise<AprobacionUsuario> =>
    request(`/api/usuarios/${usuarioId}/aprobar`, { method: 'POST' }),
  listarRoles: (): Promise<RolEmpresa[]> => request('/api/roles'),
  listarPermisosRol: (rolId: number): Promise<RolPermisos> => request(`/api/roles/${rolId}/permisos`),
  asignarRol: (usuarioId: number, rolId: number): Promise<ResultadoRol> =>
    request('/api/roles/asignaciones', { method: 'POST', body: JSON.stringify({ usuario_id: usuarioId, rol_id: rolId }) }),
  revocarRol: (usuarioId: number, rolId: number): Promise<ResultadoRol> =>
    request('/api/roles/asignaciones', { method: 'DELETE', body: JSON.stringify({ usuario_id: usuarioId, rol_id: rolId }) }),

  // Fase 3: contratos comerciales validados frente al backend.
  listarCategorias: (): Promise<{categorias: CatalogItem[];total:number}> => request('/api/categorias?pagina=1&limite=100'),
  crearCategoria: (datos: {nombre:string;descripcion?:string}): Promise<CatalogItem> => request('/api/categorias',{method:'POST',body:JSON.stringify(datos)}),
  actualizarCategoria: (id:number, datos: Record<string,unknown>): Promise<CatalogItem> => request(`/api/categorias/${id}`,{method:'PATCH',body:JSON.stringify(datos)}),
  desactivarCategoria: (id:number): Promise<CatalogItem> => request(`/api/categorias/${id}`,{method:'DELETE'}),
  crearCliente: (datos: Record<string,unknown>): Promise<CatalogItem> => request('/api/clientes',{method:'POST',body:JSON.stringify(datos)}),
  actualizarCliente: (id:number, datos: Record<string,unknown>): Promise<CatalogItem> => request(`/api/clientes/${id}`,{method:'PATCH',body:JSON.stringify(datos)}),
  desactivarCliente: (id:number): Promise<CatalogItem> => request(`/api/clientes/${id}`,{method:'DELETE'}),
  crearProducto: (datos: Record<string,unknown>): Promise<CatalogItem> => request('/api/productos',{method:'POST',body:JSON.stringify(datos)}),
  actualizarProducto: (id:number, datos: Record<string,unknown>): Promise<CatalogItem> => request(`/api/productos/${id}`,{method:'PATCH',body:JSON.stringify(datos)}),
  desactivarProducto: (id:number): Promise<CatalogItem> => request(`/api/productos/${id}`,{method:'DELETE'}),
  consultarIgv: (): Promise<{id:number;codigo:string;nombre:string;tasa:string;activo:boolean;incluido_en_precio:boolean}|null> => request('/api/configuracion/tributaria/igv'),
  actualizarIgv: (tasa:string): Promise<{id:number;tasa:string}> => request('/api/configuracion/tributaria/igv',{method:'PUT',body:JSON.stringify({tasa})}),
  listarPedidos: (): Promise<{pedidos: PedidoResumen[];total:number}> => request('/api/pedidos?pagina=1&limite=100'),
  obtenerPedido: (id:number): Promise<PedidoResumen & {detalles: unknown[]}> => request(`/api/pedidos/${id}`),
  crearPedido: (datos: {cliente_id:number;detalles:{producto_id:number;cantidad:string;descuento:string}[];observaciones?:string}): Promise<PedidoResumen> => request('/api/pedidos',{method:'POST',body:JSON.stringify(datos)}),
  confirmarPedido: (id:number): Promise<PedidoResumen> => request(`/api/pedidos/${id}/confirmar`,{method:'POST'}),
  cancelarPedido: (id:number): Promise<PedidoResumen> => request(`/api/pedidos/${id}/cancelar`,{method:'POST'}),
  crearVentaDesdePedido: (id:number): Promise<VentaResumen> => request(`/api/ventas/desde-pedido/${id}`,{method:'POST',body:JSON.stringify({})}),
  obtenerVenta: (id:number): Promise<VentaResumen & {detalles:unknown[]}> => request(`/api/ventas/${id}`),
  registrarPago: (id:number, datos:{monto:string;medio_pago:string;referencia_externa?:string}, clave:string): Promise<{id:number;codigo:string;estado:string}> => request(`/api/pagos/ventas/${id}`,{method:'POST',headers:{'Idempotency-Key':clave},body:JSON.stringify(datos)}),
  resumenPagos: (id:number): Promise<ResumenPagos> => request(`/api/pagos/ventas/${id}/resumen`),
  anularPago: (id:number,motivo:string): Promise<{id:number;estado:string}> => request(`/api/pagos/${id}/anular`,{method:'POST',body:JSON.stringify({motivo})}),
  obtenerEntregaVenta: (id:number): Promise<EntregaResumen> => request(`/api/entregas/ventas/${id}`),
  confirmarEntrega: (id:number): Promise<EntregaResumen> => request(`/api/entregas/ventas/${id}/confirmar`,{method:'POST',body:JSON.stringify({})}),

  listarCategoriasPagina: (pagina = 1, limite = 20, busqueda = ''): Promise<{categorias:{id:number;nombre:string;descripcion?:string|null;activo:boolean}[];total:number}> =>
    request(`/api/categorias?pagina=${pagina}&limite=${limite}${busqueda.trim()?`&busqueda=${encodeURIComponent(busqueda.trim())}`:''}`),
  getInventarioVisual: (inicio:string,fin:string): Promise<{items:{producto_id:number;nombre:string;[key:string]:unknown}[]}> =>
    request(`/api/mejoras/inventario?fecha_inicio=${inicio}&fecha_fin=${fin}&limite=100`),
  getClientesVisual: (inicio:string,fin:string): Promise<{items:{cliente_id:number;nombre:string;segmento?:string;[key:string]:unknown}[]}> =>
    request(`/api/mejoras/clientes?fecha_inicio=${inicio}&fecha_fin=${fin}&limite=100`),

  getDashboardComercial: async (
    fechaInicio: string,
    fechaFin: string,
    limite: number = 10
  ): Promise<DashboardComercialResponse> => {
    return request<DashboardComercialResponse>(
      `/api/dashboard/comercial?fecha_inicio=${fechaInicio}&fecha_fin=${fechaFin}&limite=${limite}`
    );
  },

  getSerieVentas: async (
    fechaInicio: string,
    fechaFin: string,
    agrupacion: 'dia' | 'mes' = 'dia'
  ): Promise<SerieVentasResponse> => {
    return request<SerieVentasResponse>(
      `/api/dashboard/ventas/serie?fecha_inicio=${fechaInicio}&fecha_fin=${fechaFin}&agrupacion=${agrupacion}`
    );
  },

  getAnalyticsResumen: async (
    fechaInicio: string,
    fechaFin: string
  ): Promise<AnalyticsResumenResponse> => {
    return request<AnalyticsResumenResponse>(
      `/api/analytics/resumen?fecha_inicio=${fechaInicio}&fecha_fin=${fechaFin}`
    );
  },

  getAnalyticsDistribuciones: async (
    fechaInicio: string,
    fechaFin: string,
    variable: 'importe_venta' | 'estado_pago' = 'importe_venta',
    intervalos: number = 5
  ): Promise<AnalyticsDistribucionesResponse> => {
    return request<AnalyticsDistribucionesResponse>(
      `/api/analytics/distribuciones?fecha_inicio=${fechaInicio}&fecha_fin=${fechaFin}&variable=${variable}&intervalos=${intervalos}`
    );
  },

  getAnalyticsProbabilidades: async (
    fechaInicio: string,
    fechaFin: string,
    umbralImporte: string = '100.00'
  ): Promise<AnalyticsProbabilidadesResponse> => {
    return request<AnalyticsProbabilidadesResponse>(
      `/api/analytics/probabilidades?fecha_inicio=${fechaInicio}&fecha_fin=${fechaFin}&umbral_importe=${umbralImporte}`
    );
  },

  getSemana08: async (
    fechaInicio: string,
    fechaFin: string,
    mediaHipotetica?: number,
    alfa: number = 0.05
  ): Promise<Semana08Response> => {
    let url = `/api/analytics/semana08?fecha_inicio=${fechaInicio}&fecha_fin=${fechaFin}&alfa=${alfa}`;
    if (mediaHipotetica !== undefined && !isNaN(mediaHipotetica)) {
      url += `&media_hipotetica=${mediaHipotetica}`;
    }
    return request<Semana08Response>(url);
  },

  getProveedores: (pagina=1,limite=20,busqueda=''):Promise<{items:import('../components/PurchasesView').Proveedor[];total:number;pagina:number;limite:number}> => request(`/api/proveedores?pagina=${pagina}&limite=${limite}&busqueda=${encodeURIComponent(busqueda)}`),
  crearProveedor: (datos:Record<string,unknown>):Promise<unknown> => request('/api/proveedores',{method:'POST',body:JSON.stringify(datos)}),
  editarProveedor: (id:number,datos:Record<string,unknown>):Promise<unknown> => request(`/api/proveedores/${id}`,{method:'PATCH',body:JSON.stringify(datos)}),
  desactivarProveedor: (id:number):Promise<unknown> => request(`/api/proveedores/${id}/desactivar`,{method:'POST'}),
  getOrdenesCompra: (pagina=1,limite=100):Promise<{items:import('../components/PurchasesView').Orden[];total:number}> => request(`/api/compras/ordenes?pagina=${pagina}&limite=${limite}`),
  crearOrdenCompra: (datos:unknown):Promise<unknown> => request('/api/compras/ordenes',{method:'POST',body:JSON.stringify(datos)}),
  confirmarOrdenCompra: (id:number):Promise<unknown> => request(`/api/compras/ordenes/${id}/confirmar`,{method:'POST'}),
  cancelarOrdenCompra: (id:number):Promise<unknown> => request(`/api/compras/ordenes/${id}/cancelar`,{method:'POST'}),
  getRecepcionesCompra: (pagina=1,limite=100):Promise<{items:import('../components/PurchasesView').Recepcion[];total:number}> => request(`/api/compras/recepciones?pagina=${pagina}&limite=${limite}`),
  crearRecepcionCompra: (datos:unknown):Promise<unknown> => request('/api/compras/recepciones',{method:'POST',body:JSON.stringify(datos)}),
  getPagosProveedor: (pagina=1,limite=100):Promise<{items:import('../components/PurchasesView').Pago[];total:number}> => request(`/api/compras/pagos?pagina=${pagina}&limite=${limite}`),
  crearPagoProveedor: (datos:unknown):Promise<unknown> => request('/api/compras/pagos',{method:'POST',body:JSON.stringify(datos)}),
  anularPagoProveedor: (id:number):Promise<unknown> => request(`/api/compras/pagos/${id}/anular`,{method:'POST'}),

  getClientes: async (
    pagina: number = 1,
    limite: number = 20,
    busqueda?: string
  ): Promise<ClienteListadoResponse> => {
    let url = `/api/clientes?pagina=${pagina}&limite=${limite}`;
    if (busqueda && busqueda.trim()) {
      url += `&busqueda=${encodeURIComponent(busqueda.trim())}`;
    }
    return request<ClienteListadoResponse>(url);
  },

  getProductos: async (
    pagina: number = 1,
    limite: number = 20,
    busqueda?: string
  ): Promise<ProductoListadoResponse> => {
    let url = `/api/productos?pagina=${pagina}&limite=${limite}`;
    if (busqueda && busqueda.trim()) {
      url += `&busqueda=${encodeURIComponent(busqueda.trim())}`;
    }
    return request<ProductoListadoResponse>(url);
  },

  getVentas: async (
    pagina: number = 1,
    limite: number = 20
  ): Promise<VentaListadoResponse> => {
    return request<VentaListadoResponse>(`/api/ventas?pagina=${pagina}&limite=${limite}`);
  },

  // Fase 7: insights, notificaciones, historial de analisis y auditoria.
  listarInsights: (limite = 50): Promise<{items: InsightF7[];limite:number}> =>
    request(`/api/insights?limite=${limite}`),
  generarInsights: (tipo: 'estadistico'|'probabilidad', analisisId: number): Promise<InsightF7[]> =>
    request('/api/insights/generar', {method:'POST',body:JSON.stringify({tipo,analisis_id:analisisId})}),
  actualizarInsight: (id: number, estado: 'REVISADO'|'DESCARTADO'): Promise<InsightF7> =>
    request(`/api/insights/${id}/estado`,{method:'PATCH',body:JSON.stringify({estado})}),
  listarNotificaciones: (soloNoLeidas=false): Promise<{items: NotificacionF7[];total_mostrado:number}> =>
    request(`/api/mejoras/notificaciones-persistentes?limite=100&solo_no_leidas=${soloNoLeidas}`),
  sincronizarNotificaciones: (inicio:string,fin:string):Promise<{nuevas:number;detectadas:number;explicacion:string}> =>
    request(`/api/mejoras/notificaciones-persistentes/sincronizar?fecha_inicio=${inicio}&fecha_fin=${fin}`,{method:'POST'}),
  marcarNotificacionLeida: (id:number):Promise<NotificacionF7> =>
    request(`/api/mejoras/notificaciones-persistentes/${id}/leida`,{method:'PATCH'}),
  listarHistorialAnalisis: (tipo:'estadistico'|'probabilidad'):Promise<{items:AnalisisF7[];tipo:string}> =>
    request(`/api/analytics/historial?tipo=${tipo}&limite=50`),
  crearAnalisisEstadistico: (inicio:string,fin:string,nombre:string):Promise<AnalisisF7> =>
    request('/api/analytics/historial/estadisticos',{method:'POST',body:JSON.stringify({fecha_inicio:inicio,fecha_fin:fin,nombre})}),
  crearAnalisisProbabilidad: (inicio:string,fin:string,umbral:string):Promise<AnalisisF7> =>
    request('/api/analytics/historial/probabilidades',{method:'POST',body:JSON.stringify({fecha_inicio:inicio,fecha_fin:fin,umbral_importe:umbral})}),
  listarAuditoria: (desplazamiento=0,limite=25,accion=''):Promise<AuditoriaF7> =>
    request(`/api/auditoria?desplazamiento=${desplazamiento}&limite=${limite}${accion?`&accion=${encodeURIComponent(accion)}`:''}`),

  // Cierre funcional: inventario y vendedores. Paginación real desde FastAPI.
  listarVendedoresOperativos: (pagina=1,limite=20,busqueda=''):Promise<{total:number;pagina:number;limite:number;items:{id:number;nombre:string;email:string;activo:boolean}[]}> =>
    request(`/api/vendedores-operativos?pagina=${pagina}&limite=${limite}&busqueda=${encodeURIComponent(busqueda)}`),
  listarInventarioOperativo: (pagina=1,limite=20,busqueda=''):Promise<{total:number;pagina:number;limite:number;items:{inventario_id:number|null;producto_id:number;producto:string;sku:string;cantidad_disponible:string}[]}> =>
    request(`/api/inventario-operativo?pagina=${pagina}&limite=${limite}&busqueda=${encodeURIComponent(busqueda)}`),
  listarMovimientosOperativos: (pagina=1,limite=20):Promise<{total:number;pagina:number;limite:number;items:{id:number;producto_id:number;tipo:string;cantidad_delta:string;motivo:string;referencia:string|null;fecha:string}[]}> =>
    request(`/api/inventario-operativo/movimientos?pagina=${pagina}&limite=${limite}`),
  ajustarInventario: (datos:{producto_id:number;cantidad_delta:string;motivo:string;referencia?:string}):Promise<{producto_id:number;stock_anterior:string;stock_actual:string;delta:string}> =>
    request('/api/inventario-operativo/ajustes',{method:'POST',body:JSON.stringify(datos)}),

  descargarReportePdf: async (
    tipo: ReporteTipo,
    fechaInicio: string,
    fechaFin: string
  ): Promise<void> => {
    const token = authStorage.getToken();
    const url = `${BASE_URL}/api/reportes/pdf-directo?tipo=${tipo}&fecha_inicio=${fechaInicio}&fecha_fin=${fechaFin}`;

    const headers: Record<string, string> = {
      'Accept': 'application/pdf',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, { headers });

    if (!response.ok) {
      let errText = `HTTP ${response.status}`;
      try {
        const json = await response.json();
        errText = json.detail || JSON.stringify(json);
      } catch {
        errText = response.statusText;
      }
      throw new ApiError(response.status, `Fallo al descargar PDF: ${errText}`);
    }

    const contentType = response.headers.get('content-type') || '';
    if (!contentType.includes('application/pdf')) {
      throw new ApiError(500, `Respuesta no es PDF: content-type recibido es ${contentType}`);
    }

    const blob = await response.blob();
    const blobUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = `reporte_${tipo.toLowerCase()}_${fechaInicio}_${fechaFin}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(blobUrl);
  },
};
