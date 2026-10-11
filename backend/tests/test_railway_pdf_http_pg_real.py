"""PDF visual HTTP con JWT + RBAC + PostgreSQL TESTING real.

Requiere TEST_DATABASE_URL aislado de DATABASE_URL; db_testing hace rollback.
Nunca envía SQL, credenciales ni bytes del PDF al log.
"""
from datetime import date
from decimal import Decimal
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select, func

from app.api.routes.reportes import router as reportes_router
from app.database.connection import get_db
from app.models.reporte_generado import ReporteGenerado
from app.services import reportes_pdf_directo as pdf
from tests.test_pedido_service import _escenario_confirmacion
from tests.test_analytics_resumen_integracion import datos_venta, autenticar

URL = '/api/reportes/pdf-directo'
PARAMS = {'tipo': 'VENTAS', 'fecha_inicio': '2026-10-01', 'fecha_fin': '2026-10-31'}


def _escenario(db, permisos=('reportes.generar',)):
    return _escenario_confirmacion(db, permisos=permisos)


def _contar_registros(db, empresa_id):
    return db.scalar(select(func.count(ReporteGenerado.id)).where(ReporteGenerado.empresa_id == empresa_id))


def test_pdf_http_datos_confirmados_empresas_y_no_persistencia(db_testing):
    empresa_a = _escenario(db_testing)
    empresa_b = _escenario(db_testing)
    datos_venta(db_testing, empresa_a, total='15.00')
    datos_venta(db_testing, empresa_a, total='25.00')
    datos_venta(db_testing, empresa_a, total='900.00', estado='CANCELADA')
    datos_venta(db_testing, empresa_b, total='300.00')
    cab_a = autenticar(db_testing, empresa_a)
    cab_b = autenticar(db_testing, empresa_b)
    registros_a = _contar_registros(db_testing, empresa_a['empresa_id'])
    registros_b = _contar_registros(db_testing, empresa_b['empresa_id'])
    app = FastAPI()
    app.include_router(reportes_router)
    # Sólo sustituye DB: JWT, sesión y permiso se validan de verdad.
    app.dependency_overrides[get_db] = lambda: db_testing
    originales = pdf._construir_pdf
    capturas = []

    def capturar(*args, **kwargs):
        capturas.append(args)
        return originales(*args, **kwargs)

    try:
        with TestClient(app) as client, patch.object(pdf, '_construir_pdf', side_effect=capturar):
            respuesta_a = client.get(URL, params=PARAMS, headers=cab_a)
            respuesta_b = client.get(URL, params=PARAMS, headers=cab_b)
            sin_jwt = client.get(URL, params=PARAMS)
            invalida = client.get(URL, params={**PARAMS, 'fecha_fin': '2026-09-01'}, headers=cab_a)
    finally:
        app.dependency_overrides.clear()

    for respuesta in (respuesta_a, respuesta_b):
        assert respuesta.status_code == 200, respuesta.text[:300]
        assert respuesta.headers['content-type'].startswith('application/pdf')
        assert 'attachment' in respuesta.headers['content-disposition']
        assert respuesta.headers['cache-control'] == 'private, no-store'
        assert respuesta.content.startswith(b'%PDF-')
        assert len(respuesta.content) > 1200
    assert sin_jwt.status_code == 401
    assert invalida.status_code == 422
    assert len(capturas) == 2
    # tipo, inicio, fin, cantidad, total, puntos
    assert capturas[0][3] == 2 and Decimal(str(capturas[0][4])) == Decimal('40.00')
    assert capturas[1][3] == 1 and Decimal(str(capturas[1][4])) == Decimal('300.00')
    assert sum(Decimal(str(v)) for _, v in capturas[0][5]) == Decimal('40.00')
    assert sum(Decimal(str(v)) for _, v in capturas[1][5]) == Decimal('300.00')
    assert _contar_registros(db_testing, empresa_a['empresa_id']) == registros_a
    assert _contar_registros(db_testing, empresa_b['empresa_id']) == registros_b
    # Parseo real del PDF si pypdf está instalado como dependencia de pruebas opcional.
    try:
        from pypdf import PdfReader
        from io import BytesIO
    except ImportError:
        pass
    else:
        texto_a = '\n'.join(p.extract_text() or '' for p in PdfReader(BytesIO(respuesta_a.content)).pages)
        texto_b = '\n'.join(p.extract_text() or '' for p in PdfReader(BytesIO(respuesta_b.content)).pages)
        assert '40.00' in texto_a and '300.00' not in texto_a
        assert '300.00' in texto_b and '40.00' not in texto_b


def test_pdf_http_sin_permiso(db_testing):
    usuario = _escenario(db_testing, permisos=('ventas.ver',))
    app = FastAPI()
    app.include_router(reportes_router)
    app.dependency_overrides[get_db] = lambda: db_testing
    try:
        with TestClient(app) as client:
            respuesta = client.get(URL, params=PARAMS, headers=autenticar(db_testing, usuario))
            assert respuesta.status_code == 403, respuesta.text[:300]
    finally:
        app.dependency_overrides.clear()
