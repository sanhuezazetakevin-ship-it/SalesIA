import React from 'react';
import { AlertCircle, AlertTriangle, CheckCircle, HelpCircle } from 'lucide-react';

export interface StockRunwayBadgeProps {
  stockActual: number | string | null | undefined;
  demandaEstimada?: number | string | null | undefined;
  diasCoberturaDirecto?: number | string | null | undefined;
  riesgoSugerido?: string | null | undefined;
  compact?: boolean;
  className?: string;
}

export const StockRunwayBadge: React.FC<StockRunwayBadgeProps> = ({
  stockActual,
  demandaEstimada,
  diasCoberturaDirecto,
  riesgoSugerido,
  compact = false,
  className = '',
}) => {
  const stock = Number(stockActual) || 0;
  const demanda = Number(demandaEstimada) || 0;

  // Calcular días de cobertura:
  // Si viene explícito, usarlo. Si no, calcular: stock / (demanda 14 días / 14)
  let dias: number | null = null;
  if (diasCoberturaDirecto !== undefined && diasCoberturaDirecto !== null && !isNaN(Number(diasCoberturaDirecto))) {
    dias = Math.round(Number(diasCoberturaDirecto));
  } else if (demanda > 0) {
    const demandaDiaria = demanda / 14;
    dias = Math.max(0, Math.round(stock / demandaDiaria));
  }

  // Determinar nivel de salud
  let nivel: 'critico' | 'preventivo' | 'optimo' | 'sin_movimiento';
  if (riesgoSugerido === 'SIN_HISTORIAL' || (demanda === 0 && dias === null)) {
    nivel = 'sin_movimiento';
  } else if (stock <= 0) {
    nivel = 'critico';
    dias = 0;
  } else if (dias !== null && dias <= 7) {
    nivel = 'critico';
  } else if (dias !== null && dias <= 15) {
    nivel = 'preventivo';
  } else if (dias !== null && dias > 15) {
    nivel = 'optimo';
  } else {
    nivel = riesgoSugerido === 'ALTO' ? 'critico' : riesgoSugerido === 'MEDIO' ? 'preventivo' : 'optimo';
  }

  // Porcentaje para la barra visual (tope en 30 días para 100%)
  const maxDiasVisual = 30;
  const porcentaje = dias !== null ? Math.min(100, Math.round((dias / maxDiasVisual) * 100)) : 0;

  if (compact) {
    switch (nivel) {
      case 'critico':
        return (
          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-rose-500/15 text-rose-500 dark:text-rose-400 border border-rose-500/30 ${className}`}>
            <AlertCircle className="w-3 h-3" />
            {dias !== null ? `${dias}d cobertura` : 'Quiebre inminente'}
          </span>
        );
      case 'preventivo':
        return (
          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/15 text-amber-500 dark:text-amber-400 border border-amber-500/30 ${className}`}>
            <AlertTriangle className="w-3 h-3" />
            {dias !== null ? `${dias}d cobertura` : 'Reordenar'}
          </span>
        );
      case 'optimo':
        return (
          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 ${className}`}>
            <CheckCircle className="w-3 h-3" />
            {dias !== null ? `${dias}d óptimo` : 'Saludable'}
          </span>
        );
      case 'sin_movimiento':
      default:
        return (
          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-gray-500/10 text-gray-500 dark:text-gray-400 border border-gray-500/20 ${className}`}>
            <HelpCircle className="w-3 h-3" />
            Sin rotación
          </span>
        );
    }
  }

  // Modo detallado con Gauge / Runway horizontal
  return (
    <div className={`p-2.5 rounded-xl border transition-all ${
      nivel === 'critico'
        ? 'bg-rose-500/5 border-rose-500/30 dark:bg-rose-950/20'
        : nivel === 'preventivo'
        ? 'bg-amber-500/5 border-amber-500/30 dark:bg-amber-950/20'
        : nivel === 'optimo'
        ? 'bg-emerald-500/5 border-emerald-500/30 dark:bg-emerald-950/20'
        : 'bg-slate-500/5 border-slate-500/20 dark:bg-slate-900/30'
    } ${className}`}>
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-1.5">
          {nivel === 'critico' && <AlertCircle className="w-3.5 h-3.5 text-rose-500 animate-pulse" />}
          {nivel === 'preventivo' && <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />}
          {nivel === 'optimo' && <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />}
          {nivel === 'sin_movimiento' && <HelpCircle className="w-3.5 h-3.5 text-gray-400" />}
          <span className="text-xs font-semibold">
            {nivel === 'critico' && <span className="text-rose-500 dark:text-rose-400">Riesgo Quiebre</span>}
            {nivel === 'preventivo' && <span className="text-amber-500 dark:text-amber-400">Reabastecer</span>}
            {nivel === 'optimo' && <span className="text-emerald-500 dark:text-emerald-400">Stock Óptimo</span>}
            {nivel === 'sin_movimiento' && <span className="text-gray-400">Sin Rotación</span>}
          </span>
        </div>
        <span className="text-xs font-mono font-bold">
          {dias !== null ? (
            <span className={nivel === 'critico' ? 'text-rose-400' : nivel === 'preventivo' ? 'text-amber-400' : 'text-emerald-400'}>
              {dias} {dias === 1 ? 'día' : 'días'}
            </span>
          ) : (
            <span className="text-gray-400 text-[11px]">N/D</span>
          )}
        </span>
      </div>

      {/* Barra de progreso de cobertura (Runway Bar) */}
      <div className="w-full h-1.5 bg-gray-200 dark:bg-white/10 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-500 rounded-full ${
            nivel === 'critico'
              ? 'bg-rose-500'
              : nivel === 'preventivo'
              ? 'bg-amber-500'
              : nivel === 'optimo'
              ? 'bg-emerald-500'
              : 'bg-gray-400'
          }`}
          style={{ width: `${Math.max(5, porcentaje)}%` }}
        />
      </div>

      <div className="flex justify-between items-center text-[10px] text-gray-400 dark:text-gray-500 mt-1">
        <span>0d quiebre</span>
        <span>15d alerta</span>
        <span>&gt;30d seguro</span>
      </div>
    </div>
  );
};
export default StockRunwayBadge;
