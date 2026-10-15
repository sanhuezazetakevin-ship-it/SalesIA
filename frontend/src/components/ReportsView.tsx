import React, { useCallback, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Calendar,
  FileText,
  FileSpreadsheet,
  Download,
  Eye,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  HardDrive,
  Search,
  X,
  TrendingUp,
  BarChart2,
  Boxes,
  Users,
  Award,
  ChevronLeft,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import { api, ReporteHistorialF8, ReportePreviewF8 } from '../services/api';
import { ReporteTipo } from '../types/api';
import { GlassCard } from './ui/GlassCard';
import { Button } from './ui/Button';
import { Badge } from './ui/Badge';

interface TipoConfig {
  value: ReporteTipo;
  nombre: string;
  descripcion: string;
  icon: React.ComponentType<{ className?: string }>;
}

const TIPOS: TipoConfig[] = [
  {
    value: 'VENTAS',
    nombre: 'Ventas',
    descripcion: 'Operaciones comerciales registradas durante el periodo.',
    icon: TrendingUp,
  },
  {
    value: 'ESTADISTICO',
    nombre: 'Estadísticas',
    descripcion: 'Resumen de importes, valores extremos y promedios.',
    icon: BarChart2,
  },
  {
    value: 'INVENTARIO',
    nombre: 'Inventario',
    descripcion: 'Existencias y valores disponibles según el reporte del backend.',
    icon: Boxes,
  },
  {
    value: 'CLIENTES',
    nombre: 'Clientes',
    descripcion: 'Actividad comercial agrupada por cliente.',
    icon: Users,
  },
  {
    value: 'RENDIMIENTO',
    nombre: 'Vendedores',
    descripcion: 'Rendimiento comercial y conversiones por vendedor.',
    icon: Award,
  },
];

const fecha = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

const safeDate = (s: string) => {
  const d = new Date(s);
  return isNaN(d.getTime()) ? s : d.toLocaleString('es-PE');
};

const formatBytes = (bytes: number | null | undefined): string => {
  if (bytes === null || bytes === undefined || isNaN(bytes)) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
};

export const ReportsView: React.FC = () => {
  const [tipo, setTipo] = useState<ReporteTipo>('VENTAS');
  const [inicio, setInicio] = useState(fecha(new Date(Date.now() - 30 * 86400000)));
  const [fin, setFin] = useState(fecha(new Date()));
  const [preview, setPreview] = useState<ReportePreviewF8 | null>(null);
  const [historial, setHistorial] = useState<ReporteHistorialF8[]>([]);
  const [filtro, setFiltro] = useState('');
  const [cargando, setCargando] = useState(false);
  const [procesando, setProcesando] = useState(false);
  const [error, setError] = useState('');
  const [aviso, setAviso] = useState('');
  const [errorHistorial, setErrorHistorial] = useState('');

  // Selected report in history
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  const [detailModalReport, setDetailModalReport] = useState<ReporteHistorialF8 | null>(null);

  // Preview table pagination
  const [previewPage, setPreviewPage] = useState(0);
  const previewPageSize = 10;

  const invalido =
    !inicio || !fin || inicio > fin || (new Date(fin).getTime() - new Date(inicio).getTime()) / 86400000 > 366;

  const cargarHistorial = useCallback(async () => {
    try {
      const data = await api.historialReportesF8(100);
      setHistorial(data.items);
      setErrorHistorial('');
    } catch (e) {
      setErrorHistorial(e instanceof Error ? e.message : 'No se pudo consultar el historial.');
    }
  }, []);

  useEffect(() => {
    void cargarHistorial();
  }, [cargarHistorial]);

  useEffect(() => {
    if (invalido) {
      setPreview(null);
      return;
    }
    let activo = true;
    setCargando(true);
    setError('');
    setPreview(null);
    setPreviewPage(0);

    const t = window.setTimeout(() => {
      api
        .previsualizarReporteF8(tipo, inicio, fin, 100)
        .then((data) => {
          if (activo) setPreview(data);
        })
        .catch((e) => {
          if (activo) setError(e instanceof Error ? e.message : 'No se pudo cargar el reporte.');
        })
        .finally(() => {
          if (activo) setCargando(false);
        });
    }, 350);

    return () => {
      activo = false;
      window.clearTimeout(t);
    };
  }, [tipo, inicio, fin, invalido]);

  const generar = async (formato: 'CSV' | 'XLSX' | 'PDF') => {
    if (invalido) return;
    setProcesando(true);
    setError('');
    setAviso('');
    try {
      const r = await api.generarReporteF8(tipo, formato, inicio, fin);
      setAviso(`Reporte ${formato} generado y registrado con el número #${r.id}.`);
      await cargarHistorial();
      setSelectedReportId(r.id);
      try {
        await api.descargarReporteGuardadoF8(r.id, formato);
      } catch {
        setAviso(
          `Reporte #${r.id} registrado. La descarga directa no está disponible en este entorno; puedes reintentar desde el historial.`
        );
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo generar el reporte.');
    } finally {
      setProcesando(false);
    }
  };

  const descargarDirecto = async () => {
    if (invalido) return;
    setProcesando(true);
    setError('');
    setAviso('');
    try {
      await api.descargarReportePdf(tipo, inicio, fin);
      setAviso('PDF visual descargado exitosamente. Este formato directo no se almacena en el historial.');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo descargar el PDF.');
    } finally {
      setProcesando(false);
    }
  };

  const handleDescargarHistorial = async (item: ReporteHistorialF8) => {
    setError('');
    try {
      await api.descargarReporteGuardadoF8(item.id, item.formato);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Archivo no disponible para descarga.');
    }
  };

  const filasFiltradas = historial.filter((r) =>
    `${r.nombre} ${r.tipo} ${r.formato} ${r.estado}`.toLowerCase().includes(filtro.toLowerCase())
  );

  const selectedReport = historial.find((r) => r.id === selectedReportId) || null;

  // Pagination slice for preview
  const previewRows = preview?.filas || [];
  const totalPreviewPages = Math.max(1, Math.ceil(previewRows.length / previewPageSize));
  const currentPreviewRows = previewRows.slice(
    previewPage * previewPageSize,
    (previewPage + 1) * previewPageSize
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="space-y-6 pb-20"
    >
      {/* Header */}
      <div className="glass p-5 md:p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4 border border-[#D97843]/20 dark:border-white/10 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-extrabold uppercase tracking-wider bg-slate-200/80 dark:bg-white/15 text-slate-800 dark:text-slate-200">
              MÓDULO DE REPORTES / FASE 8
            </span>
          </div>
          <h2 className="text-2xl md:text-3xl font-black tracking-tight text-slate-950 dark:text-white mt-1.5 flex items-center gap-2.5 drop-shadow-sm">
            <FileSpreadsheet className="h-7 w-7 text-[#D97843] dark:text-[#FFA675]" />
            Reportes Empresariales y Exportación
          </h2>
          <p className="text-sm text-slate-700 dark:text-slate-200 font-medium mt-1">
            Previsualiza los datos de tu empresa en tiempo real y descarga documentos certificados en CSV, XLSX y PDF.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={() => void cargarHistorial()}
          icon={<RefreshCw className="h-4 w-4 text-cyan-500" />}
        >
          Actualizar Historial
        </Button>
      </div>

      {/* Date Range Selector in Glass Card with Calendar Icon */}
      <GlassCard className="p-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-gray-200/50 dark:border-white/10">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-500 border border-cyan-500/20">
              <Calendar className="h-6 w-6" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-900 dark:text-white">Rango de Fechas del Reporte</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Selecciona el intervalo a consultar (máximo 366 días de operaciones).
              </p>
            </div>
          </div>
          {invalido && (
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
              <AlertCircle className="h-4 w-4" />
              Intervalo no válido: verifica el orden de las fechas y límite de 366 días.
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-4 items-end">
          <div>
            <label htmlFor="r8inicio" className="input-label flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5 text-cyan-500" />
              Fecha Desde
            </label>
            <input
              id="r8inicio"
              type="date"
              className="input-field"
              value={inicio}
              onChange={(e) => setInicio(e.target.value)}
            />
          </div>

          <div>
            <label htmlFor="r8fin" className="input-label flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5 text-cyan-500" />
              Fecha Hasta
            </label>
            <input
              id="r8fin"
              type="date"
              className="input-field"
              value={fin}
              onChange={(e) => setFin(e.target.value)}
            />
          </div>

          <div className="sm:col-span-2 flex items-center gap-2">
            <div className="text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-white/5 p-3 rounded-lg border border-gray-200/50 dark:border-white/5 flex-1">
              <span className="font-semibold text-slate-800 dark:text-gray-200 block">Tipo Activo:</span>
              {TIPOS.find((x) => x.value === tipo)?.descripcion}
            </div>
          </div>
        </div>
      </GlassCard>

      {/* Report Type Selector: Grid of Report Types */}
      <div>
        <label className="input-label mb-2 block">Selecciona el tipo de informe</label>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {TIPOS.map((t) => {
            const Icon = t.icon;
            const isSelected = tipo === t.value;
            return (
              <button
                key={t.value}
                type="button"
                onClick={() => setTipo(t.value)}
                className={`p-4 rounded-xl text-left transition-all duration-200 flex flex-col justify-between border ${
                  isSelected
                    ? 'backdrop-blur-xl bg-blue-600/10 dark:bg-cyan-500/10 border-blue-500 dark:border-cyan-500 ring-2 ring-blue-500/30 dark:ring-cyan-500/30 shadow-glow'
                    : 'backdrop-blur-xl bg-white/80 dark:bg-white/5 border-gray-200/50 dark:border-white/10 hover:border-gray-300 dark:hover:border-white/20'
                }`}
              >
                <div className="flex items-center justify-between w-full mb-3">
                  <div
                    className={`p-2 rounded-lg ${
                      isSelected
                        ? 'bg-blue-600 text-white dark:bg-cyan-500 dark:text-slate-950'
                        : 'bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-400'
                    }`}
                  >
                    <Icon className="h-5 w-5" />
                  </div>
                  {isSelected && (
                    <span className="w-2 h-2 rounded-full bg-blue-600 dark:bg-cyan-400 shadow-[0_0_8px_#06b6d4]" />
                  )}
                </div>
                <div>
                  <h4 className="font-semibold text-sm text-slate-900 dark:text-white">{t.nombre}</h4>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">{t.descripcion}</p>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Alerts */}
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

      {/* Generation Bar: Button Primary for Each Format */}
      <GlassCard className="p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <Download className="h-5 w-5 text-cyan-500" />
              Generar y Descargar Reporte
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              Los formatos CSV, XLSX y PDF se guardan en el servidor y quedan registrados en tu historial.
            </p>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            <Button
              variant="primary"
              size="sm"
              disabled={invalido || procesando}
              onClick={() => generar('CSV')}
              icon={<FileSpreadsheet className="h-4 w-4" />}
            >
              Descargar CSV
            </Button>
            <Button
              variant="primary"
              size="sm"
              disabled={invalido || procesando}
              onClick={() => generar('XLSX')}
              icon={<FileSpreadsheet className="h-4 w-4" />}
              className="bg-emerald-600 hover:bg-emerald-700 focus:ring-emerald-500"
            >
              Descargar Excel
            </Button>
            <Button
              variant="primary"
              size="sm"
              disabled={invalido || procesando}
              onClick={() => generar('PDF')}
              icon={<FileText className="h-4 w-4" />}
              className="bg-rose-600 hover:bg-rose-700 focus:ring-rose-500"
            >
              Generar PDF Guardado
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={invalido || procesando}
              onClick={descargarDirecto}
              icon={<Download className="h-4 w-4 text-cyan-500" />}
            >
              PDF Inmediato
            </Button>
          </div>
        </div>
      </GlassCard>

      {/* Preview Section: data-table in Glass Card */}
      <GlassCard className="p-6 overflow-hidden">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div>
            <h3 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <Eye className="h-5 w-5 text-cyan-500" />
              Previsualización de Datos ({tipo})
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              {cargando
                ? 'Consultando FastAPI...'
                : preview
                ? `${preview.total_filas} registros encontrados · Moneda: ${preview.moneda} · Zona: ${preview.zona_horaria}`
                : 'Sin resultados calculados aún'}
            </p>
          </div>

          {preview && preview.total_filas > preview.filas.length && (
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
              Vista preliminar: primeros {preview.filas.length} registros
            </span>
          )}
        </div>

        {cargando ? (
          <div className="py-16 flex flex-col items-center justify-center text-gray-400 space-y-3">
            <RefreshCw className="h-8 w-8 animate-spin text-cyan-500" />
            <p className="text-sm">Generando vista preliminar desde PostgreSQL...</p>
          </div>
        ) : preview && preview.filas.length > 0 ? (
          <>
            <div className="overflow-x-auto rounded-lg border border-gray-200/50 dark:border-white/10">
              <table className="data-table">
                <thead>
                  <tr>
                    {preview.columnas.map((col, idx) => (
                      <th key={idx}>{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {currentPreviewRows.map((row, rIdx) => (
                    <tr key={rIdx}>
                      {row.map((val, cIdx) => (
                        <td key={cIdx} className="font-mono text-xs">
                          {val === null || val === undefined ? '—' : String(val)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination controls for preview */}
            <div className="flex items-center justify-between pt-4 border-t border-gray-200/50 dark:border-white/10 text-xs text-gray-500 dark:text-gray-400">
              <span>
                Mostrando {previewPage * previewPageSize + 1} -{' '}
                {Math.min((previewPage + 1) * previewPageSize, previewRows.length)} de {previewRows.length} filas
              </span>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  disabled={previewPage === 0}
                  onClick={() => setPreviewPage((p) => Math.max(0, p - 1))}
                  className="pagination-btn flex items-center gap-1"
                >
                  <ChevronLeft className="h-3.5 w-3.5" />
                  Anterior
                </button>
                <span className="px-2">
                  {previewPage + 1} / {totalPreviewPages}
                </span>
                <button
                  type="button"
                  disabled={previewPage >= totalPreviewPages - 1}
                  onClick={() => setPreviewPage((p) => p + 1)}
                  className="pagination-btn flex items-center gap-1"
                >
                  Siguiente
                  <ChevronRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="py-12 text-center text-gray-400">
            <FileText className="h-10 w-10 mx-auto mb-2 opacity-40 text-gray-400" />
            <p className="text-sm font-medium">No se encontraron operaciones registradas para este periodo y tipo.</p>
            <p className="text-xs text-gray-500 mt-1">Prueba seleccionando otro rango de fechas o tipo de reporte.</p>
          </div>
        )}
      </GlassCard>

      {/* History List: Glass Cards in grid-cols-1 md:grid-cols-2 lg:grid-cols-3 */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <HardDrive className="h-5 w-5 text-cyan-500" />
              Historial de Reportes Generados
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Archivos persistidos en el servidor listos para consulta y descarga reiterada.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                id="r8buscar"
                type="text"
                className="input-field pl-9 py-1.5 text-xs w-64"
                placeholder="Buscar por nombre, formato, estado..."
                value={filtro}
                onChange={(e) => setFiltro(e.target.value)}
              />
            </div>
          </div>
        </div>

        {errorHistorial && (
          <div className="alert-card alert-info text-xs">
            <AlertCircle className="h-4 w-4 shrink-0 text-blue-500" />
            {errorHistorial}
          </div>
        )}

        {filasFiltradas.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filasFiltradas.map((item) => {
              const isSelected = selectedReportId === item.id;
              const isSpreadsheet = item.formato === 'CSV' || item.formato === 'XLSX';

              return (
                <GlassCard
                  key={item.id}
                  hover
                  onClick={() => setSelectedReportId(isSelected ? null : item.id)}
                  className={`p-4 flex flex-col justify-between transition-all duration-200 cursor-pointer ${
                    isSelected
                      ? 'border-blue-500 ring-2 ring-blue-500/30 dark:border-cyan-500 dark:ring-cyan-500/30 shadow-glow'
                      : ''
                  }`}
                >
                  <div>
                    {/* Top row */}
                    <div className="flex items-center justify-between mb-2.5">
                      <div className="flex items-center gap-2">
                        <div
                          className={`p-2 rounded-lg ${
                            isSpreadsheet
                              ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
                              : 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20'
                          }`}
                        >
                          {isSpreadsheet ? (
                            <FileSpreadsheet className="h-4 w-4" />
                          ) : (
                            <FileText className="h-4 w-4" />
                          )}
                        </div>
                        <div>
                          <span className="text-[11px] font-mono font-bold text-gray-500 dark:text-gray-400">
                            #{item.id}
                          </span>
                          <span className="ml-1.5 inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold uppercase bg-gray-100 dark:bg-white/10 text-gray-700 dark:text-gray-300">
                            {item.formato}
                          </span>
                        </div>
                      </div>

                      <Badge
                        variant={
                          item.estado === 'COMPLETADO'
                            ? 'success'
                            : item.estado === 'FALLIDO'
                            ? 'danger'
                            : 'warning'
                        }
                      >
                        {item.estado}
                      </Badge>
                    </div>

                    {/* Title */}
                    <h4 className="font-semibold text-sm text-slate-900 dark:text-white line-clamp-1">
                      {item.nombre}
                    </h4>

                    {/* Metadata */}
                    <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mt-2 pt-2 border-t border-gray-100 dark:border-white/5">
                      <span>{safeDate(item.created_at)}</span>
                      <span className="font-mono">{formatBytes(item.tamano_bytes)}</span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center justify-end gap-2 mt-4 pt-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDetailModalReport(item);
                        setSelectedReportId(item.id);
                      }}
                      icon={<Eye className="h-3.5 w-3.5" />}
                    >
                      Ver
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={procesando || item.estado !== 'COMPLETADO'}
                      onClick={(e) => {
                        e.stopPropagation();
                        void handleDescargarHistorial(item);
                      }}
                      icon={<Download className="h-3.5 w-3.5" />}
                    >
                      Descargar
                    </Button>
                  </div>
                </GlassCard>
              );
            })}
          </div>
        ) : (
          <GlassCard className="p-8 text-center text-gray-400">
            <FileSpreadsheet className="h-10 w-10 mx-auto mb-2 opacity-40 text-gray-400" />
            <p className="text-sm font-medium">No hay reportes registrados que coincidan con la búsqueda.</p>
          </GlassCard>
        )}
      </div>

      {/* Sticky Bottom Bar for Selection */}
      <AnimatePresence>
        {selectedReport && (
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 50 }}
            transition={{ duration: 0.2 }}
            className="fixed bottom-4 left-4 right-4 md:left-72 md:right-8 z-40"
          >
            <div className="backdrop-blur-2xl bg-slate-900/95 dark:bg-[#12121A]/95 text-white p-4 rounded-xl shadow-2xl border border-cyan-500/30 flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-cyan-500/20 text-cyan-400">
                  <CheckCircle2 className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm font-semibold flex items-center gap-2">
                    Reporte #{selectedReport.id}: {selectedReport.nombre}
                    <span className="text-xs px-2 py-0.5 rounded bg-white/10 font-mono text-cyan-300">
                      {selectedReport.formato}
                    </span>
                  </p>
                  <p className="text-xs text-gray-400">
                    {safeDate(selectedReport.created_at)} · {formatBytes(selectedReport.tamano_bytes)} · Estado:{' '}
                    {selectedReport.estado}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 self-end sm:self-auto">
                <Button
                  variant="primary"
                  size="sm"
                  disabled={selectedReport.estado !== 'COMPLETADO'}
                  onClick={() => void handleDescargarHistorial(selectedReport)}
                  icon={<Download className="h-4 w-4" />}
                >
                  Descargar Archivo
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedReportId(null)}
                  className="text-gray-300 hover:text-white"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Detail Modal */}
      <AnimatePresence>
        {detailModalReport && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white dark:bg-[#12121A] border border-gray-200 dark:border-white/10 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4"
            >
              <div className="flex items-center justify-between pb-3 border-b border-gray-100 dark:border-white/10">
                <h3 className="font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <FileText className="h-5 w-5 text-cyan-500" />
                  Detalle del Reporte #{detailModalReport.id}
                </h3>
                <button
                  type="button"
                  onClick={() => setDetailModalReport(null)}
                  className="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-white/10 text-gray-400 hover:text-gray-200"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="space-y-3 text-sm">
                <div>
                  <span className="text-xs uppercase text-gray-500 dark:text-gray-400 block font-semibold">
                    Nombre
                  </span>
                  <p className="font-medium text-slate-900 dark:text-white">{detailModalReport.nombre}</p>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <span className="text-xs uppercase text-gray-500 dark:text-gray-400 block font-semibold">
                      Tipo
                    </span>
                    <p className="font-mono text-slate-800 dark:text-gray-200">{detailModalReport.tipo}</p>
                  </div>
                  <div>
                    <span className="text-xs uppercase text-gray-500 dark:text-gray-400 block font-semibold">
                      Formato
                    </span>
                    <p className="font-mono text-slate-800 dark:text-gray-200">{detailModalReport.formato}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <span className="text-xs uppercase text-gray-500 dark:text-gray-400 block font-semibold">
                      Estado
                    </span>
                    <Badge
                      variant={
                        detailModalReport.estado === 'COMPLETADO'
                          ? 'success'
                          : detailModalReport.estado === 'FALLIDO'
                          ? 'danger'
                          : 'warning'
                      }
                    >
                      {detailModalReport.estado}
                    </Badge>
                  </div>
                  <div>
                    <span className="text-xs uppercase text-gray-500 dark:text-gray-400 block font-semibold">
                      Tamaño
                    </span>
                    <p className="font-mono text-slate-800 dark:text-gray-200">
                      {formatBytes(detailModalReport.tamano_bytes)}
                    </p>
                  </div>
                </div>

                <div>
                  <span className="text-xs uppercase text-gray-500 dark:text-gray-400 block font-semibold">
                    Fecha de Creación
                  </span>
                  <p className="text-slate-800 dark:text-gray-200">{safeDate(detailModalReport.created_at)}</p>
                </div>
              </div>

              <div className="pt-3 border-t border-gray-100 dark:border-white/10 flex items-center justify-end gap-2">
                <Button variant="outline" size="sm" onClick={() => setDetailModalReport(null)}>
                  Cerrar
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  disabled={detailModalReport.estado !== 'COMPLETADO'}
                  onClick={() => {
                    void handleDescargarHistorial(detailModalReport);
                    setDetailModalReport(null);
                  }}
                  icon={<Download className="h-4 w-4" />}
                >
                  Descargar
                </Button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default ReportsView;
