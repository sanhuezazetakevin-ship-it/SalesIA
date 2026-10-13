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

export const api = {
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
