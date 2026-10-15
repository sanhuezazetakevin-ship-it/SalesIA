import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import {
  BarChart3,
  TrendingUp,
  Percent,
  Activity,
  Calendar,
  RefreshCw,
  AlertCircle,
  HelpCircle,
  Sparkles,
  Calculator,
  ArrowRight,
  ShieldCheck,
  Sigma,
} from 'lucide-react';
import { api } from '../services/api';
import {
  AnalyticsResumenResponse,
  AnalyticsDistribucionesResponse,
  AnalyticsProbabilidadesResponse,
  Semana08Response,
} from '../types/api';
import { GlassCard } from './ui/GlassCard';
import { Button } from './ui/Button';

const money = (value: string | number | null | undefined) => {
  const n = Number(value);
  return value === null || value === undefined || !Number.isFinite(n)
    ? 'Sin datos'
    : new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN', maximumFractionDigits: 2 }).format(n);
};

const percentage = (value: string | number | null | undefined) => {
  const n = Number(value);
  return value === null || value === undefined || !Number.isFinite(n) ? 'Sin datos' : `${(n * 100).toFixed(1)}%`;
};

// Custom Tooltip for Recharts
interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ name: string; value: number | string; color?: string }>;
  label?: string;
  unit?: string;
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload, label, unit = '' }) => {
  if (active && payload && payload.length) {
    return (
      <div className="backdrop-blur-xl bg-slate-900/90 dark:bg-[#12121A]/95 p-3 rounded-lg border border-gray-700/50 dark:border-white/10 shadow-xl text-xs space-y-1.5 z-50">
        <p className="font-semibold text-gray-200 border-b border-white/10 pb-1">{label}</p>
        {payload.map((entry, index) => (
          <div key={`item-${index}`} className="flex items-center justify-between gap-4 text-gray-300">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color || '#06b6d4' }} />
              {entry.name}:
            </span>
            <span className="font-mono font-bold text-white">
              {typeof entry.value === 'number' ? entry.value.toLocaleString('es-PE') : entry.value}
              {unit}
            </span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export const AnalyticsView: React.FC = () => {
  const hoy = new Date().toISOString().split('T')[0];
  const haceUnMes = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

  const [fechaInicio, setFechaInicio] = useState(haceUnMes);
  const [fechaFin, setFechaFin] = useState(hoy);
  const [activeSubTab, setActiveSubTab] = useState<'resumen' | 'distribuciones' | 'probabilidades' | 'semana08'>('resumen');

  // Filtros específicos
  const [variableDist, setVariableDist] = useState<'importe_venta' | 'estado_pago'>('importe_venta');
  const [intervalos, setIntervalos] = useState(5);
  const [umbralImporte, setUmbralImporte] = useState('100.00');
  const [mediaHipotetica, setMediaHipotetica] = useState(150);
  const [alfa, setAlfa] = useState(0.05);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [resumen, setResumen] = useState<AnalyticsResumenResponse | null>(null);
  const [distribucion, setDistribucion] = useState<AnalyticsDistribucionesResponse | null>(null);
  const [probabilidades, setProbabilidades] = useState<AnalyticsProbabilidadesResponse | null>(null);
  const [semana08, setSemana08] = useState<Semana08Response | null>(null);

  const consultarAnalytics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (activeSubTab === 'resumen') {
        const resp = await api.getAnalyticsResumen(fechaInicio, fechaFin);
        setResumen(resp);
        const [dist, probs] = await Promise.allSettled([
          api.getAnalyticsDistribuciones(fechaInicio, fechaFin, 'importe_venta', 6),
          api.getAnalyticsProbabilidades(fechaInicio, fechaFin, umbralImporte),
        ]);
        setDistribucion(dist.status === 'fulfilled' ? dist.value : null);
        setProbabilidades(probs.status === 'fulfilled' ? probs.value : null);
      } else if (activeSubTab === 'distribuciones') {
        const resp = await api.getAnalyticsDistribuciones(fechaInicio, fechaFin, variableDist, intervalos);
        setDistribucion(resp);
      } else if (activeSubTab === 'probabilidades') {
        const resp = await api.getAnalyticsProbabilidades(fechaInicio, fechaFin, umbralImporte);
        setProbabilidades(resp);
      } else if (activeSubTab === 'semana08') {
        const resp = await api.getSemana08(fechaInicio, fechaFin, mediaHipotetica, alfa);
        setSemana08(resp);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error al consultar analytics';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [activeSubTab, fechaInicio, fechaFin, variableDist, intervalos, umbralImporte, mediaHipotetica, alfa]);

  useEffect(() => {
    consultarAnalytics();
  }, [consultarAnalytics]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="space-y-6"
    >
      {/* Header section */}
      <div className="glass p-5 md:p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4 border border-[#D97843]/20 dark:border-white/10 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-extrabold uppercase tracking-wider bg-slate-200/80 dark:bg-white/15 text-slate-800 dark:text-slate-200">
              INTELIGENCIA EMPRESARIAL / ANÁLISIS
            </span>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/15 text-emerald-800 dark:text-emerald-300 border border-emerald-500/30">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              PostgreSQL Live
            </span>
          </div>
          <h2 className="text-2xl md:text-3xl font-black tracking-tight text-slate-950 dark:text-white mt-1.5 flex items-center gap-2.5 drop-shadow-sm">
            <BarChart3 className="h-7 w-7 text-[#D97843] dark:text-[#FFA675]" />
            Centro de Analítica y Modelado Estadístico
          </h2>
          <p className="text-sm text-slate-700 dark:text-slate-200 font-medium mt-1">
            Indicadores descriptivos, frecuencias continuas y probabilidades bayesianas computadas sobre transacciones reales.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={consultarAnalytics}
          disabled={loading}
          icon={<RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin text-cyan-500' : ''}`} />}
        >
          {loading ? 'Calculando...' : 'Actualizar'}
        </Button>
      </div>

      {/* Date Range Selector Card */}
      <GlassCard className="p-4">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-end gap-4">
          <div className="flex-1">
            <label className="input-label flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5 text-cyan-500" />
              Fecha Inicio
            </label>
            <input
              type="date"
              className="input-field"
              value={fechaInicio}
              onChange={(e) => setFechaInicio(e.target.value)}
            />
          </div>
          <div className="flex-1">
            <label className="input-label flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5 text-cyan-500" />
              Fecha Fin
            </label>
            <input
              type="date"
              className="input-field"
              value={fechaFin}
              onChange={(e) => setFechaFin(e.target.value)}
            />
          </div>
          <Button
            variant="primary"
            onClick={consultarAnalytics}
            disabled={loading}
            className="sm:w-auto"
            icon={<Activity className="h-4 w-4" />}
          >
            {loading ? 'Calculando...' : 'Filtrar Periodo'}
          </Button>
        </div>
      </GlassCard>

      {/* Navigation SubTabs */}
      <div className="tab-bar overflow-x-auto p-1.5 glass">
        <button
          type="button"
          className={`tab-item flex items-center gap-2 ${activeSubTab === 'resumen' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('resumen')}
        >
          <TrendingUp className={`h-4 w-4 ${activeSubTab === 'resumen' ? 'text-cyan-500' : 'text-gray-400'}`} />
          <span>A. Media & Mediana</span>
        </button>
        <button
          type="button"
          className={`tab-item flex items-center gap-2 ${activeSubTab === 'distribuciones' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('distribuciones')}
        >
          <BarChart3 className={`h-4 w-4 ${activeSubTab === 'distribuciones' ? 'text-cyan-500' : 'text-gray-400'}`} />
          <span>B. Distribuciones & Frecuencias</span>
        </button>
        <button
          type="button"
          className={`tab-item flex items-center gap-2 ${activeSubTab === 'probabilidades' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('probabilidades')}
        >
          <Percent className={`h-4 w-4 ${activeSubTab === 'probabilidades' ? 'text-cyan-500' : 'text-gray-400'}`} />
          <span>C. Probabilidades & Bayes</span>
        </button>
        <button
          type="button"
          className={`tab-item flex items-center gap-2 ${activeSubTab === 'semana08' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('semana08')}
        >
          <Sigma className={`h-4 w-4 ${activeSubTab === 'semana08' ? 'text-cyan-500' : 'text-gray-400'}`} />
          <span>D. Semana 08: Dispersión & Hipótesis</span>
        </button>
      </div>

      {/* Error message */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="alert-card alert-error"
            role="alert"
          >
            <AlertCircle className="h-5 w-5 shrink-0" />
            <div>
              <p className="font-medium">Ocurrió un inconveniente al computar los análisis</p>
              <p className="text-xs mt-0.5 opacity-90">{error}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* SubTab A: Resumen (Media / Mediana) */}
      {activeSubTab === 'resumen' && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="space-y-6"
        >
          {resumen && (
            <>
              {/* Stat Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <GlassCard hover className="p-5 flex flex-col justify-between border-l-4 border-l-cyan-500">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                      Total Ventas Confirmadas
                    </span>
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                      CUANTITATIVA
                    </span>
                  </div>
                  <div className="mt-3">
                    <div className="text-2xl font-bold font-mono text-right text-slate-900 dark:text-white">
                      {money(resumen.total_ventas)}
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 text-right">
                      {resumen.cantidad_ventas} transacciones analizadas
                    </p>
                  </div>
                </GlassCard>

                <GlassCard hover className="p-5 flex flex-col justify-between border-l-4 border-l-blue-500">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                      Media Aritmética (Ticket Promedio)
                    </span>
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                      CUANTITATIVA
                    </span>
                  </div>
                  <div className="mt-3">
                    <div className="text-2xl font-bold font-mono text-right text-cyan-600 dark:text-cyan-400">
                      {money(resumen.ticket_promedio)}
                    </div>
                    <p className="text-xs font-mono text-gray-500 dark:text-gray-400 mt-1 text-right">
                      x̄ = (∑ xᵢ) / n
                    </p>
                  </div>
                </GlassCard>

                <GlassCard hover className="p-5 flex flex-col justify-between border-l-4 border-l-indigo-500">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                      Mediana de Ventas
                    </span>
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                      CUANTITATIVA
                    </span>
                  </div>
                  <div className="mt-3">
                    <div className="text-2xl font-bold font-mono text-right text-slate-900 dark:text-white">
                      {money(resumen.mediana_ventas)}
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 text-right">
                      Corte central 50% (libre de atípicos)
                    </p>
                  </div>
                </GlassCard>
              </div>

              {/* Visual Grid: ComposedChart with Recharts */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <GlassCard className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                        <BarChart3 className="h-5 w-5 text-cyan-500" />
                        Distribución de Importes (Histograma)
                      </h3>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Frecuencia y tendencia porcentual calculadas por intervalos
                      </p>
                    </div>
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                      CUANTITATIVA CONTINUA
                    </span>
                  </div>

                  {distribucion && (distribucion.distribucion?.length || distribucion.intervalos?.length) ? (
                    <div className="h-72 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart
                          data={(distribucion.distribucion || distribucion.intervalos || []).map((d, i) => ({
                            name: d.etiqueta || d.categoria || (d.desde != null && d.hasta != null ? `${d.desde} - ${d.hasta}` : `Int ${i + 1}`),
                            frecuencia: d.frecuencia_absoluta ?? d.frecuencia ?? 0,
                            porcentaje: d.porcentaje ? parseFloat(d.porcentaje) : (d.frecuencia_relativa ? parseFloat(d.frecuencia_relativa) * 100 : 0),
                          }))}
                          margin={{ top: 10, right: 10, left: -20, bottom: 20 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                          <XAxis
                            dataKey="name"
                            tick={{ fill: '#94a3b8', fontSize: 10 }}
                            interval={0}
                            angle={-25}
                            textAnchor="end"
                          />
                          <YAxis yAxisId="left" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                          <YAxis yAxisId="right" orientation="right" tick={{ fill: '#94a3b8', fontSize: 11 }} unit="%" />
                          <Tooltip content={<CustomTooltip unit="" />} />
                          <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                          <Bar
                            yAxisId="left"
                            dataKey="frecuencia"
                            name="Frecuencia (Ventas)"
                            fill="#06b6d4"
                            radius={[4, 4, 0, 0]}
                          />
                          <Line
                            yAxisId="right"
                            type="monotone"
                            dataKey="porcentaje"
                            name="Porcentaje (%)"
                            stroke="#3b82f6"
                            strokeWidth={2}
                            dot={{ r: 4, fill: '#3b82f6' }}
                          />
                        </ComposedChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <div className="h-72 flex flex-col items-center justify-center text-center p-4 text-gray-500">
                      <HelpCircle className="h-8 w-8 text-gray-400 mb-2 opacity-50" />
                      <p className="text-sm">No hay observaciones suficientes en este periodo para generar el histograma.</p>
                    </div>
                  )}
                </GlassCard>

                {/* State / Probability Chart */}
                <GlassCard className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                        <Activity className="h-5 w-5 text-blue-500" />
                        Participación y Cobranzas
                      </h3>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Volumen comparativo de ventas pagadas vs totales
                      </p>
                    </div>
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                      CUALITATIVA NOMINAL
                    </span>
                  </div>

                  {probabilidades ? (
                    <div className="space-y-4">
                      <div className="h-56 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <ComposedChart
                            data={[
                              {
                                categoria: 'Total Ventas',
                                cantidad: probabilidades.total_observaciones,
                              },
                              {
                                categoria: 'Pagadas',
                                cantidad: probabilidades.conteos.pagado,
                              },
                              {
                                categoria: 'Ticket Alto',
                                cantidad: probabilidades.conteos.importe_alto,
                              },
                              {
                                categoria: 'Alto y Pagado',
                                cantidad: probabilidades.conteos.importe_alto_y_pagado,
                              },
                            ]}
                            margin={{ top: 10, right: 10, left: -20, bottom: 5 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                            <XAxis dataKey="categoria" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                            <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
                            <Tooltip content={<CustomTooltip />} />
                            <Bar dataKey="cantidad" name="Operaciones" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                          </ComposedChart>
                        </ResponsiveContainer>
                      </div>

                      <div className="grid grid-cols-2 gap-3 pt-2">
                        <div className="p-3 rounded-lg bg-gray-50 dark:bg-white/5 border border-gray-200/50 dark:border-white/5">
                          <span className="text-[11px] text-gray-500 dark:text-gray-400 block">Tasa de cobranza</span>
                          <span className="text-lg font-bold font-mono text-slate-900 dark:text-white">
                            {percentage(probabilidades.probabilidad_pagado)}
                          </span>
                        </div>
                        <div className="p-3 rounded-lg bg-gray-50 dark:bg-white/5 border border-gray-200/50 dark:border-white/5">
                          <span className="text-[11px] text-gray-500 dark:text-gray-400 block">Tickets Altos (&gt;={probabilidades.umbral_importe_alto})</span>
                          <span className="text-lg font-bold font-mono text-slate-900 dark:text-white">
                            {percentage(probabilidades.probabilidad_importe_alto)}
                          </span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="h-72 flex flex-col items-center justify-center text-center p-4 text-gray-500">
                      <HelpCircle className="h-8 w-8 text-gray-400 mb-2 opacity-50" />
                      <p className="text-sm">Sin observaciones de cobro en el periodo seleccionado.</p>
                    </div>
                  )}
                </GlassCard>
              </div>

              {/* Analytical Data Table with data-table class */}
              <GlassCard className="p-6 overflow-hidden">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                    <Calculator className="h-5 w-5 text-cyan-500" />
                    Tabla de Métricas Descriptivas Centrales
                  </h3>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    Cálculos exactos sobre muestra N={resumen.cantidad_ventas}
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Métrica Estadística</th>
                        <th>Tipo de Variable</th>
                        <th>Fórmula / Procedimiento</th>
                        <th className="text-right">Valor Muestral</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td className="font-medium text-slate-900 dark:text-white">Total Facturado Acumulado</td>
                        <td>
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                            CUANTITATIVA
                          </span>
                        </td>
                        <td className="text-xs text-gray-500 dark:text-gray-400">∑ xᵢ de ventas en estado completado</td>
                        <td className="text-right font-mono font-semibold text-slate-900 dark:text-white">
                          {money(resumen.total_ventas)}
                        </td>
                      </tr>
                      <tr>
                        <td className="font-medium text-slate-900 dark:text-white">Media Aritmética (Ticket Medio)</td>
                        <td>
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                            CUANTITATIVA
                          </span>
                        </td>
                        <td className="text-xs text-gray-500 dark:text-gray-400">x̄ = (∑ xᵢ) / n</td>
                        <td className="text-right font-mono font-semibold text-cyan-600 dark:text-cyan-400">
                          {money(resumen.ticket_promedio)}
                        </td>
                      </tr>
                      <tr>
                        <td className="font-medium text-slate-900 dark:text-white">Mediana de Ventas</td>
                        <td>
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                            CUANTITATIVA
                          </span>
                        </td>
                        <td className="text-xs text-gray-500 dark:text-gray-400">Elemento en posición (n+1)/2 tras ordenamiento</td>
                        <td className="text-right font-mono font-semibold text-slate-900 dark:text-white">
                          {money(resumen.mediana_ventas)}
                        </td>
                      </tr>
                      <tr>
                        <td className="font-medium text-slate-900 dark:text-white">Sesgo de Distribución</td>
                        <td>
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                            CUANTITATIVA
                          </span>
                        </td>
                        <td className="text-xs text-gray-500 dark:text-gray-400">Comparación Media vs Mediana (x̄ - Me)</td>
                        <td className="text-right font-mono text-slate-800 dark:text-gray-200">
                          {Number(resumen.ticket_promedio) > Number(resumen.mediana_ventas)
                            ? 'Asimétrica a la derecha (x̄ > Me)'
                            : 'Asimétrica a la izquierda (x̄ < Me)'}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div className="alert-card alert-info mt-4">
                  <Sparkles className="h-4 w-4 shrink-0 text-blue-500" />
                  <p className="text-xs">
                    <strong>Interpretación descriptiva:</strong> La media describe el importe monetario medio por transacción;
                    la mediana indica el valor central libre del impacto de compras atípicas o de montos extremos.
                  </p>
                </div>
              </GlassCard>
            </>
          )}
        </motion.div>
      )}

      {/* SubTab B: Distribuciones */}
      {activeSubTab === 'distribuciones' && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="space-y-6"
        >
          {/* Controls */}
          <GlassCard className="p-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
              <div>
                <label className="input-label">Variable a evaluar:</label>
                <select
                  className="input-field"
                  value={variableDist}
                  onChange={(e) => setVariableDist(e.target.value as 'importe_venta' | 'estado_pago')}
                >
                  <option value="importe_venta">Importe de Venta (Cuantitativa)</option>
                  <option value="estado_pago">Estado de Pago (Cualitativa)</option>
                </select>
              </div>

              <div>
                <label className="input-label">Intervalos (Bins 1-20):</label>
                <input
                  type="number"
                  min={1}
                  max={20}
                  className="input-field"
                  value={intervalos}
                  onChange={(e) => setIntervalos(Number(e.target.value))}
                />
              </div>

              <Button
                variant="primary"
                onClick={consultarAnalytics}
                disabled={loading}
                icon={<RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />}
              >
                Recalcular Histograma
              </Button>
            </div>
          </GlassCard>

          {/* Chart & Table */}
          {distribucion && (
            <>
              <GlassCard className="p-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
                  <div>
                    <h3 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                      <BarChart3 className="h-5 w-5 text-cyan-500" />
                      Histograma de Frecuencias: {distribucion.variable}
                    </h3>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Total de observaciones analizadas: {distribucion.total_observaciones}
                    </p>
                  </div>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400 self-start sm:self-auto">
                    {variableDist === 'importe_venta' ? 'CUANTITATIVA' : 'CUALITATIVA'}
                  </span>
                </div>

                {(() => {
                  const lista = distribucion.distribucion || distribucion.intervalos || [];
                  if (lista.length === 0) {
                    return (
                      <div className="py-12 text-center text-gray-500">
                        No se registraron datos para generar la distribución en el periodo.
                      </div>
                    );
                  }

                  const chartData = lista.map((item, idx) => ({
                    etiqueta: item.categoria || item.etiqueta || (item.desde && item.hasta ? `${item.desde}–${item.hasta}` : `Int ${idx + 1}`),
                    frecuencia: item.frecuencia_absoluta ?? item.frecuencia ?? 0,
                    porcentaje: item.porcentaje
                      ? parseFloat(item.porcentaje)
                      : item.frecuencia_relativa
                      ? parseFloat(item.frecuencia_relativa) * 100
                      : 0,
                  }));

                  return (
                    <div className="h-80 w-full mt-4">
                      <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: -15, bottom: 25 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                          <XAxis
                            dataKey="etiqueta"
                            tick={{ fill: '#94a3b8', fontSize: 11 }}
                            angle={-20}
                            textAnchor="end"
                          />
                          <YAxis yAxisId="left" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                          <YAxis yAxisId="right" orientation="right" tick={{ fill: '#94a3b8', fontSize: 11 }} unit="%" />
                          <Tooltip content={<CustomTooltip unit="" />} />
                          <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '15px' }} />
                          <Bar
                            yAxisId="left"
                            dataKey="frecuencia"
                            name="Frecuencia Absoluta (fi)"
                            fill="#06b6d4"
                            radius={[4, 4, 0, 0]}
                          />
                          <Line
                            yAxisId="right"
                            type="monotone"
                            dataKey="porcentaje"
                            name="Frecuencia Relativa (%)"
                            stroke="#3b82f6"
                            strokeWidth={2}
                            dot={{ r: 4, fill: '#3b82f6' }}
                          />
                        </ComposedChart>
                      </ResponsiveContainer>
                    </div>
                  );
                })()}
              </GlassCard>

              {/* Data Table */}
              <GlassCard className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-base font-semibold text-slate-900 dark:text-white">
                    Tabla de Distribución de Frecuencias
                  </h3>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    N={distribucion.total_observaciones} observaciones
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Intervalo / Categoría</th>
                        <th>Tipo</th>
                        <th className="text-right">Frecuencia Absoluta (fi)</th>
                        <th className="text-right">Frecuencia Relativa (hi)</th>
                        <th className="text-right">Porcentaje (%)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(distribucion.distribucion || distribucion.intervalos || []).map((item, idx) => {
                        const freq = item.frecuencia_absoluta ?? item.frecuencia ?? 0;
                        const label = item.categoria || item.etiqueta || (item.desde && item.hasta ? `${item.desde} – ${item.hasta}` : `Intervalo ${idx + 1}`);
                        const rel = item.frecuencia_relativa ?? (distribucion.total_observaciones ? (freq / distribucion.total_observaciones).toFixed(4) : '0');
                        const pct = item.porcentaje ?? `${(parseFloat(String(rel)) * 100).toFixed(1)}%`;

                        return (
                          <tr key={idx}>
                            <td className="font-medium text-slate-900 dark:text-white">{label}</td>
                            <td>
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                                {variableDist === 'importe_venta' ? 'CUANTITATIVA' : 'CUALITATIVA'}
                              </span>
                            </td>
                            <td className="text-right font-mono font-medium text-slate-800 dark:text-gray-200">
                              {freq.toLocaleString('es-PE')}
                            </td>
                            <td className="text-right font-mono text-slate-600 dark:text-gray-400">{rel}</td>
                            <td className="text-right font-mono font-bold text-cyan-600 dark:text-cyan-400">{pct}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </GlassCard>
            </>
          )}
        </motion.div>
      )}

      {/* SubTab C: Probabilidades y Teorema de Bayes */}
      {activeSubTab === 'probabilidades' && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="space-y-6"
        >
          {/* Controls */}
          <GlassCard className="p-4">
            <div className="flex flex-col sm:flex-row items-stretch sm:items-end gap-4">
              <div className="flex-1">
                <label className="input-label">Umbral Importe Alto (PEN):</label>
                <input
                  type="text"
                  className="input-field"
                  value={umbralImporte}
                  onChange={(e) => setUmbralImporte(e.target.value)}
                />
              </div>
              <Button
                variant="primary"
                onClick={consultarAnalytics}
                disabled={loading}
                icon={<Calculator className="h-4 w-4" />}
              >
                Calcular Teorema de Bayes
              </Button>
            </div>
          </GlassCard>

          {probabilidades && (
            <>
              {/* Stat Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <GlassCard hover className="p-4 border-l-4 border-l-blue-500">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-gray-500 dark:text-gray-400">P(Pagado)</span>
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                      SIMPLE
                    </span>
                  </div>
                  <div className="mt-2 text-right">
                    <div className="text-2xl font-bold font-mono text-slate-900 dark:text-white">
                      {probabilidades.probabilidad_pagado ?? 'N/A'}
                    </div>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-1">
                      {probabilidades.conteos.pagado} de {probabilidades.total_observaciones} ventas
                    </p>
                  </div>
                </GlassCard>

                <GlassCard hover className="p-4 border-l-4 border-l-cyan-500">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-gray-500 dark:text-gray-400">
                      P(Alto ≥ S/ {probabilidades.umbral_importe_alto})
                    </span>
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                      SIMPLE
                    </span>
                  </div>
                  <div className="mt-2 text-right">
                    <div className="text-2xl font-bold font-mono text-slate-900 dark:text-white">
                      {probabilidades.probabilidad_importe_alto ?? 'N/A'}
                    </div>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-1">
                      {probabilidades.conteos.importe_alto} superan umbral
                    </p>
                  </div>
                </GlassCard>

                <GlassCard hover className="p-4 border-l-4 border-l-indigo-500">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-gray-500 dark:text-gray-400">P(Pagado | Alto)</span>
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                      CONDICIONAL
                    </span>
                  </div>
                  <div className="mt-2 text-right">
                    <div className="text-2xl font-bold font-mono text-slate-900 dark:text-white">
                      {probabilidades.probabilidad_pagado_dado_alto ?? 'N/A'}
                    </div>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-1">
                      Cobranza dado ticket alto
                    </p>
                  </div>
                </GlassCard>

                <GlassCard hover className="p-4 border-2 border-cyan-500 bg-cyan-500/5 dark:bg-cyan-500/10 shadow-[0_0_15px_rgba(6,182,212,0.2)]">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-cyan-600 dark:text-cyan-400">★ Bayes: P(Alto | Pagado)</span>
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-cyan-500/20 text-cyan-700 dark:text-cyan-300">
                      BAYES
                    </span>
                  </div>
                  <div className="mt-2 text-right">
                    <div className="text-2xl font-bold font-mono text-cyan-600 dark:text-cyan-400">
                      {probabilidades.bayes_importe_alto_dado_pagado ?? 'N/A'}
                    </div>
                    <p className="text-[11px] font-mono text-gray-500 dark:text-gray-400 mt-1">
                      P(Alto)·P(Pag|Alto) / P(Pag)
                    </p>
                  </div>
                </GlassCard>
              </div>

              {/* ComposedChart Visualizing probabilities */}
              <GlassCard className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                    <Percent className="h-5 w-5 text-cyan-500" />
                    Comparativa de Probabilidades (0% a 100%)
                  </h3>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                    CUANTITATIVA
                  </span>
                </div>

                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart
                      data={[
                        {
                          name: 'P(Pagado)',
                          porcentaje: Number(probabilidades.probabilidad_pagado || 0) * 100,
                          label: 'Pago completado',
                        },
                        {
                          name: 'P(Alto)',
                          porcentaje: Number(probabilidades.probabilidad_importe_alto || 0) * 100,
                          label: 'Ticket sobre umbral',
                        },
                        {
                          name: 'P(Pagado | Alto)',
                          porcentaje: Number(probabilidades.probabilidad_pagado_dado_alto || 0) * 100,
                          label: 'Pagado dado ticket alto',
                        },
                        {
                          name: 'Bayes: P(Alto | Pag)',
                          porcentaje: Number(probabilidades.bayes_importe_alto_dado_pagado || 0) * 100,
                          label: 'Alto dado que está pagado',
                        },
                      ]}
                      margin={{ top: 10, right: 10, left: -20, bottom: 10 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                      <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                      <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} unit="%" domain={[0, 100]} />
                      <Tooltip content={<CustomTooltip unit="%" />} />
                      <Bar dataKey="porcentaje" name="Probabilidad (%)" fill="#06b6d4" radius={[4, 4, 0, 0]} />
                      <Line type="monotone" dataKey="porcentaje" name="Tendencia" stroke="#3b82f6" strokeWidth={2} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </GlassCard>

              {/* Data Table */}
              <GlassCard className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-base font-semibold text-slate-900 dark:text-white">
                    Tabla de Probabilidades Exactas
                  </h3>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    Evaluación con umbral S/ {probabilidades.umbral_importe_alto}
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Evento / Condición</th>
                        <th>Tipo</th>
                        <th className="text-right">Casos Favorables</th>
                        <th className="text-right">Probabilidad (0-1)</th>
                        <th className="text-right">Porcentaje (%)</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td className="font-medium text-slate-900 dark:text-white">P(Pagado)</td>
                        <td>
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                            SIMPLE
                          </span>
                        </td>
                        <td className="text-right font-mono text-slate-700 dark:text-gray-300">
                          {probabilidades.conteos.pagado} / {probabilidades.total_observaciones}
                        </td>
                        <td className="text-right font-mono text-slate-900 dark:text-white">
                          {probabilidades.probabilidad_pagado ?? 'N/A'}
                        </td>
                        <td className="text-right font-mono font-bold text-cyan-600 dark:text-cyan-400">
                          {percentage(probabilidades.probabilidad_pagado)}
                        </td>
                      </tr>
                      <tr>
                        <td className="font-medium text-slate-900 dark:text-white">
                          P(Alto ≥ {probabilidades.umbral_importe_alto})
                        </td>
                        <td>
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                            SIMPLE
                          </span>
                        </td>
                        <td className="text-right font-mono text-slate-700 dark:text-gray-300">
                          {probabilidades.conteos.importe_alto} / {probabilidades.total_observaciones}
                        </td>
                        <td className="text-right font-mono text-slate-900 dark:text-white">
                          {probabilidades.probabilidad_importe_alto ?? 'N/A'}
                        </td>
                        <td className="text-right font-mono font-bold text-cyan-600 dark:text-cyan-400">
                          {percentage(probabilidades.probabilidad_importe_alto)}
                        </td>
                      </tr>
                      <tr>
                        <td className="font-medium text-slate-900 dark:text-white">P(Pagado | Alto)</td>
                        <td>
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                            CONDICIONAL
                          </span>
                        </td>
                        <td className="text-right font-mono text-slate-700 dark:text-gray-300">
                          {probabilidades.conteos.importe_alto_y_pagado} / {probabilidades.conteos.importe_alto}
                        </td>
                        <td className="text-right font-mono text-slate-900 dark:text-white">
                          {probabilidades.probabilidad_pagado_dado_alto ?? 'N/A'}
                        </td>
                        <td className="text-right font-mono font-bold text-cyan-600 dark:text-cyan-400">
                          {percentage(probabilidades.probabilidad_pagado_dado_alto)}
                        </td>
                      </tr>
                      <tr className="bg-cyan-500/5 dark:bg-cyan-500/10">
                        <td className="font-medium text-cyan-700 dark:text-cyan-300">★ Teorema de Bayes: P(Alto | Pagado)</td>
                        <td>
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-cyan-500/20 text-cyan-700 dark:text-cyan-300">
                            INFERENCIA
                          </span>
                        </td>
                        <td className="text-right font-mono text-cyan-700 dark:text-cyan-300">Fórmula Bayesiana</td>
                        <td className="text-right font-mono font-bold text-cyan-700 dark:text-cyan-300">
                          {probabilidades.bayes_importe_alto_dado_pagado ?? 'N/A'}
                        </td>
                        <td className="text-right font-mono font-bold text-cyan-700 dark:text-cyan-300">
                          {percentage(probabilidades.bayes_importe_alto_dado_pagado)}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div className="alert-card alert-info mt-4">
                  <ShieldCheck className="h-4 w-4 shrink-0 text-blue-500" />
                  <p className="text-xs">
                    <strong>Fundamento matemático:</strong> Permite evaluar si una venta ya completada y cancelada
                    tiene alta o baja probabilidad de pertenecer a los tickets de alta magnitud, utilizando conteos exactos.
                  </p>
                </div>
              </GlassCard>
            </>
          )}
        </motion.div>
      )}

      {/* SubTab D: Semana 08 (Dispersión y Contraste de Hipótesis) */}
      {activeSubTab === 'semana08' && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="space-y-6"
        >
          {/* Controls */}
          <GlassCard className="p-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
              <div>
                <label className="input-label">Media Hipotética (H0):</label>
                <input
                  type="number"
                  className="input-field"
                  value={mediaHipotetica}
                  onChange={(e) => setMediaHipotetica(Number(e.target.value))}
                />
              </div>

              <div>
                <label className="input-label">Significancia (alfa):</label>
                <input
                  type="number"
                  step="0.01"
                  className="input-field"
                  value={alfa}
                  onChange={(e) => setAlfa(Number(e.target.value))}
                />
              </div>

              <Button
                variant="primary"
                onClick={consultarAnalytics}
                disabled={loading}
                icon={<Activity className="h-4 w-4" />}
              >
                Ejecutar Prueba t de Student
              </Button>
            </div>
          </GlassCard>

          {semana08 && (() => {
            const res = semana08.resultados || semana08;
            return (
              <div className="space-y-6">
                {/* Stat Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <GlassCard hover className="p-5 border-l-4 border-l-blue-500">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-gray-500 dark:text-gray-400">
                        Esperanza Empírica (Media)
                      </span>
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                        CUANTITATIVA
                      </span>
                    </div>
                    <div className="mt-3 text-right">
                      <div className="text-2xl font-bold font-mono text-slate-900 dark:text-white">
                        PEN {res.esperanza_empirica ?? res.media ?? 'N/A'}
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        Muestra de {res.cantidad} ventas
                      </p>
                    </div>
                  </GlassCard>

                  <GlassCard hover className="p-5 border-l-4 border-l-cyan-500">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-gray-500 dark:text-gray-400">
                        Desviación Muestral (s)
                      </span>
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                        DISPERSIÓN
                      </span>
                    </div>
                    <div className="mt-3 text-right">
                      <div className="text-2xl font-bold font-mono text-cyan-600 dark:text-cyan-400">
                        {res.desviacion_muestral ?? 'N/A'}
                      </div>
                      <p className="text-xs font-mono text-gray-500 dark:text-gray-400 mt-1">
                        s²: {res.varianza_muestral ?? 'N/A'}
                      </p>
                    </div>
                  </GlassCard>

                  <GlassCard hover className="p-5 border-l-4 border-l-indigo-500">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-gray-500 dark:text-gray-400">
                        Desviación Poblacional (σ)
                      </span>
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                        DISPERSIÓN
                      </span>
                    </div>
                    <div className="mt-3 text-right">
                      <div className="text-2xl font-bold font-mono text-slate-900 dark:text-white">
                        {res.desviacion_poblacional ?? 'N/A'}
                      </div>
                      <p className="text-xs font-mono text-gray-500 dark:text-gray-400 mt-1">
                        σ²: {res.varianza_poblacional ?? 'N/A'}
                      </p>
                    </div>
                  </GlassCard>
                </div>

                {/* ComposedChart Histogram if present */}
                {semana08.resultados?.histograma?.etiquetas?.length ? (
                  <GlassCard className="p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h3 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                          <BarChart3 className="h-5 w-5 text-cyan-500" />
                          {semana08.resultados.histograma.titulo || 'Distribución de la muestra'}
                        </h3>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          Frecuencia observada en {semana08.resultados.histograma.etiquetas.length} intervalos
                        </p>
                      </div>
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                        CUANTITATIVA
                      </span>
                    </div>

                    <div className="h-64 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart
                          data={semana08.resultados.histograma.etiquetas.map((label, i) => ({
                            label,
                            valor: semana08.resultados?.histograma?.valores[i] || 0,
                          }))}
                          margin={{ top: 10, right: 10, left: -20, bottom: 20 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                          <XAxis dataKey="label" tick={{ fill: '#94a3b8', fontSize: 10 }} angle={-25} textAnchor="end" />
                          <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
                          <Tooltip content={<CustomTooltip />} />
                          <Bar dataKey="valor" name="Frecuencia" fill="#06b6d4" radius={[4, 4, 0, 0]} />
                          <Line type="monotone" dataKey="valor" name="Curva" stroke="#3b82f6" strokeWidth={2} />
                        </ComposedChart>
                      </ResponsiveContainer>
                    </div>
                  </GlassCard>
                ) : null}

                {/* Contraste de Hipótesis Card */}
                {res.contraste && (
                  <GlassCard className="p-6 border-l-4 border-l-cyan-500 space-y-4">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div>
                        <h3 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                          <Activity className="h-5 w-5 text-cyan-500" />
                          Resultado de la Prueba t de Student (SciPy)
                        </h3>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                          {res.contraste.metodo} · {res.contraste.hipotesis_nula}
                        </p>
                      </div>
                      <div>
                        <span
                          className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                            res.contraste.rechazar_hipotesis_nula
                              ? 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20'
                              : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
                          }`}
                        >
                          {res.contraste.rechazar_hipotesis_nula ? 'RECHAZA H0' : 'NO RECHAZA H0'}
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 rounded-lg bg-gray-50 dark:bg-white/5 border border-gray-200/50 dark:border-white/5">
                      <div>
                        <span className="text-[11px] uppercase tracking-wider text-gray-500 dark:text-gray-400 block">
                          Estadístico t
                        </span>
                        <span className="text-lg font-bold font-mono text-slate-900 dark:text-white">
                          {res.contraste.estadistico_t ?? 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="text-[11px] uppercase tracking-wider text-gray-500 dark:text-gray-400 block">
                          Grados Libertad
                        </span>
                        <span className="text-lg font-bold font-mono text-slate-900 dark:text-white">
                          {res.contraste.grados_libertad ?? 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="text-[11px] uppercase tracking-wider text-gray-500 dark:text-gray-400 block">
                          p-valor
                        </span>
                        <span className="text-lg font-bold font-mono text-cyan-600 dark:text-cyan-400">
                          {res.contraste.valor_p ?? 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="text-[11px] uppercase tracking-wider text-gray-500 dark:text-gray-400 block">
                          Alfa (α)
                        </span>
                        <span className="text-lg font-bold font-mono text-slate-900 dark:text-white">
                          {res.contraste.alfa ?? alfa}
                        </span>
                      </div>
                    </div>

                    <div className="alert-card alert-info">
                      <Sparkles className="h-4 w-4 shrink-0 text-blue-500" />
                      <div className="text-xs space-y-1">
                        <p>{res.contraste.explicacion}</p>
                        {res.contraste.advertencia && (
                          <p className="text-gray-500 dark:text-gray-400 italic">{res.contraste.advertencia}</p>
                        )}
                      </div>
                    </div>
                  </GlassCard>
                )}

                {/* Analytical Data Table with data-table */}
                <GlassCard className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-base font-semibold text-slate-900 dark:text-white">
                      Parámetros de Dispersión y Estimación
                    </h3>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      Muestra N={res.cantidad}
                    </span>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Parámetro</th>
                          <th>Tipo</th>
                          <th>Notación</th>
                          <th className="text-right">Valor Numérico</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td className="font-medium text-slate-900 dark:text-white">Esperanza Matemática Empírica</td>
                          <td>
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                              CUANTITATIVA
                            </span>
                          </td>
                          <td className="font-mono text-xs text-gray-500 dark:text-gray-400">E[X] ≈ x̄</td>
                          <td className="text-right font-mono font-bold text-slate-900 dark:text-white">
                            {res.esperanza_empirica ?? res.media ?? 'N/A'}
                          </td>
                        </tr>
                        <tr>
                          <td className="font-medium text-slate-900 dark:text-white">Desviación Estándar Muestral</td>
                          <td>
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                              DISPERSIÓN
                            </span>
                          </td>
                          <td className="font-mono text-xs text-gray-500 dark:text-gray-400">s = √(∑(xᵢ - x̄)² / (n-1))</td>
                          <td className="text-right font-mono font-bold text-cyan-600 dark:text-cyan-400">
                            {res.desviacion_muestral ?? 'N/A'}
                          </td>
                        </tr>
                        <tr>
                          <td className="font-medium text-slate-900 dark:text-white">Varianza Muestral</td>
                          <td>
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                              DISPERSIÓN
                            </span>
                          </td>
                          <td className="font-mono text-xs text-gray-500 dark:text-gray-400">s²</td>
                          <td className="text-right font-mono text-slate-800 dark:text-gray-200">
                            {res.varianza_muestral ?? 'N/A'}
                          </td>
                        </tr>
                        <tr>
                          <td className="font-medium text-slate-900 dark:text-white">Desviación Estándar Poblacional</td>
                          <td>
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                              DISPERSIÓN
                            </span>
                          </td>
                          <td className="font-mono text-xs text-gray-500 dark:text-gray-400">σ = √(∑(xᵢ - μ)² / N)</td>
                          <td className="text-right font-mono text-slate-800 dark:text-gray-200">
                            {res.desviacion_poblacional ?? 'N/A'}
                          </td>
                        </tr>
                        <tr>
                          <td className="font-medium text-slate-900 dark:text-white">Varianza Poblacional</td>
                          <td>
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                              DISPERSIÓN
                            </span>
                          </td>
                          <td className="font-mono text-xs text-gray-500 dark:text-gray-400">σ²</td>
                          <td className="text-right font-mono text-slate-800 dark:text-gray-200">
                            {res.varianza_poblacional ?? 'N/A'}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </GlassCard>
              </div>
            );
          })()}
        </motion.div>
      )}
    </motion.div>
  );
};
export default AnalyticsView;
