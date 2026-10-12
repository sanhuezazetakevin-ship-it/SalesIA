import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import {
  DashboardComercialResponse,
  SerieVentasResponse,
  RankingItem,
} from '../types/api';

export const DashboardView: React.FC = () => {
  const hoy = new Date().toISOString().split('T')[0];
  const haceUnMes = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

  const [fechaInicio, setFechaInicio] = useState(haceUnMes);
  const [fechaFin, setFechaFin] = useState(hoy);
  const [agrupacion, setAgrupacion] = useState<'dia' | 'mes'>('dia');
  const [limite, setLimite] = useState(10);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dataComercial, setDataComercial] = useState<DashboardComercialResponse | null>(null);
  const [dataSerie, setDataSerie] = useState<SerieVentasResponse | null>(null);

  const cargarDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [comercial, serie] = await Promise.all([
        api.getDashboardComercial(fechaInicio, fechaFin, limite),
        api.getSerieVentas(fechaInicio, fechaFin, agrupacion),
      ]);
      setDataComercial(comercial);
      setDataSerie(serie);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error al cargar el dashboard';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [fechaInicio, fechaFin, limite, agrupacion]);

  useEffect(() => {
    cargarDashboard();
  }, [cargarDashboard]);

  // Gráfico SVG interactivo para Serie de Ventas
  const renderGraficoSerie = () => {
    if (!dataSerie || !dataSerie.puntos || dataSerie.puntos.length === 0) {
      return (
        <div className="empty-state">
          No hay ventas confirmadas en este intervalo de fechas ({fechaInicio} al {fechaFin}).
        </div>
      );
    }

    const puntos = dataSerie.puntos;
    const maxTotal = Math.max(...puntos.map((p) => parseFloat(p.total_ventas) || 0), 10);
    const width = 800;
    const height = 260;
    const padding = 45;

    const xStep = puntos.length > 1 ? (width - padding * 2) / (puntos.length - 1) : 0;
    const coords = puntos.map((p, idx) => {
      const x = puntos.length === 1 ? width / 2 : padding + idx * xStep;
      const val = parseFloat(p.total_ventas) || 0;
      const y = height - padding - (val / maxTotal) * (height - padding * 2);
      return { x, y, p, val };
    });

    const pathData = coords.reduce(
      (acc, c, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${c.x} ${c.y}`,
      ''
    );

    return (
      <div className="chart-box">
        <div className="chart-header">
          <span>Serie Temporal de Ventas ({agrupacion === 'dia' ? 'Por Día' : 'Por Mes'})</span>
          <span>Moneda: {dataSerie.moneda} | Criterio: {dataSerie.criterio_estado}</span>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto', maxHeight: '300px' }}>
            {/* Ejes */}
            <line
              x1={padding}
              y1={height - padding}
              x2={width - padding}
              y2={height - padding}
              stroke="#222"
              strokeWidth="2"
            />
            <line
              x1={padding}
              y1={padding}
              x2={padding}
              y2={height - padding}
              stroke="#222"
              strokeWidth="2"
            />

            {/* Guías horizontales */}
            {[0, 0.5, 1].map((pct, idx) => {
              const y = height - padding - pct * (height - padding * 2);
              const labelVal = (maxTotal * pct).toFixed(2);
              return (
                <g key={idx}>
                  <line
                    x1={padding}
                    y1={y}
                    x2={width - padding}
                    y2={y}
                    stroke="#eee"
                    strokeDasharray="4 4"
                  />
                  <text x={padding - 8} y={y + 4} fontSize="10" textAnchor="end" fill="#555">
                    {labelVal}
                  </text>
                </g>
              );
            })}

            {/* Línea del gráfico */}
            {coords.length > 1 && (
              <path d={pathData} fill="none" stroke="#111" strokeWidth="2.5" />
            )}

            {/* Puntos y etiquetas */}
            {coords.map((c, i) => (
              <g key={i}>
                <circle cx={c.x} cy={c.y} r="4" fill="#fff" stroke="#111" strokeWidth="2" />
                <text
                  x={c.x}
                  y={height - padding + 16}
                  fontSize="9"
                  textAnchor="middle"
                  fill="#333"
                  transform={puntos.length > 8 ? `rotate(45 ${c.x} ${height - padding + 16})` : undefined}
                >
                  {c.p.fecha.slice(5)}
                </text>
                <title>
                  {`Fecha: ${c.p.fecha}\nTotal: PEN ${c.p.total_ventas}\nCantidad: ${c.p.cantidad_ventas} ventas`}
                </title>
              </g>
            ))}
          </svg>
        </div>
        <div style={{ fontSize: '0.8rem', color: '#666', marginTop: '0.5rem' }}>
          * Pase el cursor sobre los puntos para ver el desglose exacto de transacciones e importe en Soles (PEN).
        </div>
      </div>
    );
  };

  // Renderizar tabla de ranking
  const renderRanking = (titulo: string, items?: RankingItem[]) => {
    if (!items || items.length === 0) {
      return (
        <div style={{ flex: 1, minWidth: '280px' }}>
          <h4 style={{ fontSize: '0.9rem', marginBottom: '0.4rem', borderBottom: '1px solid #ddd' }}>
            {titulo}
          </h4>
          <p style={{ fontSize: '0.8rem', color: '#777', padding: '0.5rem 0' }}>Sin datos en el período.</p>
        </div>
      );
    }

    const maxVal = Math.max(...items.map((it) => parseFloat(it.total) || 1), 1);

    return (
      <div style={{ flex: 1, minWidth: '280px' }}>
        <h4 style={{ fontSize: '0.9rem', marginBottom: '0.4rem', borderBottom: '1px solid #222' }}>
          {titulo}
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginTop: '0.5rem' }}>
          {items.map((item, idx) => {
            const val = parseFloat(item.total) || 0;
            const pct = Math.min(100, (val / maxVal) * 100);
            return (
              <div key={idx} style={{ fontSize: '0.8rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
                  <span>
                    <strong>#{idx + 1}</strong> {item.nombre}
                  </span>
                  <span>
                    PEN {item.total} <span style={{ color: '#777' }}>({item.cantidad} ops)</span>
                  </span>
                </div>
                <div style={{ height: '6px', backgroundColor: '#eee', border: '1px solid #ccc' }}>
                  <div style={{ height: '100%', width: `${pct}%`, backgroundColor: '#111' }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div>
      <div className="section-box">
        <h2 className="section-title">2. Dashboard Ejecutivo y Comercial</h2>

        {/* Filtros */}
        <div className="filter-bar">
          <div className="form-group">
            <label>Fecha Inicio:</label>
            <input
              type="date"
              value={fechaInicio}
              onChange={(e) => setFechaInicio(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label>Fecha Fin:</label>
            <input
              type="date"
              value={fechaFin}
              onChange={(e) => setFechaFin(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label>Agrupación Gráfica:</label>
            <select
              value={agrupacion}
              onChange={(e) => setAgrupacion(e.target.value as 'dia' | 'mes')}
            >
              <option value="dia">Por Día</option>
              <option value="mes">Por Mes</option>
            </select>
          </div>

          <div className="form-group">
            <label>Límite Rankings:</label>
            <select
              value={limite}
              onChange={(e) => setLimite(Number(e.target.value))}
            >
              <option value={5}>Top 5</option>
              <option value={10}>Top 10</option>
              <option value={20}>Top 20</option>
            </select>
          </div>

          <button onClick={cargarDashboard} disabled={loading} className="btn-primary">
            {loading ? 'Actualizando...' : 'Consultar'}
          </button>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        {/* Tarjetas KPI */}
        {dataComercial && (
          <div className="grid-cards">
            <div className="card">
              <div className="card-label">Total Ventas (PEN)</div>
              <div className="card-value">PEN {dataComercial.kpis.total_ventas}</div>
              <div className="card-sub">
                {dataComercial.variacion_porcentual_ventas
                  ? `Variación: ${dataComercial.variacion_porcentual_ventas}% vs período previo`
                  : 'Sin comparativa previa'}
              </div>
            </div>

            <div className="card">
              <div className="card-label">Cantidad de Ventas</div>
              <div className="card-value">{dataComercial.kpis.cantidad_ventas}</div>
              <div className="card-sub">
                {dataComercial.kpis_periodo_anterior
                  ? `Previo: ${dataComercial.kpis_periodo_anterior.cantidad_ventas} ventas`
                  : 'Transacciones confirmadas'}
              </div>
            </div>

            <div className="card">
              <div className="card-label">Ticket Promedio</div>
              <div className="card-value">
                {dataComercial.kpis.ticket_promedio ? `PEN ${dataComercial.kpis.ticket_promedio}` : 'N/A'}
              </div>
              <div className="card-sub">Media aritmética por transacción</div>
            </div>

            <div className="card">
              <div className="card-label">Estado de Pedidos</div>
              <div className="card-value" style={{ fontSize: '1.1rem' }}>
                {dataComercial.pedidos_por_estado
                  ? Object.entries(dataComercial.pedidos_por_estado)
                      .map(([k, v]) => `${k}: ${v}`)
                      .join(' | ') || '0 pedidos'
                  : '0'}
              </div>
              <div className="card-sub">Distribución de estados</div>
            </div>
          </div>
        )}

        {/* Serie de ventas */}
        {renderGraficoSerie()}

        {/* Rankings */}
        {dataComercial && (
          <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', marginTop: '1.5rem' }}>
            {renderRanking('Top Productos', dataComercial.productos_destacados)}
            {renderRanking('Top Clientes', dataComercial.clientes_destacados)}
            {renderRanking('Top Vendedores', dataComercial.vendedores_destacados)}
          </div>
        )}
      </div>
    </div>
  );
};
