import React, { useState } from 'react';
import { api } from '../services/api';
import { ReporteTipo } from '../types/api';

export const ReportsView: React.FC = () => {
  const hoy = new Date().toISOString().split('T')[0];
  const haceUnMes = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

  const [tipo, setTipo] = useState<ReporteTipo>('VENTAS');
  const [fechaInicio, setFechaInicio] = useState(haceUnMes);
  const [fechaFin, setFechaFin] = useState(hoy);

  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleDescargarPdf = async () => {
    setLoading(true);
    setSuccessMsg(null);
    setErrorMsg(null);

    try {
      await api.descargarReportePdf(tipo, fechaInicio, fechaFin);
      setSuccessMsg(`Reporte en PDF (${tipo}) generado y descargado exitosamente en su navegador.`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error al generar PDF';
      setErrorMsg(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="section-box">
        <h2 className="section-title">5. Emisión de Reportes Oficiales en PDF Directo</h2>

        <p style={{ fontSize: '0.85rem', marginBottom: '1.25rem', color: '#444' }}>
          Este módulo consume el endpoint binario <code>/api/reportes/pdf-directo</code> que renderiza
          documentos ejecutivos al vuelo mediante ReportLab en memoria, respetando la cabecera Bearer
          y el aislamiento multiempresa de PostgreSQL.
        </p>

        {successMsg && <div className="alert alert-success">{successMsg}</div>}
        {errorMsg && <div className="alert alert-error">{errorMsg}</div>}

        <div className="filter-bar" style={{ maxWidth: '650px' }}>
          <div className="form-group">
            <label>Tipo de Reporte:</label>
            <select
              value={tipo}
              onChange={(e) => setTipo(e.target.value as ReporteTipo)}
            >
              <option value="VENTAS">VENTAS (Transacciones confirmadas)</option>
              <option value="ESTADISTICO">ESTADÍSTICO (Media, mínima, máxima, totales)</option>
              <option value="INVENTARIO">INVENTARIO (Unidades y montos por producto)</option>
              <option value="CLIENTES">CLIENTES (Ventas por cliente y volumen)</option>
              <option value="RENDIMIENTO">RENDIMIENTO (Rendimiento por vendedor)</option>
            </select>
          </div>

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

          <button
            onClick={handleDescargarPdf}
            disabled={loading}
            className="btn-primary"
            style={{ minWidth: '180px' }}
          >
            {loading ? 'Generando PDF en memoria...' : 'Generar y Descargar PDF'}
          </button>
        </div>

        <div className="section-box" style={{ marginTop: '1.5rem', backgroundColor: '#fafafa' }}>
          <h4 style={{ fontSize: '0.85rem', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
            Flujo de Integración Implementado (según Sección 6 de la Guía):
          </h4>
          <ol style={{ fontSize: '0.8rem', paddingLeft: '1.25rem', color: '#555', lineHeight: '1.6' }}>
            <li>Selección de tipo de reporte y rango de fechas (UTC).</li>
            <li>Petición HTTP autenticada con <code>Authorization: Bearer &lt;token&gt;</code>.</li>
            <li>Validación de cabecera <code>Content-Type: application/pdf</code>.</li>
            <li>Conversión binaria nativa a <code>Blob</code> en el cliente.</li>
            <li>Inyección de <code>ObjectURL</code> temporal con atributo de descarga.</li>
            <li>Revocación inmediata del objeto URL para liberar memoria del navegador.</li>
          </ol>
        </div>
      </div>
    </div>
  );
};
