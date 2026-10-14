import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { api } from '../services/api';
import {
  DashboardComercialResponse,
  SerieVentasResponse,
  RankingItem,
  AnalyticsResumenResponse,
  AnalyticsProbabilidadesResponse,
  AnalyticsDistribucionesResponse,
  Semana08Response,
} from '../types/api';

const fechaLocal = (date: Date): string => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const soles = (valor: string | number | null | undefined): string =>
  valor === null || valor === undefined || valor === '' || !Number.isFinite(Number(valor))
    ? 'N/D'
    : new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(Number(valor));

const numero = (valor: string | number | null | undefined): number => {
  const n = Number(valor);
  return Number.isFinite(n) ? n : 0;
};

const decimal = (valor: string | number | null | undefined, max = 2): string => {
  const n = Number(valor);
  return Number.isFinite(n) ? n.toFixed(max) : 'N/D';
};

const porcentajeTexto = (valor: string | number | null | undefined): string => {
  const n = Number(valor);
  return Number.isFinite(n) ? `${n.toFixed(2)}%` : 'N/D';
};

const capitalizar = (texto: string): string =>
  texto
    .toLowerCase()
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((parte) => parte.charAt(0).toUpperCase() + parte.slice(1))
    .join(' ');

const csvCelda = (valor: string | number): string => {
  const texto = String(valor);
  const seguro = /^[\s]*[=+@-]/.test(texto) ? `'${texto}` : texto;
  return `"${seguro.replace(/"/g, '""')}"`;
};

export const DashboardView: React.FC = () => {
  const hoy = fechaLocal(new Date());
  const haceUnMes = fechaLocal(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000));

  const [fechaInicio, setFechaInicio] = useState(haceUnMes);
  const [fechaFin, setFechaFin] = useState(hoy);
  const [agrupacion, setAgrupacion] = useState<'dia' | 'mes'>('dia');
  const [limite, setLimite] = useState(10);

  const [loading, setLoading] = useState(false);
  const requestId = useRef(0);
  const [error, setError] = useState<string | null>(null);
  const [erroresComplementarios, setErroresComplementarios] = useState<string[]>([]);

  const [dataComercial, setDataComercial] = useState<DashboardComercialResponse | null>(null);
  const [dataSerie, setDataSerie] = useState<SerieVentasResponse | null>(null);
  const [analyticsResumen, setAnalyticsResumen] = useState<AnalyticsResumenResponse | null>(null);
  const [analyticsProbabilidades, setAnalyticsProbabilidades] = useState<AnalyticsProbabilidadesResponse | null>(null);
  const [analyticsDistribuciones, setAnalyticsDistribuciones] = useState<AnalyticsDistribucionesResponse | null>(null);
  const [analyticsSemana08, setAnalyticsSemana08] = useState<Semana08Response | null>(null);

  const rangoInvalido = !fechaInicio || !fechaFin || fechaInicio > fechaFin;

  const cargarDashboard = useCallback(async () => {
    const id = ++requestId.current;
    if (!fechaInicio || !fechaFin || fechaInicio > fechaFin) {
      setError('Selecciona un rango válido: la fecha inicial no puede ser posterior a la final.');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    setErroresComplementarios([]);

    try {
      const [comercial, serie] = await Promise.all([
        api.getDashboardComercial(fechaInicio, fechaFin, limite),
        api.getSerieVentas(fechaInicio, fechaFin, agrupacion),
      ]);

      if (id !== requestId.current) return;
      setDataComercial(comercial);
      setDataSerie(serie);

      const extras = await Promise.allSettled([
        api.getAnalyticsResumen(fechaInicio, fechaFin),
        api.getAnalyticsProbabilidades(fechaInicio, fechaFin, '100.00'),
        api.getAnalyticsDistribuciones(fechaInicio, fechaFin, 'estado_pago', 5),
        api.getSemana08(fechaInicio, fechaFin, undefined, 0.05),
      ]);

      if (id !== requestId.current) return;

      const mensajes: string[] = [];

      if (extras[0].status === 'fulfilled') setAnalyticsResumen(extras[0].value);
      else {
        setAnalyticsResumen(null);
        mensajes.push('No fue posible cargar el resumen estadístico.');
      }

      if (extras[1].status === 'fulfilled') setAnalyticsProbabilidades(extras[1].value);
      else {
        setAnalyticsProbabilidades(null);
        mensajes.push('No fue posible cargar el módulo de probabilidades.');
      }

      if (extras[2].status === 'fulfilled') setAnalyticsDistribuciones(extras[2].value);
      else {
        setAnalyticsDistribuciones(null);
        mensajes.push('No fue posible cargar la distribución de estados de pago.');
      }

      if (extras[3].status === 'fulfilled') setAnalyticsSemana08(extras[3].value);
      else {
        setAnalyticsSemana08(null);
        mensajes.push('No fue posible cargar el bloque de dispersión e hipótesis.');
      }

      setErroresComplementarios(mensajes);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error al cargar el dashboard';
      if (id === requestId.current) {
        setError(msg);
        setDataComercial(null);
        setDataSerie(null);
      }
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, [fechaInicio, fechaFin, limite, agrupacion]);

  useEffect(() => {
    cargarDashboard();
  }, [cargarDashboard]);

  const exportarCSV = () => {
    if (!dataSerie?.puntos?.length) return;
    const filas = [
      ['Fecha', 'Cantidad de ventas', 'Total de ventas (PEN)'],
      ...dataSerie.puntos.map((p) => [p.fecha, p.cantidad_ventas, p.total_ventas]),
    ];
    const contenido = '\uFEFF' + filas.map((f) => f.map(csvCelda).join(';')).join('\r\n');
    const url = URL.createObjectURL(new Blob([contenido], { type: 'text/csv;charset=utf-8;' }));
    const enlace = document.createElement('a');
    enlace.href = url;
    enlace.download = `salesia_ventas_${fechaInicio}_${fechaFin}_${agrupacion}.csv`;
    enlace.click();
    URL.revokeObjectURL(url);
  };

  const totalPedidos = dataComercial?.pedidos_por_estado
    ? Object.values(dataComercial.pedidos_por_estado).reduce((a, b) => a + b, 0)
    : null;

  const kpisEstadisticos = useMemo(() => {
    const cantidadVentas = dataComercial?.kpis.cantidad_ventas ?? analyticsResumen?.cantidad_ventas ?? 0;
    const totalVentas = numero(dataComercial?.kpis.total_ventas ?? analyticsResumen?.total_ventas ?? 0);
    const promedio = numero(dataComercial?.kpis.ticket_promedio ?? analyticsResumen?.ticket_promedio ?? 0);
    const mediana = numero(analyticsResumen?.mediana_ventas ?? analyticsSemana08?.resultados?.mediana ?? analyticsSemana08?.mediana ?? 0);
    const dispersion = analyticsSemana08?.resultados?.desviacion_muestral ?? analyticsSemana08?.desviacion_muestral;
    const periodoAnterior = numero(dataComercial?.kpis_periodo_anterior?.total_ventas ?? 0);
    const promedioDiario = dataSerie?.puntos?.length ? totalVentas / dataSerie.puntos.length : 0;

    return { cantidadVentas, totalVentas, promedio, mediana, dispersion, periodoAnterior, promedioDiario };
  }, [dataComercial, analyticsResumen, analyticsSemana08, dataSerie]);

  const estadoPedidoPrincipal = useMemo(() => {
    if (!dataComercial?.pedidos_por_estado) return null;
    const entries = Object.entries(dataComercial.pedidos_por_estado);
    if (!entries.length) return null;
    const [estado, cantidad] = entries.reduce((max, actual) => (actual[1] > max[1] ? actual : max));
    return { estado, cantidad };
  }, [dataComercial]);

  const insightsEjecutivos = useMemo(() => {
    const lista: string[] = [];

    if (dataComercial) {
      lista.push(
        `En el periodo seleccionado se registraron ${dataComercial.kpis.cantidad_ventas} ventas confirmadas por un total de ${soles(dataComercial.kpis.total_ventas)}.`
      );
    }

    if (analyticsResumen?.mediana_ventas) {
      const media = numero(dataComercial?.kpis.ticket_promedio ?? analyticsResumen.ticket_promedio);
      const mediana = numero(analyticsResumen.mediana_ventas);
      if (media > 0 && mediana > 0) {
        lista.push(
          media > mediana
            ? `La media (${soles(media)}) es superior a la mediana (${soles(mediana)}), lo que sugiere operaciones altas que empujan el promedio.`
            : `La media (${soles(media)}) y la mediana (${soles(mediana)}) se mantienen cercanas, lo que indica un comportamiento de ventas más equilibrado.`
        );
      }
    }

    if (estadoPedidoPrincipal) {
      lista.push(
        `El estado con mayor presencia en pedidos es ${capitalizar(estadoPedidoPrincipal.estado)} con ${estadoPedidoPrincipal.cantidad} registros.`
      );
    }

    if (analyticsProbabilidades?.probabilidad_pagado_dado_alto) {
      lista.push(
        `La probabilidad de que una venta de importe alto esté pagada es ${analyticsProbabilidades.probabilidad_pagado_dado_alto}.`
      );
    }

    if (dataComercial?.variacion_porcentual_ventas !== null && dataComercial?.variacion_porcentual_ventas !== undefined) {
      const varNum = Number(dataComercial.variacion_porcentual_ventas);
      if (Number.isFinite(varNum)) {
        lista.push(
          varNum >= 0
            ? `Las ventas crecieron ${varNum.toFixed(2)}% respecto al periodo anterior.`
            : `Las ventas disminuyeron ${Math.abs(varNum).toFixed(2)}% respecto al periodo anterior.`
        );
      }
    }

    if (!lista.length) {
      lista.push('Cuando existan ventas, comparativas y datos estadísticos, aquí se mostrará un resumen ejecutivo automático para la toma de decisiones.');
    }

    return lista.slice(0, 5);
  }, [dataComercial, analyticsResumen, analyticsProbabilidades, estadoPedidoPrincipal]);

  const tarjetasPrincipales = [
    {
      titulo: 'Ventas Totales',
      valor: soles(dataComercial?.kpis.total_ventas),
      ayuda: 'Importe total confirmado dentro del rango consultado.',
      meta: dataComercial?.moneda || 'PEN',
    },
    {
      titulo: 'Cantidad de Ventas',
      valor: String(dataComercial?.kpis.cantidad_ventas ?? 0),
      ayuda: 'Operaciones confirmadas incluidas en los KPI.',
      meta: dataComercial ? `${dataComercial.kpis.cantidad_ventas} operaciones` : 'Sin datos',
    },
    {
      titulo: 'Ticket Promedio',
      valor: soles(dataComercial?.kpis.ticket_promedio),
      ayuda: 'Promedio de ingreso por transacción.',
      meta: 'Media aritmética',
    },
    {
      titulo: 'Mediana de Ventas',
      valor: analyticsResumen?.mediana_ventas ? soles(analyticsResumen.mediana_ventas) : 'N/D',
      ayuda: 'Valor central, menos sensible a compras atípicas.',
      meta: 'Estadística descriptiva',
    },
    {
      titulo: 'Periodo Anterior',
      valor: dataComercial?.kpis_periodo_anterior ? soles(dataComercial.kpis_periodo_anterior.total_ventas) : 'N/D',
      ayuda: 'Sirve como referencia para la comparativa del periodo actual.',
      meta: dataComercial?.periodo_anterior
        ? `${dataComercial.periodo_anterior.fecha_inicio} a ${dataComercial.periodo_anterior.fecha_fin}`
        : 'Sin base previa',
    },
    {
      titulo: 'Variación Comercial',
      valor: porcentajeTexto(dataComercial?.variacion_porcentual_ventas),
      ayuda: 'Cambio porcentual de ventas frente al periodo anterior.',
      meta: 'Comparativa temporal',
    },
  ];

  const tarjetasAnaliticas = [
    {
      titulo: 'Promedio por tramo',
      valor: soles(kpisEstadisticos.promedioDiario),
      ayuda: agrupacion === 'dia' ? 'Promedio simple por día visualizado.' : 'Promedio simple por mes visualizado.',
    },
    {
      titulo: 'Desviación muestral',
      valor: analyticsSemana08?.resultados?.desviacion_muestral !== null && analyticsSemana08?.resultados?.desviacion_muestral !== undefined
        ? decimal(analyticsSemana08.resultados.desviacion_muestral)
        : analyticsSemana08?.desviacion_muestral !== null && analyticsSemana08?.desviacion_muestral !== undefined
          ? decimal(analyticsSemana08.desviacion_muestral)
          : 'N/D',
      ayuda: 'Mide la dispersión de importes respecto al promedio.',
    },
    {
      titulo: 'P(Venta pagada)',
      valor: analyticsProbabilidades?.probabilidad_pagado ?? 'N/D',
      ayuda: 'Probabilidad empírica de que una venta observada esté pagada.',
    },
    {
      titulo: 'P(Pagado | importe alto)',
      valor: analyticsProbabilidades?.probabilidad_pagado_dado_alto ?? 'N/D',
      ayuda: 'Indica qué tan probable es cobrar ventas con importe alto.',
    },
  ];

  const renderGraficoSerie = () => {
    if (!dataSerie || !dataSerie.puntos || dataSerie.puntos.length === 0) {
      return (
        <div className="empty-state">
          No hay ventas confirmadas en este intervalo de fechas ({fechaInicio} al {fechaFin}).
        </div>
      );
    }

    const puntos = dataSerie.puntos;
    const maxTotal = Math.max(...puntos.map((p) => numero(p.total_ventas)), 10);
    const width = Math.max(800, puntos.length * (agrupacion === 'dia' ? 18 : 44));
    const height = 260;
    const padding = 45;

    const xStep = puntos.length > 1 ? (width - padding * 2) / (puntos.length - 1) : 0;
    const coords = puntos.map((p, idx) => {
      const x = puntos.length === 1 ? width / 2 : padding + idx * xStep;
      const val = numero(p.total_ventas);
      const y = height - padding - (val / maxTotal) * (height - padding * 2);
      return { x, y, p, val };
    });

    const pathData = coords.reduce((acc, c, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${c.x} ${c.y}`, '');

    return (
      <div className="chart-box dashboard-chart-box">
        <div className="chart-header">
          <span>Serie Temporal de Ventas ({agrupacion === 'dia' ? 'Por Día' : 'Por Mes'})</span>
          <span>Moneda: {dataSerie.moneda} | Criterio: {dataSerie.criterio_estado}</span>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto', maxHeight: '300px', minWidth: '760px' }}>
            <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#222" strokeWidth="2" />
            <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="#222" strokeWidth="2" />

            {[0, 0.25, 0.5, 0.75, 1].map((pct, idx) => {
              const y = height - padding - pct * (height - padding * 2);
              const labelVal = (maxTotal * pct).toFixed(2);
              return (
                <g key={idx}>
                  <line x1={padding} y1={y} x2={width - padding} y2={y} stroke="#eee" strokeDasharray="4 4" />
                  <text x={padding - 8} y={y + 4} fontSize="10" textAnchor="end" fill="#555">
                    {labelVal}
                  </text>
                </g>
              );
            })}

            {coords.length > 1 && <path d={pathData} fill="none" stroke="#111" strokeWidth="2.5" />}

            {coords.map((c, i) => (
              <g key={i}>
                <circle cx={c.x} cy={c.y} r="4" fill="#fff" stroke="#111" strokeWidth="2" />
                <text
                  x={c.x}
                  y={height - padding + 18}
                  fontSize="9"
                  textAnchor="middle"
                  fill="#333"
                  transform={puntos.length > 8 ? `rotate(45 ${c.x} ${height - padding + 18})` : undefined}
                >
                  {c.p.fecha.slice(5)}
                </text>
                <title>{`Fecha: ${c.p.fecha}\nTotal: PEN ${c.p.total_ventas}\nCantidad: ${c.p.cantidad_ventas} ventas`}</title>
              </g>
            ))}
          </svg>
        </div>
        <div className="chart-footnote">
          * Pasa el cursor sobre los puntos para ver el detalle exacto. Cuando el periodo sea largo, conviene cambiar la agrupación a “Por Mes” para mejorar la lectura.
        </div>
      </div>
    );
  };

  const renderRanking = (titulo: string, items?: RankingItem[]) => {
    if (!items || items.length === 0) {
      return (
        <div className="ranking-panel">
          <h4 className="ranking-title">{titulo}</h4>
          <p className="ranking-empty">Sin datos en el período.</p>
        </div>
      );
    }

    const maxVal = Math.max(...items.map((it) => numero(it.total) || 1), 1);

    return (
      <div className="ranking-panel">
        <h4 className="ranking-title">{titulo}</h4>
        <div className="ranking-list">
          {items.map((item, idx) => {
            const val = numero(item.total);
            const pct = Math.min(100, (val / maxVal) * 100);
            return (
              <div key={idx} className="ranking-item">
                <div className="ranking-row">
                  <span>
                    <strong>#{idx + 1}</strong> {item.nombre}
                  </span>
                  <span>
                    {soles(item.total)} <span className="ranking-meta">({item.cantidad} ops)</span>
                  </span>
                </div>
                <div className="ranking-track">
                  <div style={{ width: `${pct}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderDistribucionPagos = () => {
    const items = analyticsProbabilidades?.variable_aleatoria_estado_pago ?? [];
    if (!items.length) {
      return <div className="empty-state">La distribución de estados de pago aparecerá aquí cuando el backend entregue observaciones suficientes.</div>;
    }

    const max = Math.max(...items.map((item) => item.frecuencia_absoluta), 1);

    return (
      <div className="mini-bars">
        {items.map((item) => (
          <div className="mini-bar-item" key={item.estado}>
            <div className="mini-bar-head">
              <span>{capitalizar(item.estado)}</span>
              <strong>{item.probabilidad ?? 'N/D'}</strong>
            </div>
            <div className="mini-bar-track">
              <div style={{ width: `${(item.frecuencia_absoluta / max) * 100}%` }} />
            </div>
            <small>{item.frecuencia_absoluta} registros observados</small>
          </div>
        ))}
      </div>
    );
  };

  const renderDistribucionResumen = () => {
    const items = analyticsDistribuciones?.distribucion ?? analyticsDistribuciones?.intervalos ?? [];
    if (!items.length) {
      return <div className="empty-state">No hay distribución disponible para este periodo.</div>;
    }

    return (
      <div className="distribution-table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Etiqueta</th>
              <th>Frecuencia</th>
              <th>Relativo</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, idx) => (
              <tr key={idx}>
                <td>{item.categoria || item.etiqueta || `${item.desde ?? item.limite_inferior ?? ''} ${item.hasta ? `- ${item.hasta}` : ''}`}</td>
                <td>{item.frecuencia_absoluta ?? item.frecuencia ?? 'N/D'}</td>
                <td>{item.frecuencia_relativa ?? item.porcentaje ?? 'N/D'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div>
      <div className="section-box">
        <h2 className="section-title">2. Dashboard Ejecutivo y Comercial</h2>

        <div className="dashboard-hero">
          <div>
            <p className="dashboard-eyebrow">Boceto funcional de la vista ejecutiva</p>
            <h3 className="dashboard-hero-title">Panel empresarial listo para diseño visual</h3>
            <p className="dashboard-hero-copy">
              Esta versión prioriza la disposición del contenido: resumen ejecutivo, contexto comercial,
              comparativas, análisis estadístico y zonas preparadas para inventario e insights.
            </p>
          </div>
          <div className="dashboard-hero-side">
            <div className="hero-chip"><strong>Periodo:</strong> {fechaInicio} a {fechaFin}</div>
            <div className="hero-chip"><strong>Agrupación:</strong> {agrupacion === 'dia' ? 'Por Día' : 'Por Mes'}</div>
            <div className="hero-chip"><strong>Fuente:</strong> FastAPI + PostgreSQL</div>
          </div>
        </div>

        <div className="filter-bar filter-bar-dashboard">
          <div className="form-group">
            <label htmlFor="dashboard-inicio">Fecha Inicio</label>
            <input id="dashboard-inicio" type="date" value={fechaInicio} onChange={(e) => setFechaInicio(e.target.value)} />
          </div>

          <div className="form-group">
            <label htmlFor="dashboard-fin">Fecha Fin</label>
            <input id="dashboard-fin" type="date" value={fechaFin} onChange={(e) => setFechaFin(e.target.value)} />
          </div>

          <div className="form-group">
            <label>Agrupación Gráfica</label>
            <select value={agrupacion} onChange={(e) => setAgrupacion(e.target.value as 'dia' | 'mes')}>
              <option value="dia">Por Día</option>
              <option value="mes">Por Mes</option>
            </select>
          </div>

          <div className="form-group">
            <label>Límite Rankings</label>
            <select value={limite} onChange={(e) => setLimite(Number(e.target.value))}>
              <option value={5}>Top 5</option>
              <option value={10}>Top 10</option>
              <option value={20}>Top 20</option>
            </select>
          </div>

          <div className="dashboard-filter-actions">
            <button onClick={cargarDashboard} disabled={loading || rangoInvalido} className="btn-primary">
              {loading ? 'Actualizando...' : 'Consultar'}
            </button>
            <button type="button" onClick={exportarCSV} disabled={!dataSerie?.puntos?.length || loading}>
              Exportar serie CSV
            </button>
          </div>
        </div>

        {rangoInvalido && <div className="alert alert-error" role="alert">El rango de fechas no es válido.</div>}
        {error && <div className="alert alert-error" role="alert">{error}</div>}
        {loading && <div className="alert alert-info" role="status">Consultando indicadores comerciales y estadísticos...</div>}
        {!loading && erroresComplementarios.length > 0 && (
          <div className="alert alert-info">
            <strong>Observación:</strong> algunos bloques complementarios no pudieron cargarse todavía. El tablero principal sigue disponible.
          </div>
        )}

        <div className="dashboard-actions">
          <span>Datos del backend · {dataComercial?.zona_horaria || 'Zona horaria del servidor'}</span>
          <span>Moneda base · {dataComercial?.moneda || 'PEN'}</span>
          <span>Criterio comercial · {dataComercial?.criterio_estado || 'Confirmadas'}</span>
        </div>

        <div className="dashboard-layout">
          <section className="dashboard-main-column">
            <div className="dashboard-block">
              <div className="block-heading">
                <div>
                  <p className="block-kicker">Resumen principal</p>
                  <h3>Indicadores ejecutivos</h3>
                </div>
                <p>Lectura rápida para gerencia, administración y Project Owner.</p>
              </div>
              <div className="grid-cards dashboard-kpi-grid">
                {tarjetasPrincipales.map((item) => (
                  <div className="card card-kpi" key={item.titulo}>
                    <div className="card-label">{item.titulo}</div>
                    <div className="card-value">{item.valor}</div>
                    <div className="card-sub">{item.ayuda}</div>
                    <div className="card-note">{item.meta}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="dashboard-block">
              <div className="block-heading">
                <div>
                  <p className="block-kicker">Lectura guiada</p>
                  <h3>Resumen ejecutivo interpretado</h3>
                </div>
                <p>Texto pensado para usuarios no técnicos.</p>
              </div>
              <div className="insights-list">
                {insightsEjecutivos.map((texto, idx) => (
                  <div className="insight-item" key={idx}>
                    <span className="insight-index">{idx + 1}</span>
                    <p>{texto}</p>
                  </div>
                ))}
              </div>
            </div>

            {dataComercial?.pedidos_por_estado && Object.keys(dataComercial.pedidos_por_estado).length > 0 && (
              <div className="dashboard-block">
                <div className="block-heading">
                  <div>
                    <p className="block-kicker">Operación comercial</p>
                    <h3>Pedidos por estado</h3>
                  </div>
                  <p>Total visible: {totalPedidos ?? 'N/D'} pedidos.</p>
                </div>
                <div className="chart-box">
                  <div className="order-status-grid">
                    {Object.entries(dataComercial.pedidos_por_estado).map(([estado, cantidad]) => (
                      <div className="order-status-item" key={estado}>
                        <span>{capitalizar(estado)}</span>
                        <strong>{cantidad}</strong>
                        <div className="order-status-track">
                          <div style={{ width: `${totalPedidos ? Math.max(0, Math.min(100, (cantidad / totalPedidos) * 100)) : 0}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            <div className="dashboard-block">
              <div className="block-heading">
                <div>
                  <p className="block-kicker">Comportamiento temporal</p>
                  <h3>Evolución de ventas</h3>
                </div>
                <p>Vista principal para tendencia, estacionalidad y exportación.</p>
              </div>
              {renderGraficoSerie()}
            </div>

            {dataComercial && (
              <div className="dashboard-block">
                <div className="block-heading">
                  <div>
                    <p className="block-kicker">Contribución comercial</p>
                    <h3>Rankings operativos</h3>
                  </div>
                  <p>Productos, clientes y vendedores más relevantes en el periodo.</p>
                </div>
                <div className="ranking-grid">
                  {renderRanking('Top Productos', dataComercial.productos_destacados)}
                  {renderRanking('Top Clientes', dataComercial.clientes_destacados)}
                  {renderRanking('Top Vendedores', dataComercial.vendedores_destacados)}
                </div>
              </div>
            )}
          </section>

          <aside className="dashboard-side-column">
            <div className="dashboard-block side-block">
              <div className="block-heading compact">
                <div>
                  <p className="block-kicker">Analítica aplicada</p>
                  <h3>Estadística rápida</h3>
                </div>
              </div>
              <div className="side-kpi-stack">
                {tarjetasAnaliticas.map((item) => (
                  <div className="side-kpi-card" key={item.titulo}>
                    <span>{item.titulo}</span>
                    <strong>{item.valor}</strong>
                    <small>{item.ayuda}</small>
                  </div>
                ))}
              </div>
            </div>

            <div className="dashboard-block side-block">
              <div className="block-heading compact">
                <div>
                  <p className="block-kicker">Estados de pago</p>
                  <h3>Distribución probabilística</h3>
                </div>
              </div>
              {renderDistribucionPagos()}
            </div>

            <div className="dashboard-block side-block">
              <div className="block-heading compact">
                <div>
                  <p className="block-kicker">Distribución resumida</p>
                  <h3>Tabla de frecuencias</h3>
                </div>
              </div>
              {renderDistribucionResumen()}
            </div>

            <div className="dashboard-block side-block">
              <div className="block-heading compact">
                <div>
                  <p className="block-kicker">Capas previstas</p>
                  <h3>Espacios listos para diseño</h3>
                </div>
              </div>
              <div className="roadmap-list">
                <div className="roadmap-item">
                  <strong>Inventario y alertas</strong>
                  <p>Bloque reservado para stock disponible, riesgo de ruptura y productos críticos.</p>
                </div>
                <div className="roadmap-item">
                  <strong>Insights automáticos</strong>
                  <p>Zona preparada para recomendaciones e interpretaciones generadas a partir de reglas o IA.</p>
                </div>
                <div className="roadmap-item">
                  <strong>Comparativas extendidas</strong>
                  <p>Espacio previsto para comparativas semanales, mensuales y por segmentos comerciales.</p>
                </div>
              </div>
            </div>

            <div className="dashboard-block side-block">
              <div className="block-heading compact">
                <div>
                  <p className="block-kicker">Notas de implementación</p>
                  <h3>Guía para UI/UX</h3>
                </div>
              </div>
              <ul className="design-notes">
                <li>Ya quedó definida la jerarquía de información.</li>
                <li>Tu compañero puede trabajar colores, iconos y sombras sin tocar la lógica.</li>
                <li>Las tarjetas y bloques son responsivos y se adaptan a pantallas medianas.</li>
                <li>Los módulos sin endpoint real muestran mensaje informativo, no datos inventados.</li>
              </ul>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
};
