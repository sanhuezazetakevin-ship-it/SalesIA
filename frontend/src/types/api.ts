export interface User {
  id: number;
  empresa_id: number;
  nombre: string;
  email: string;
  activo: boolean;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  usuario: User;
}

export interface MeResponse {
  id: number;
  empresa_id: number;
  nombre: string;
  email: string;
  activo: boolean;
}

export interface KPIComercial {
  cantidad_ventas: number;
  total_ventas: string;
  ticket_promedio: string | null;
}

export interface RankingItem {
  id: number;
  nombre: string;
  cantidad: number | string;
  total: string;
}

export interface DashboardComercialResponse {
  periodo: {
    fecha_inicio: string;
    fecha_fin: string;
  };
  periodo_anterior?: {
    fecha_inicio: string;
    fecha_fin: string;
  };
  moneda: string;
  zona_horaria: string;
  criterio_estado: string;
  kpis: KPIComercial;
  kpis_periodo_anterior?: KPIComercial | null;
  variacion_porcentual_ventas?: string | null;
  pedidos_por_estado?: Record<string, number>;
  productos_destacados?: RankingItem[];
  clientes_destacados?: RankingItem[];
  vendedores_destacados?: RankingItem[];
}

export interface SeriePunto {
  fecha: string;
  cantidad_ventas: number;
  total_ventas: string;
}

export interface SerieVentasResponse {
  fecha_inicio: string;
  fecha_fin: string;
  agrupacion: 'dia' | 'mes';
  criterio_estado: string;
  zona_horaria: string;
  moneda: string;
  puntos: SeriePunto[];
}

export interface AnalyticsResumenResponse {
  periodo: {
    fecha_inicio: string;
    fecha_fin: string;
  };
  moneda: string;
  criterio_estado: string;
  zona_horaria: string;
  cantidad_ventas: number;
  total_ventas: string;
  ticket_promedio: string | null;
  mediana_ventas: string | null;
}

export interface IntervaloDistribucion {
  categoria?: string | null;
  desde?: string | null;
  hasta?: string | null;
  limite_inferior?: string;
  limite_superior?: string;
  etiqueta?: string;
  frecuencia?: number;
  frecuencia_absoluta?: number;
  frecuencia_relativa?: string;
  porcentaje?: string;
}

export interface AnalyticsDistribucionesResponse {
  variable: string;
  tipo_variable?: string;
  total_observaciones: number;
  distribucion?: IntervaloDistribucion[];
  intervalos?: IntervaloDistribucion[];
  [key: string]: unknown;
}

export interface AnalyticsProbabilidadesResponse {
  total_observaciones: number;
  umbral_importe_alto: string;
  criterio_importe_alto: string;
  conteos: {
    importe_alto: number;
    pagado: number;
    importe_alto_y_pagado: number;
  };
  variable_aleatoria_estado_pago: Array<{
    estado: string;
    frecuencia_absoluta: number;
    probabilidad: string | null;
  }>;
  probabilidad_pagado: string | null;
  probabilidad_importe_alto: string | null;
  probabilidad_conjunta_alto_y_pagado: string | null;
  probabilidad_pagado_dado_alto: string | null;
  bayes_importe_alto_dado_pagado: string | null;
}

export interface ContrasteHipotesis {
  estado: string;
  metodo?: string;
  hipotesis_nula?: string;
  estadistico_t?: number;
  grados_libertad?: number;
  valor_p?: number;
  alfa?: number;
  rechazar_hipotesis_nula?: boolean;
  explicacion?: string;
  advertencia?: string;
}

export interface Semana08Resultados {
  cantidad: number;
  sin_datos: boolean;
  media: number | null;
  mediana: number | null;
  varianza_poblacional: number | null;
  desviacion_poblacional: number | null;
  varianza_muestral: number | null;
  desviacion_muestral: number | null;
  esperanza_empirica: number | null;
  histograma?: {
    tipo: string;
    titulo: string;
    etiquetas: string[];
    valores: number[];
    eje_x: string;
    eje_y: string;
  };
  contraste?: ContrasteHipotesis | null;
  explicacion?: string;
  advertencia?: string;
}

export interface Semana08Response {
  periodo?: { inicio: string; fin: string };
  moneda?: string;
  criterio?: string;
  zona_horaria?: string;
  metodologia?: string;
  resultados?: Semana08Resultados;
  distribucion_estados_pago?: {
    tipo: string;
    titulo: string;
    etiquetas: string[];
    valores: number[];
    unidad: string;
    sin_datos: boolean;
  };
  // Propiedades planas de respaldo
  cantidad?: number;
  sin_datos?: boolean;
  media?: number | null;
  mediana?: number | null;
  varianza_poblacional?: number | null;
  desviacion_poblacional?: number | null;
  varianza_muestral?: number | null;
  desviacion_muestral?: number | null;
  esperanza_empirica?: number | null;
  contraste?: ContrasteHipotesis | null;
  explicacion?: string;
  advertencia?: string;
}

export interface Cliente {
  id: number;
  empresa_id: number;
  nombre: string;
  tipo_documento?: string | null;
  numero_documento?: string | null;
  email?: string | null;
  telefono?: string | null;
  direccion?: string | null;
  activo: boolean;
  created_at: string;
}

export interface ClienteListadoResponse {
  total: number;
  pagina: number;
  limite: number;
  clientes: Cliente[];
}

export interface Producto {
  id: number;
  empresa_id: number;
  categoria_id?: number | null;
  sku: string;
  nombre: string;
  descripcion?: string | null;
  tipo_item: string;
  precio_venta: string | number;
  costo_referencia: string | number;
  controla_stock: boolean;
  activo: boolean;
  created_at: string;
}

export interface ProductoListadoResponse {
  total: number;
  pagina: number;
  limite: number;
  productos: Producto[];
}

export interface Venta {
  id: number;
  codigo: string;
  cliente_id?: number;
  total: string;
  estado: string;
  estado_pago: string;
  created_at: string;
}

export interface VentaListadoResponse {
  total: number;
  pagina: number;
  limite: number;
  ventas: Venta[];
}

export type ReporteTipo = 'VENTAS' | 'ESTADISTICO' | 'INVENTARIO' | 'CLIENTES' | 'RENDIMIENTO';
