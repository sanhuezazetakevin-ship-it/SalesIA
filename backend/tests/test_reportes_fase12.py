"""FASE 12: protecciones, formatos, rutas y casos límite sin DB real."""
from datetime import date
from io import BytesIO
import csv
import pytest
from app.services import reportes_service as s


def test_formatos_csv_seguro_excel():
    value = s._csv(['nombre', 'total'], [['=HYPERLINK("bad")', '10.00'], ['Normal', 20]])
    assert value.startswith(b'\xef\xbb\xbf')
    rows = list(csv.reader(value.decode('utf-8-sig').splitlines()))
    assert rows[1][0].startswith("'=")
    assert rows[2] == ['Normal', '20']


def test_html_escapado():
    html = s._html(['nombre'], [['<img src=x onerror=alert(1)>']], 'Prueba', date(2026,1,1), date(2026,1,2)).decode()
    assert '<img' not in html
    assert '&lt;img' in html


def test_pdf_valido():
    data = s._pdf(['Campo','Importe'], [['Ejemplo', '15.00']], 'Ventas', date(2026,1,1), date(2026,1,2))
    assert data[:5] == b'%PDF-'


def test_intervalo_invalido():
    with pytest.raises(s.ReporteError):
        s.validar('VENTAS', date(2026,3,1), date(2026,2,1))
    with pytest.raises(s.ReporteError):
        s.validar('CLIENTES', date(2020,1,1), date(2026,1,1))
    with pytest.raises(s.ReporteError):
        s.validar('DESCONOCIDO', date(2026,1,1), date(2026,1,1))


def test_catalogo_tipos():
    assert s.TIPOS == {'VENTAS','ESTADISTICO','INVENTARIO','CLIENTES','RENDIMIENTO'}
    assert s.FORMATOS == {'CSV','XLSX','PDF'}


def test_openapi_reportes():
    from app.main import app
    paths = app.openapi()['paths']
    for p in ['/api/reportes', '/api/reportes/generar', '/api/reportes/previsualizar',
              '/api/reportes/imprimible','/api/reportes/{reporte_id}', '/api/reportes/{reporte_id}/descargar']:
        assert p in paths


def test_sin_autenticacion():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as client:
        r = client.get('/api/reportes')
    assert r.status_code == 401


def test_validacion_parametros_con_autenticacion_simulada():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.dependencies import get_current_active_user
    from app.database.connection import get_db
    from types import SimpleNamespace
    original = dict(app.dependency_overrides)
    try:
        app.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace(id=7)
        app.dependency_overrides[get_db] = lambda: object()
        with TestClient(app) as client:
            r = client.get('/api/reportes/previsualizar', params={
                'tipo':'VENTAS','fecha_inicio':'2026-01-01','fecha_fin':'2026-01-31','limite':101})
        assert r.status_code == 422
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original)


def test_xlsx_valido():
    data = s._xlsx(["Campo", "Importe"], [["Ejemplo", "15.00"]])
    assert data[:4] == b"PK\x03\x04"
