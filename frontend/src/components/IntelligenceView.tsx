import React, { useCallback, useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles,
  Bell,
  History,
  ShieldCheck,
  Calendar,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Check,
  X,
  Clock,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Cpu,
  Layers,
  ArrowRight,
  Filter,
  Info,
  AlertTriangle,
  Lightbulb,
} from 'lucide-react';
import { api, InsightF7, NotificacionF7, AnalisisF7, EventoAuditoriaF7, ApiError } from '../services/api';
import { GlassCard } from './ui/GlassCard';
import { Button } from './ui/Button';
import { Badge } from './ui/Badge';

type Vista = 'insights' | 'notificaciones' | 'historial' | 'auditoria';

const fecha = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const hoy = fecha(new Date());
const inicioInicial = fecha(new Date(Date.now() - 180 * 86400000));
const human = (s: string | null | undefined) => (s ? new Date(s).toLocaleString('es-PE') : 'Sin fecha');

const detalleError = (error: unknown) => {
  if (error instanceof ApiError && error.status === 403)
    return 'No cuentas con permisos para consultar o ejecutar esta operación.';
  return error instanceof Error ? error.message : 'No se pudo completar la operación.';
};

export const IntelligenceView: React.FC = () => {
  const [vista, setVista] = useState<Vista>('insights');
  const [desde, setDesde] = useState(inicioInicial);
  const [hasta, setHasta] = useState(hoy);
  const [tipo, setTipo] = useState<'estadistico' | 'probabilidad'>('estadistico');
  const [nombre, setNombre] = useState('Resumen comercial');
  const [umbral, setUmbral] = useState('100.00');
  const [soloNoLeidas, setSoloNoLeidas] = useState(false);
  const [accion, setAccion] = useState('');
  const [pagina, setPagina] = useState(0);
  const [tamPagina, setTamPagina] = useState(25);
  const ultimaSincronizacion = useRef('');
  const [loading, setLoading] = useState(false);
  const [procesando, setProcesando] = useState(false);
  const [error, setError] = useState('');
  const [aviso, setAviso] = useState('');
  const [insights, setInsights] = useState<InsightF7[]>([]);
  const [notificaciones, setNotificaciones] = useState<NotificacionF7[]>([]);
  const [analisis, setAnalisis] = useState<AnalisisF7[]>([]);
  const [auditoria, setAuditoria] = useState<{ total: number; items: EventoAuditoriaF7[] }>({
    total: 0,
    items: [],
  });
  const [ampliado, setAmpliado] = useState<number | null>(null);

  const cargar = useCallback(async () => {
    setLoading(true);
    setError('');
    setAviso('');
    try {
      if (vista === 'insights') setInsights((await api.listarInsights()).items);
      if (vista === 'notificaciones') setNotificaciones((await api.listarNotificaciones(soloNoLeidas)).items);
      if (vista === 'historial') setAnalisis((await api.listarHistorialAnalisis(tipo)).items);
      if (vista === 'auditoria') {
        const r = await api.listarAuditoria(pagina * tamPagina, tamPagina, accion);
        setAuditoria({ total: r.total, items: r.items });
      }
    } catch (e) {
      setError(detalleError(e));
    } finally {
      setLoading(false);
    }
  }, [vista, soloNoLeidas, tipo, pagina, tamPagina, accion]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  const fechasValidas = desde <= hasta && !!desde && !!hasta;
  const umbralValido = Number.isFinite(Number(umbral)) && Number(umbral) >= 0;

  useEffect(() => {
    if (vista !== 'notificaciones' || !fechasValidas) return;
    const clave = `${desde}|${hasta}`;
    if (ultimaSincronizacion.current === clave) return;
    ultimaSincronizacion.current = clave;
    let activo = true;
    api
      .sincronizarNotificaciones(desde, hasta)
      .then(() => {
        if (activo) void cargar();
      })
      .catch(() => {
        if (activo)
          setAviso('Las alertas existentes están disponibles; la sincronización automática no pudo completarse.');
      });
    return () => {
      activo = false;
    };
  }, [vista, desde, hasta, fechasValidas, cargar]);

  useEffect(() => {
    if (vista !== 'notificaciones') return;
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') void cargar();
    }, 60000);
    return () => window.clearInterval(timer);
  }, [vista, cargar]);

  const ejecutar = async (operacion: () => Promise<unknown>, mensaje: string) => {
    setProcesando(true);
    setError('');
    setAviso('');
    try {
      await operacion();
      await cargar();
      setAviso(mensaje);
    } catch (e) {
      setError(detalleError(e));
    } finally {
      setProcesando(false);
    }
  };

  const getPriorityVariant = (prioridad: string): 'danger' | 'warning' | 'info' => {
    const p = prioridad.toUpperCase();
    if (p.includes('ALTA') || p.includes('CRITICA') || p.includes('URGENTE')) return 'danger';
    if (p.includes('MEDIA') || p.includes('MODERADA')) return 'warning';
    return 'info';
  };

  const getNotificationIcon = (nivel: string) => {
    const n = nivel.toUpperCase();
    if (n.includes('ERROR') || n.includes('CRITIC') || n.includes('ALTA')) {
      return <AlertCircle className="h-5 w-5 text-rose-500" />;
    }
    if (n.includes('WARN') || n.includes('AVISO') || n.includes('MEDIA')) {
      return <AlertTriangle className="h-5 w-5 text-amber-500" />;
    }
    return <Info className="h-5 w-5 text-cyan-500" />;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="glass p-5 md:p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4 border border-[#D97843]/20 dark:border-white/10 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-extrabold uppercase tracking-wider bg-slate-200/80 dark:bg-white/15 text-slate-800 dark:text-slate-200">
              CENTRO INTELIGENTE / FASE 7
            </span>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-cyan-500/15 text-cyan-800 dark:text-cyan-300 border border-cyan-500/30">
              <Sparkles className="w-3.5 h-3.5" />
              IA &amp; Trazabilidad
            </span>
          </div>
          <h2 className="text-2xl md:text-3xl font-black tracking-tight text-slate-950 dark:text-white mt-1.5 flex items-center gap-2.5 drop-shadow-sm">
            <Cpu className="h-7 w-7 text-[#D97843] dark:text-[#FFA675]" />
            Centro Inteligente y Registro de Auditoría
          </h2>
          <p className="text-sm text-slate-700 dark:text-slate-200 font-medium mt-1">
            Generación de recomendaciones operativas, alertas persistentes, histórico de modelos y bitácora de eventos.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={() => void cargar()}
          disabled={loading || procesando}
          icon={<RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin text-cyan-500' : ''}`} />}
        >
          {loading ? 'Consultando...' : 'Actualizar'}
        </Button>
      </div>

      {/* Main Tab Bar */}
      <div className="tab-bar overflow-x-auto p-1.5 glass">
        <button
          type="button"
          className={`tab-item flex items-center gap-2 ${vista === 'insights' ? 'active' : ''}`}
          onClick={() => {
            setVista('insights');
            setAmpliado(null);
          }}
        >
          <Lightbulb className={`h-4 w-4 ${vista === 'insights' ? 'text-cyan-500' : 'text-gray-400'}`} />
          <span>Insights</span>
        </button>
        <button
          type="button"
          className={`tab-item flex items-center gap-2 ${vista === 'notificaciones' ? 'active' : ''}`}
          onClick={() => {
            setVista('notificaciones');
            setAmpliado(null);
          }}
        >
          <Bell className={`h-4 w-4 ${vista === 'notificaciones' ? 'text-cyan-500' : 'text-gray-400'}`} />
          <span>Notificaciones</span>
          {notificaciones.filter((n) => !n.leida).length > 0 && (
            <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-cyan-500 text-white">
              {notificaciones.filter((n) => !n.leida).length}
            </span>
          )}
        </button>
        <button
          type="button"
          className={`tab-item flex items-center gap-2 ${vista === 'historial' ? 'active' : ''}`}
          onClick={() => {
            setVista('historial');
            setAmpliado(null);
          }}
        >
          <History className={`h-4 w-4 ${vista === 'historial' ? 'text-cyan-500' : 'text-gray-400'}`} />
          <span>Historial</span>
        </button>
        <button
          type="button"
          className={`tab-item flex items-center gap-2 ${vista === 'auditoria' ? 'active' : ''}`}
          onClick={() => {
            setVista('auditoria');
            setAmpliado(null);
          }}
        >
          <ShieldCheck className={`h-4 w-4 ${vista === 'auditoria' ? 'text-cyan-500' : 'text-gray-400'}`} />
          <span>Auditoría</span>
        </button>
      </div>

      {/* Global Date Filter in Glass Card */}
      <GlassCard className="p-4">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-end gap-4">
          <div className="flex-1">
            <label htmlFor="p7desde" className="input-label flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5 text-cyan-500" />
              Fecha Desde
            </label>
            <input
              id="p7desde"
              type="date"
              className="input-field"
              value={desde}
              onChange={(e) => setDesde(e.target.value)}
            />
          </div>

          <div className="flex-1">
            <label htmlFor="p7hasta" className="input-label flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5 text-cyan-500" />
              Fecha Hasta
            </label>
            <input
              id="p7hasta"
              type="date"
              className="input-field"
              value={hasta}
              onChange={(e) => setHasta(e.target.value)}
            />
          </div>

          <Button
            variant="outline"
            onClick={() => void cargar()}
            disabled={loading || procesando || !fechasValidas}
            className="sm:w-auto"
            icon={<RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />}
          >
            Refrescar Datos
          </Button>
        </div>
      </GlassCard>

      {/* Feedback Alerts */}
      <AnimatePresence>
        {!fechasValidas && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="alert-card alert-error"
          >
            <AlertCircle className="h-5 w-5 shrink-0" />
            <div className="text-xs">Selecciona fechas válidas: la fecha inicial no puede superar la fecha final.</div>
          </motion.div>
        )}
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="alert-card alert-error"
            role="alert"
          >
            <AlertCircle className="h-5 w-5 shrink-0" />
            <div className="text-xs">{error}</div>
          </motion.div>
        )}
        {aviso && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="alert-card alert-success"
            role="status"
          >
            <CheckCircle2 className="h-5 w-5 shrink-0" />
            <div className="text-xs font-medium">{aviso}</div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* TAB 1: INSIGHTS */}
      {vista === 'insights' && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="space-y-4"
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                <Lightbulb className="h-5 w-5 text-amber-500" />
                Recomendaciones del Sistema (Insights)
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Los insights se producen analizando modelos y contrastes persistidos en el servidor.
              </p>
            </div>
            <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">
              {insights.length} recomendación(es)
            </span>
          </div>

          {insights.length === 0 && !loading && (
            <GlassCard className="p-12 text-center text-gray-400 space-y-3">
              <Sparkles className="h-10 w-10 mx-auto opacity-40 text-cyan-500" />
              <p className="text-base font-semibold text-slate-800 dark:text-gray-200">
                Todavía no se han generado recomendaciones
              </p>
              <p className="text-xs max-w-md mx-auto text-gray-500">
                El motor mostrará oportunidades y advertencias cuando el backend produzca insights a partir de análisis
                guardados. Puedes generar nuevos análisis en la pestaña &apos;Historial&apos;.
              </p>
            </GlassCard>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {insights.map((item) => (
              <GlassCard
                key={item.id}
                hover
                className="p-5 flex flex-col justify-between space-y-4 border-l-4 border-l-cyan-500"
              >
                <div className="space-y-2.5">
                  {/* Top row with Priority Badge */}
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-mono font-bold text-gray-500 dark:text-gray-400">
                      Insight #{item.id}
                    </span>
                    <div className="flex items-center gap-2">
                      <Badge variant={getPriorityVariant(item.prioridad)} dot>
                        {item.prioridad}
                      </Badge>
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold uppercase bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-300">
                        {item.estado}
                      </span>
                    </div>
                  </div>

                  {/* Title & Description */}
                  <h4 className="font-semibold text-base text-slate-900 dark:text-white leading-snug">
                    {item.titulo}
                  </h4>
                  <p className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed">{item.descripcion}</p>

                  {/* Recommendation block */}
                  <div className="p-3 rounded-lg bg-gray-50 dark:bg-white/5 border border-gray-200/50 dark:border-white/5 text-xs space-y-1">
                    <span className="font-semibold text-cyan-600 dark:text-cyan-400 flex items-center gap-1.5">
                      <Lightbulb className="h-3.5 w-3.5" />
                      Acción Sugerida:
                    </span>
                    <p className="text-slate-800 dark:text-gray-200">
                      {item.recomendacion || 'Sin recomendación específica.'}
                    </p>
                  </div>

                  {/* Meta */}
                  <div className="text-[11px] text-gray-500 dark:text-gray-400 flex items-center justify-between pt-1">
                    <span>Origen: {item.tipo_insight}</span>
                    <span className="font-mono">{human(item.created_at)}</span>
                  </div>
                </div>

                {/* Actions */}
                <div className="pt-3 border-t border-gray-100 dark:border-white/5 flex items-center justify-end gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={procesando || item.estado === 'REVISADO'}
                    onClick={() =>
                      void ejecutar(
                        () => api.actualizarInsight(item.id, 'REVISADO'),
                        'Recomendación marcada como revisada.'
                      )
                    }
                    icon={<Check className="h-3.5 w-3.5 text-emerald-500" />}
                  >
                    Marcar Revisada
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={procesando || item.estado === 'DESCARTADO'}
                    onClick={() =>
                      void ejecutar(
                        () => api.actualizarInsight(item.id, 'DESCARTADO'),
                        'Recomendación descartada.'
                      )
                    }
                    icon={<X className="h-3.5 w-3.5 text-gray-400" />}
                  >
                    Descartar
                  </Button>
                </div>
              </GlassCard>
            ))}
          </div>
        </motion.div>
      )}

      {/* TAB 2: NOTIFICACIONES */}
      {vista === 'notificaciones' && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="space-y-4"
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                <Bell className="h-5 w-5 text-cyan-500" />
                Alertas y Notificaciones Persistentes
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Notificaciones almacenadas en el servidor con registro de confirmación de lectura.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-xs font-medium text-gray-700 dark:text-gray-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={soloNoLeidas}
                  onChange={(e) => setSoloNoLeidas(e.target.checked)}
                  className="rounded border-gray-300 text-cyan-600 focus:ring-cyan-500 h-4 w-4"
                />
                Solo no leídas
              </label>

              <Button
                variant="primary"
                size="sm"
                disabled={procesando || !fechasValidas}
                onClick={() =>
                  void ejecutar(
                    () => api.sincronizarNotificaciones(desde, hasta),
                    'Sincronización completada. Alertas actualizadas.'
                  )
                }
                icon={<RefreshCw className={`h-3.5 w-3.5 ${procesando ? 'animate-spin' : ''}`} />}
              >
                Sincronizar Alertas
              </Button>
            </div>
          </div>

          {notificaciones.length === 0 && !loading && (
            <GlassCard className="p-12 text-center text-gray-400">
              <Bell className="h-10 w-10 mx-auto mb-2 opacity-40 text-gray-400" />
              <p className="text-sm font-medium">No hay notificaciones para este filtro en el periodo.</p>
            </GlassCard>
          )}

          <div className="space-y-3">
            {notificaciones.map((item) => {
              const isUnread = !item.leida;
              return (
                <GlassCard
                  key={item.id}
                  hover
                  className={`p-4 transition-all duration-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
                    isUnread
                      ? 'border-l-4 border-l-cyan-500 bg-cyan-500/5 dark:bg-cyan-500/10 shadow-[0_0_15px_rgba(6,182,212,0.1)]'
                      : 'border-l-4 border-l-transparent opacity-85'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 p-2 rounded-lg bg-gray-100 dark:bg-white/5 shrink-0">
                      {getNotificationIcon(item.nivel)}
                    </div>

                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <h4 className="font-semibold text-sm text-slate-900 dark:text-white">
                          {item.titulo}
                        </h4>
                        {isUnread && (
                          <span className="w-2 h-2 rounded-full bg-cyan-500 shadow-[0_0_6px_#06b6d4]" />
                        )}
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold uppercase bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                          {item.nivel}
                        </span>
                      </div>
                      <p className="text-xs text-gray-600 dark:text-gray-300">{item.descripcion}</p>
                      <div className="text-[11px] text-gray-500 dark:text-gray-400 flex items-center gap-3 pt-0.5">
                        <span className="font-mono flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {human(item.created_at)}
                        </span>
                        <span>·</span>
                        <span>{item.leida ? 'Leída' : 'Pendiente de lectura'}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-auto shrink-0">
                    {isUnread && (
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={procesando}
                        onClick={() =>
                          void ejecutar(
                            () => api.marcarNotificacionLeida(item.id),
                            'Notificación marcada como leída.'
                          )
                        }
                        icon={<Check className="h-3.5 w-3.5 text-cyan-500" />}
                      >
                        Marcar Leída
                      </Button>
                    )}
                  </div>
                </GlassCard>
              );
            })}
          </div>
        </motion.div>
      )}

      {/* TAB 3: HISTORIAL */}
      {vista === 'historial' && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="space-y-6"
        >
          {/* Analysis Generation Card */}
          <GlassCard className="p-5">
            <h3 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2 mb-3">
              <Cpu className="h-5 w-5 text-cyan-500" />
              Nuevo Cálculo y Almacenamiento de Análisis
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
              <div>
                <label htmlFor="p7tipo" className="input-label">
                  Tipo de Análisis
                </label>
                <select
                  id="p7tipo"
                  className="input-field"
                  value={tipo}
                  onChange={(e) => setTipo(e.target.value as 'estadistico' | 'probabilidad')}
                >
                  <option value="estadistico">Estadística Descriptiva e Inferencial</option>
                  <option value="probabilidad">Probabilidades &amp; Teorema de Bayes</option>
                </select>
              </div>

              {tipo === 'estadistico' ? (
                <div>
                  <label htmlFor="p7nombre" className="input-label">
                    Nombre Descriptivo
                  </label>
                  <input
                    id="p7nombre"
                    type="text"
                    maxLength={150}
                    className="input-field"
                    value={nombre}
                    onChange={(e) => setNombre(e.target.value)}
                    placeholder="Ej. Balance Trimestral"
                  />
                </div>
              ) : (
                <div>
                  <label htmlFor="p7umbral" className="input-label">
                    Importe Alto Desde (S/)
                  </label>
                  <input
                    id="p7umbral"
                    type="number"
                    min="0"
                    step="0.01"
                    className="input-field"
                    value={umbral}
                    onChange={(e) => setUmbral(e.target.value)}
                  />
                </div>
              )}

              <Button
                variant="primary"
                disabled={
                  procesando || !fechasValidas || (tipo === 'estadistico' ? !nombre.trim() : !umbralValido)
                }
                onClick={() =>
                  void ejecutar(
                    () =>
                      tipo === 'estadistico'
                        ? api.crearAnalisisEstadistico(desde, hasta, nombre.trim())
                        : api.crearAnalisisProbabilidad(desde, hasta, umbral),
                    'Análisis computado y registrado en el historial de modelos.'
                  )
                }
                icon={<Cpu className="h-4 w-4" />}
              >
                Calcular y Guardar
              </Button>
            </div>
          </GlassCard>

          {/* Timeline of Analyses */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                <History className="h-5 w-5 text-cyan-500" />
                Línea de Tiempo de Análisis Almacenados
              </h3>
              <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                {analisis.length} modelo(s)
              </span>
            </div>

            {analisis.length === 0 && !loading && (
              <GlassCard className="p-12 text-center text-gray-400">
                <History className="h-10 w-10 mx-auto mb-2 opacity-40 text-gray-400" />
                <p className="text-sm font-medium">No se encontraron análisis guardados de tipo {tipo}.</p>
                <p className="text-xs text-gray-500 mt-1">
                  Ejecuta un nuevo cálculo arriba para almacenarlo y generar recomendaciones.
                </p>
              </GlassCard>
            )}

            <div className="relative pl-6 sm:pl-8 space-y-6 before:content-[''] before:absolute before:left-3 sm:before:left-4 before:top-3 before:bottom-3 before:w-0.5 before:bg-gradient-to-b before:from-cyan-500 before:to-transparent">
              {analisis.map((item) => {
                const isOpen = ampliado === item.id;
                return (
                  <div key={item.id} className="relative">
                    {/* Timeline bullet */}
                    <div className="absolute -left-6 sm:-left-8 top-3.5 w-3 h-3 rounded-full bg-cyan-500 border-2 border-white dark:border-[#0A0A0F] shadow-[0_0_8px_#06b6d4]" />

                    <GlassCard hover className="p-5 space-y-3">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <h4 className="font-semibold text-base text-slate-900 dark:text-white">
                            Análisis #{item.id}
                          </h4>
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400">
                            {item.tipo}
                          </span>
                          <Badge variant={item.estado === 'COMPLETADO' ? 'success' : 'neutral'}>
                            {item.estado}
                          </Badge>
                        </div>

                        <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                          {human(item.created_at)}
                        </span>
                      </div>

                      {/* Action buttons */}
                      <div className="flex items-center gap-2 pt-2 border-t border-gray-100 dark:border-white/5">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setAmpliado(isOpen ? null : item.id)}
                          icon={
                            isOpen ? (
                              <ChevronUp className="h-3.5 w-3.5" />
                            ) : (
                              <ChevronDown className="h-3.5 w-3.5" />
                            )
                          }
                        >
                          {isOpen ? 'Ocultar Resultados' : 'Ver Resultados JSON'}
                        </Button>

                        <Button
                          variant="primary"
                          size="sm"
                          disabled={procesando}
                          onClick={() =>
                            void ejecutar(
                              () => api.generarInsights(tipo, item.id),
                              'Recomendaciones generadas exitosamente. Puedes revisarlas en la pestaña Insights.'
                            )
                          }
                          icon={<Sparkles className="h-3.5 w-3.5" />}
                        >
                          Generar Recomendaciones
                        </Button>
                      </div>

                      {/* Expanded JSON viewer */}
                      <AnimatePresence>
                        {isOpen && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="overflow-hidden pt-2"
                          >
                            <pre className="p-4 rounded-lg bg-slate-950/90 text-cyan-400 text-xs font-mono overflow-x-auto border border-white/10 max-h-80">
                              {JSON.stringify(item.resultados, null, 2)}
                            </pre>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </GlassCard>
                  </div>
                );
              })}
            </div>
          </div>
        </motion.div>
      )}

      {/* TAB 4: AUDITORÍA */}
      {vista === 'auditoria' && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="space-y-4"
        >
          {/* Filter Bar */}
          <GlassCard className="p-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <label htmlFor="p7accion" className="input-label mb-0">
                  Acción:
                </label>
                <select
                  id="p7accion"
                  className="input-field py-1.5 text-xs w-48"
                  value={accion}
                  onChange={(e) => {
                    setPagina(0);
                    setAccion(e.target.value);
                  }}
                >
                  <option value="">Todas las acciones</option>
                  {['CREAR', 'ACTUALIZAR', 'ELIMINAR', 'CONFIRMAR', 'CANCELAR', 'ANULAR', 'CONSULTAR', 'OTRO'].map(
                    (x) => (
                      <option key={x} value={x}>
                        {x}
                      </option>
                    )
                  )}
                </select>
              </div>

              <div className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                Eventos encontrados: <strong className="text-slate-900 dark:text-white">{auditoria.total}</strong>
              </div>
            </div>
          </GlassCard>

          {/* Audit Data Table */}
          <GlassCard className="p-6 overflow-hidden">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                  <ShieldCheck className="h-5 w-5 text-cyan-500" />
                  Bitácora Criptográfica de Eventos y Auditoría
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Registro inmutable de trazabilidad operacional. No permite edición ni borrado.
                </p>
              </div>
            </div>

            {auditoria.items.length === 0 && !loading ? (
              <div className="py-12 text-center text-gray-400">
                <ShieldCheck className="h-10 w-10 mx-auto mb-2 opacity-40 text-gray-400" />
                <p className="text-sm font-medium">Sin eventos registrados para el filtro seleccionado.</p>
              </div>
            ) : (
              <>
                <div className="overflow-x-auto rounded-lg border border-gray-200/50 dark:border-white/10">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Fecha y Hora</th>
                        <th>Acción</th>
                        <th>Entidad</th>
                        <th>Usuario</th>
                        <th>Descripción</th>
                        <th>Origen</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditoria.items.map((e) => (
                        <tr key={e.id}>
                          <td className="font-mono text-xs whitespace-nowrap">{human(e.created_at)}</td>
                          <td>
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold uppercase bg-gray-100 dark:bg-white/10 text-gray-700 dark:text-gray-300">
                              {e.accion}
                            </span>
                          </td>
                          <td className="font-medium text-slate-900 dark:text-white">
                            {e.entidad}
                            {e.entidad_id ? ` #${e.entidad_id}` : ''}
                          </td>
                          <td className="font-mono text-xs">{e.usuario_id ?? 'Sistema'}</td>
                          <td className="text-xs max-w-xs truncate" title={e.descripcion || ''}>
                            {e.descripcion || '—'}
                          </td>
                          <td className="text-xs text-gray-500 dark:text-gray-400">{e.origen}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Audit Pagination */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-4 border-t border-gray-200/50 dark:border-white/10 text-xs text-gray-500 dark:text-gray-400">
                  <div className="flex items-center gap-2">
                    <span>Registros por página:</span>
                    <select
                      className="input-field py-1 px-2 text-xs w-20"
                      value={tamPagina}
                      onChange={(e) => {
                        setPagina(0);
                        setTamPagina(Number(e.target.value));
                      }}
                    >
                      <option value={10}>10</option>
                      <option value={25}>25</option>
                      <option value={50}>50</option>
                    </select>
                  </div>

                  <div className="flex items-center gap-2">
                    <span>
                      Página {pagina + 1} de {Math.max(1, Math.ceil(auditoria.total / tamPagina))}
                    </span>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={pagina === 0 || loading}
                        onClick={() => setPagina((p) => Math.max(0, p - 1))}
                        icon={<ChevronLeft className="h-3.5 w-3.5" />}
                      >
                        Anterior
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={(pagina + 1) * tamPagina >= auditoria.total || loading}
                        onClick={() => setPagina((p) => p + 1)}
                      >
                        Siguiente
                        <ChevronRight className="h-3.5 w-3.5 ml-1" />
                      </Button>
                    </div>
                  </div>
                </div>
              </>
            )}
          </GlassCard>
        </motion.div>
      )}
    </motion.div>
  );
};

export default IntelligenceView;
