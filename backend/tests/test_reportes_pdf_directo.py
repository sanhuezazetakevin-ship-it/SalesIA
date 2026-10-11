"""Pruebas aisladas del nuevo formato visual sin datos empresariales reales."""
from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock
from io import BytesIO
import pytest
from app.services import reportes_pdf_directo as pdf


def test_pdf_visual_valido():
    contenido = pdf._construir_pdf('VENTAS', date(2026,1,1), date(2026,1,31), 3,
                                  Decimal('1234.50'), [('01/2026', Decimal('1234.50'))])
    assert contenido.startswith(b'%PDF-')
    assert len(contenido) > 1200


def test_pdf_sin_ventas():
    contenido = pdf._construir_pdf('CLIENTES', date(2026,1,1), date(2026,1,31), 0, Decimal(0), [])
    assert contenido.startswith(b'%PDF-')


def test_endpoint_documentado():
    pytest.importorskip("psycopg")
    from app.main import app
    assert '/api/reportes/pdf-directo' in app.openapi()['paths']


def test_servicio_filtra_empresa_y_no_persiste_archivo():
    db = MagicMock()
    db.execute.return_value.one.return_value = (2, Decimal('250'))
    with patch.object(pdf, '_tenant', return_value=19) as tenant, patch.object(pdf, '_serie', return_value=[('01/2026', Decimal('250'))]):
        contenido = pdf.generar_pdf_directo(db, 7, 'VENTAS', date(2026,1,1),date(2026,1,31))
    assert contenido.startswith(b'%PDF-')
    tenant.assert_called_once_with(db, 7, 'reportes.generar')
    assert db.add.call_count == 0
    assert db.commit.call_count == 0


def test_intervalo_no_valido():
    with patch.object(pdf, '_tenant', return_value=19):
        with pytest.raises(pdf.ReporteError):
            pdf.generar_pdf_directo(MagicMock(), 7, 'VENTAS', date(2026,2,1), date(2026,1,1))
