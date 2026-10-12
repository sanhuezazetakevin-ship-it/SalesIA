import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import {
  AnalyticsResumenResponse,
  AnalyticsDistribucionesResponse,
  AnalyticsProbabilidadesResponse,
  Semana08Response,
} from '../types/api';

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

  // Histograma SVG simple
  const renderHistograma = () => {
    const lista = distribucion?.distribucion || distribucion?.intervalos || [];
    if (!distribucion || lista.length === 0) {
      return <div className="empty-state">No se registraron datos para generar la distribución.</div>;
    }

    const maxFreq = Math.max(...lista.map((i) => i.frecuencia_absoluta ?? i.frecuencia ?? 0), 1);
    const width = 650;
    const height = 220;
    const padding = 40;
    const barWidth = (width - padding * 2) / lista.length;

    return (
      <div className="chart-box">
        <div className="chart-header">
          <span>Histograma de Distribución ({distribucion.variable})</span>
          <span>Observaciones totales: {distribucion.total_observaciones}</span>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto', maxHeight: '250px' }}>
            <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#222" strokeWidth="2" />
            {lista.map((item, idx) => {
              const freq = item.frecuencia_absoluta ?? item.frecuencia ?? 0;
              const barH = (freq / maxFreq) * (height - padding * 2);
              const x = padding + idx * barWidth + 6;
              const y = height - padding - barH;
              const w = Math.max(10, barWidth - 12);
              const label = item.categoria || item.etiqueta || (item.desde && item.hasta ? `${item.desde}–${item.hasta}` : '');
              const pct = item.frecuencia_relativa ? `${(parseFloat(item.frecuencia_relativa) * 100).toFixed(1)}%` : (item.porcentaje || '');

              return (
                <g key={idx}>
                  <rect x={x} y={y} width={w} height={barH} fill="#111" stroke="#000" />
                  <text x={x + w / 2} y={y - 5} fontSize="10" textAnchor="middle" fill="#111" fontWeight="bold">
                    {freq}
                  </text>
                  <text x={x + w / 2} y={height - padding + 15} fontSize="9" textAnchor="middle" fill="#555">
                    {label}
                  </text>
                  <title>{`${label}: ${freq} observaciones (${pct})`}</title>
                </g>
              );
            })}
          </svg>
        </div>
      </div>
    );
  };

  return (
    <div>
      <div className="section-box">
        <h2 className="section-title">4. Analytics & Motor Estadístico (Semanas 07 & 08)</h2>

        {/* Filtros de intervalo */}
        <div className="filter-bar">
          <div className="form-group">
            <label>Fecha Inicio:</label>
            <input type="date" value={fechaInicio} onChange={(e) => setFechaInicio(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Fecha Fin:</label>
            <input type="date" value={fechaFin} onChange={(e) => setFechaFin(e.target.value)} />
          </div>
          <button onClick={consultarAnalytics} disabled={loading} className="btn-primary">
            {loading ? 'Calculando...' : 'Actualizar'}
          </button>
        </div>

        {/* Pestañas de análisis estadístico */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem', flexWrap: 'wrap' }}>
          <button
            className={activeSubTab === 'resumen' ? 'btn-primary' : ''}
            onClick={() => setActiveSubTab('resumen')}
          >
            A. Media & Mediana
          </button>
          <button
            className={activeSubTab === 'distribuciones' ? 'btn-primary' : ''}
            onClick={() => setActiveSubTab('distribuciones')}
          >
            B. Distribuciones & Frecuencias
          </button>
          <button
            className={activeSubTab === 'probabilidades' ? 'btn-primary' : ''}
            onClick={() => setActiveSubTab('probabilidades')}
          >
            C. Probabilidades & Teorema de Bayes
          </button>
          <button
            className={activeSubTab === 'semana08' ? 'btn-primary' : ''}
            onClick={() => setActiveSubTab('semana08')}
          >
            D. Semana 08: Dispersión & Hipótesis
          </button>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        {/* SubTab A: Resumen (Media / Mediana) */}
        {activeSubTab === 'resumen' && resumen && (
          <div>
            <div className="grid-cards">
              <div className="card">
                <div className="card-label">Total Ventas Confirmadas</div>
                <div className="card-value">PEN {resumen.total_ventas}</div>
                <div className="card-sub">{resumen.cantidad_ventas} transacciones analizadas</div>
              </div>

              <div className="card">
                <div className="card-label">Media Aritmética (Ticket Promedio)</div>
                <div className="card-value">
                  {resumen.ticket_promedio ? `PEN ${resumen.ticket_promedio}` : 'N/A'}
                </div>
                <div className="card-sub">x̄ = (∑ xᵢ) / n</div>
              </div>

              <div className="card">
                <div className="card-label">Mediana de Ventas</div>
                <div className="card-value">
                  {resumen.mediana_ventas ? `PEN ${resumen.mediana_ventas}` : 'N/A'}
                </div>
                <div className="card-sub">Valor central ordenado (50% de corte)</div>
              </div>
            </div>

            <div className="alert alert-info">
              <strong>Interpretación descriptiva:</strong> La media describe el importe monetario medio por transacción;
              la mediana indica el valor central libre del impacto de compras atípicas o de montos extremos.
            </div>
          </div>
        )}

        {/* SubTab B: Distribuciones */}
        {activeSubTab === 'distribuciones' && (
          <div>
            <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', alignItems: 'center' }}>
              <div className="form-group">
                <label>Variable a evaluar:</label>
                <select
                  value={variableDist}
                  onChange={(e) => setVariableDist(e.target.value as 'importe_venta' | 'estado_pago')}
                >
                  <option value="importe_venta">Importe de Venta</option>
                  <option value="estado_pago">Estado de Pago</option>
                </select>
              </div>

              <div className="form-group">
                <label>Intervalos (Bins 1-20):</label>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={intervalos}
                  onChange={(e) => setIntervalos(Number(e.target.value))}
                  style={{ width: '80px' }}
                />
              </div>

              <button onClick={consultarAnalytics} disabled={loading} style={{ alignSelf: 'flex-end' }}>
                Recalcular Histograma
              </button>
            </div>

            {renderHistograma()}
          </div>
        )}

        {/* SubTab C: Probabilidades y Teorema de Bayes */}
        {activeSubTab === 'probabilidades' && (
          <div>
            <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', alignItems: 'center' }}>
              <div className="form-group">
                <label>Umbral Importe Alto (PEN):</label>
                <input
                  type="text"
                  value={umbralImporte}
                  onChange={(e) => setUmbralImporte(e.target.value)}
                  style={{ width: '120px' }}
                />
              </div>
              <button onClick={consultarAnalytics} disabled={loading} style={{ alignSelf: 'flex-end' }}>
                Calcular Bayes
              </button>
            </div>

            {probabilidades && (
              <div>
                <div className="grid-cards">
                  <div className="card">
                    <div className="card-label">P(Pagado)</div>
                    <div className="card-value">{probabilidades.probabilidad_pagado ?? 'N/A'}</div>
                    <div className="card-sub">
                      {probabilidades.conteos.pagado} de {probabilidades.total_observaciones} ventas
                    </div>
                  </div>

                  <div className="card">
                    <div className="card-label">P(Importe Alto ≥ {probabilidades.umbral_importe_alto})</div>
                    <div className="card-value">{probabilidades.probabilidad_importe_alto ?? 'N/A'}</div>
                    <div className="card-sub">{probabilidades.conteos.importe_alto} ventas superan el umbral</div>
                  </div>

                  <div className="card">
                    <div className="card-label">P(Pagado | Alto)</div>
                    <div className="card-value">{probabilidades.probabilidad_pagado_dado_alto ?? 'N/A'}</div>
                    <div className="card-sub">Probabilidad de pago dado que el ticket es alto</div>
                  </div>

                  <div className="card" style={{ border: '2px solid #111' }}>
                    <div className="card-label">★ Teorema de Bayes: P(Alto | Pagado)</div>
                    <div className="card-value">{probabilidades.bayes_importe_alto_dado_pagado ?? 'N/A'}</div>
                    <div className="card-sub">P(Alto|Pagado) = P(Pagado|Alto)·P(Alto) / P(Pagado)</div>
                  </div>
                </div>

                <div className="alert alert-info">
                  <strong>Fundamento matemático:</strong> Permite evaluar si una venta ya completada y cancelada
                  tiene alta o baja probabilidad de pertenecer a los tickets de alta magnitud, utilizando conteos exactos.
                </div>
              </div>
            )}
          </div>
        )}

        {/* SubTab D: Semana 08 (Dispersión y Contraste de Hipótesis) */}
        {activeSubTab === 'semana08' && (
          <div>
            <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
              <div className="form-group">
                <label>Media Hipotética de Referencia (H0):</label>
                <input
                  type="number"
                  value={mediaHipotetica}
                  onChange={(e) => setMediaHipotetica(Number(e.target.value))}
                  style={{ width: '120px' }}
                />
              </div>

              <div className="form-group">
                <label>Nivel de Significancia (alfa):</label>
                <input
                  type="number"
                  step="0.01"
                  value={alfa}
                  onChange={(e) => setAlfa(Number(e.target.value))}
                  style={{ width: '90px' }}
                />
              </div>

              <button onClick={consultarAnalytics} disabled={loading} style={{ alignSelf: 'flex-end' }}>
                Ejecutar Prueba t de Student
              </button>
            </div>

            {semana08 && (() => {
              const res = semana08.resultados || semana08;
              return (
                <div>
                  <div className="grid-cards">
                    <div className="card">
                      <div className="card-label">Esperanza Empírica (Media)</div>
                      <div className="card-value">PEN {res.esperanza_empirica ?? res.media ?? 'N/A'}</div>
                      <div className="card-sub">Muestra de {res.cantidad} ventas</div>
                    </div>

                    <div className="card">
                      <div className="card-label">Desviación Estándar Muestral (s)</div>
                      <div className="card-value">{res.desviacion_muestral ?? 'N/A'}</div>
                      <div className="card-sub">Varianza muestral: {res.varianza_muestral ?? 'N/A'}</div>
                    </div>

                    <div className="card">
                      <div className="card-label">Desviación Poblacional (σ)</div>
                      <div className="card-value">{res.desviacion_poblacional ?? 'N/A'}</div>
                      <div className="card-sub">Varianza poblacional: {res.varianza_poblacional ?? 'N/A'}</div>
                    </div>
                  </div>

                  {res.contraste && (
                    <div className="section-box" style={{ marginTop: '1rem' }}>
                      <h3 className="section-title">Resultado de la Prueba t de Student (SciPy)</h3>
                      <p style={{ fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                        <strong>Método:</strong> {res.contraste.metodo}
                        <br />
                        <strong>Hipótesis Nula:</strong> {res.contraste.hipotesis_nula}
                      </p>

                      <div style={{ display: 'flex', gap: '1.5rem', margin: '0.75rem 0', flexWrap: 'wrap' }}>
                        <div>
                          <strong>Estadístico t:</strong> {res.contraste.estadistico_t ?? 'N/A'}
                        </div>
                        <div>
                          <strong>Grados de libertad:</strong> {res.contraste.grados_libertad ?? 'N/A'}
                        </div>
                        <div>
                          <strong>p-valor:</strong> {res.contraste.valor_p ?? 'N/A'}
                        </div>
                        <div>
                          <strong>Decisión:</strong>{' '}
                          <span className={`badge ${res.contraste.rechazar_hipotesis_nula ? 'badge-connected' : 'badge-disconnected'}`}>
                            {res.contraste.rechazar_hipotesis_nula ? 'RECHAZA H0' : 'NO RECHAZA H0'}
                          </span>
                        </div>
                      </div>

                      <div className="alert alert-info" style={{ marginTop: '0.75rem' }}>
                        {res.contraste.explicacion}
                        <br />
                        <small style={{ color: '#555' }}>{res.contraste.advertencia}</small>
                      </div>
                    </div>
                  )}
                </div>
              );
            })()}
          </div>
        )}
      </div>
    </div>
  );
};
