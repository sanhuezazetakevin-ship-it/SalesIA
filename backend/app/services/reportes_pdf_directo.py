"""Reporte PDF visual bajo demanda sin almacenamiento en disco, aislado por empresa."""
from datetime import date
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from sqlalchemy import select, func
from app.models.venta import Venta
from app.models.venta_detalle import VentaDetalle
from app.models.producto import Producto
from app.models.cliente import Cliente
from app.services.dashboard_comercial_service import _filtro_ventas
from app.services.reportes_service import ReporteError, _tenant, validar

TIPOS_VISUALES = {'VENTAS', 'ESTADISTICO', 'INVENTARIO', 'CLIENTES', 'RENDIMIENTO'}


def _serie(db, empresa_id, tipo, inicio, fin):
    filtros = _filtro_ventas(empresa_id, inicio, fin)
    if tipo in ('VENTAS', 'ESTADISTICO'):
        # Agrupación mensual por SQL, como máximo 13 barras por rango permitido.
        grupo = func.date_trunc('month', Venta.created_at)
        stmt = (select(grupo.label('grupo'), func.sum(Venta.total).label('valor'))
                .where(*filtros).group_by(grupo).order_by(grupo))
        return [(d.strftime('%m/%Y'), Decimal(str(v or 0))) for d, v in db.execute(stmt)]
    if tipo == 'INVENTARIO':
        stmt = (select(Producto.nombre, func.sum(VentaDetalle.cantidad).label('valor'))
                .join(VentaDetalle, (VentaDetalle.producto_id == Producto.id) & (VentaDetalle.empresa_id == Producto.empresa_id))
                .join(Venta, (Venta.id == VentaDetalle.venta_id) & (Venta.empresa_id == VentaDetalle.empresa_id))
                .where(*filtros, Producto.empresa_id == empresa_id)
                .group_by(Producto.id, Producto.nombre).order_by(func.sum(VentaDetalle.cantidad).desc(), Producto.id).limit(8))
        return [(name or 'Producto', Decimal(str(v or 0))) for name,v in db.execute(stmt)]
    if tipo == 'CLIENTES':
        stmt = (select(Cliente.nombre, func.sum(Venta.total).label('valor'))
                .join(Venta, (Venta.cliente_id == Cliente.id) & (Venta.empresa_id == Cliente.empresa_id))
                .where(*filtros, Cliente.empresa_id == empresa_id)
                .group_by(Cliente.id, Cliente.nombre).order_by(func.sum(Venta.total).desc(), Cliente.id).limit(8))
        return [(name or 'Cliente', Decimal(str(v or 0))) for name,v in db.execute(stmt)]
    stmt = (select(Venta.usuario_id, func.sum(Venta.total).label('valor'))
            .where(*filtros).group_by(Venta.usuario_id)
            .order_by(func.sum(Venta.total).desc(), Venta.usuario_id).limit(8))
    return [(f'Vendedor {uid}', Decimal(str(v or 0))) for uid,v in db.execute(stmt)]


def _grafico_barras(puntos):
    """Gráfico vectorial ReportLab: sin matplotlib ni imágenes temporales."""
    from reportlab.graphics.shapes import Drawing, Rect, String, Line
    width, height = 505, 196
    d = Drawing(width, height)
    if not puntos:
        d.add(String(12, 94, 'Sin información para representar en este período.', fontSize=11))
        return d
    maximo = max(float(v) for _, v in puntos) or 1
    ancho = min(52, 420 / max(len(puntos), 1) - 10)
    paso = 465 / len(puntos)
    d.add(Line(35, 35, 495, 35, strokeColor='#CBD5E1'))
    for idx, (nombre, valor) in enumerate(puntos):
        x = 43 + idx * paso
        h = 120 * float(valor) / maximo
        d.add(Rect(x, 35, ancho, h, fillColor='#2563EB', strokeColor=None))
        etiqueta = str(nombre)[:15]
        d.add(String(x, 19, etiqueta, fontSize=7))
        d.add(String(x, 40 + h, f'{float(valor):,.0f}', fontSize=7))
    return d


def _grafico_participacion(puntos):
    """Segundo gráfico vectorial: participación relativa de las categorías de la consulta."""
    from reportlab.graphics.shapes import Drawing, Wedge, String, Rect
    from reportlab.lib import colors
    d = Drawing(505, 170)
    valores = [(str(n), max(0.0, float(v))) for n, v in puntos]
    total = sum(v for _, v in valores)
    if total <= 0:
        d.add(String(14, 85, 'Sin datos suficientes para calcular la participación.', fontSize=10))
        return d
    import math
    paleta = ['#1764DC', '#05B4D7', '#284F94', '#5B8EE6', '#79BAC7', '#94A7C8', '#B0CAEA', '#D2E4F5']
    a = 90.0
    for i, (nombre, valor) in enumerate(valores[:8]):
        if valor <= 0:
            continue
        angulo = valor / total * 360
        d.add(Wedge(94, 86, 65, a, a + angulo, fillColor=colors.HexColor(paleta[i]), strokeColor=colors.white, strokeWidth=.8))
        a += angulo
        y = 151 - i * 18
        d.add(Rect(206, y - 3, 9, 9, fillColor=colors.HexColor(paleta[i]), strokeColor=None))
        d.add(String(224, y, f'{nombre[:24]}  {valor / total * 100:.1f}%', fontSize=9, fillColor=colors.HexColor('#243A5B')))
    return d


def _construir_pdf(tipo, inicio, fin, cantidad, total, puntos):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    stream = BytesIO()
    doc = SimpleDocTemplate(stream, pagesize=A4, leftMargin=43, rightMargin=43,
                            topMargin=45, bottomMargin=45, pageCompression=1)
    styles = getSampleStyleSheet()
    total = Decimal(str(total))
    promedio = (total / cantidad) if cantidad else Decimal(0)
    titulo = {'VENTAS': 'Ventas', 'ESTADISTICO': 'Estadísticas', 'INVENTARIO': 'Productos vendidos',
              'CLIENTES': 'Clientes', 'RENDIMIENTO': 'Vendedores'}[tipo]
    styles['Title'].textColor = colors.HexColor('#173E84')
    styles['Heading2'].textColor = colors.HexColor('#173E84')
    resumen_tabla = Table([
        ['VENTAS CONFIRMADAS', 'IMPORTE TOTAL', 'TICKET PROMEDIO'],
        [f'{cantidad:,}', f'S/ {total:,.2f}', f'S/ {promedio:,.2f}' if cantidad else 'N/D'],
    ], colWidths=[169,169,169], rowHeights=[25,38])
    resumen_tabla.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#173E84')),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('BACKGROUND',(0,1),(-1,1),colors.HexColor('#EDF4FE')),
        ('TEXTCOLOR',(0,1),(-1,1),colors.HexColor('#173E84')),
        ('FONTSIZE',(0,0),(-1,0),9),('FONTSIZE',(0,1),(-1,1),14),
        ('FONTNAME',(0,0),(-1,-1),'Helvetica-Bold'),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('LEFTPADDING',(0,0),(-1,-1),12),
    ]))
    elementos = [Paragraph('SalesIA Enterprise | Reporte ejecutivo', styles['Title']),
        Paragraph(escape(titulo), styles['Heading2']),
        Paragraph(f'Período: {inicio.isoformat()} a {fin.isoformat()} | Moneda: PEN | Fechas UTC', styles['Normal']),
        Spacer(1, 16), Paragraph('Resumen del período', styles['Heading2']),
        resumen_tabla, Spacer(1, 18), Paragraph('Evolución o desglose por grupo', styles['Heading2']),
        _grafico_barras(puntos), Spacer(1, 10), Paragraph('Participación porcentual del desglose', styles['Heading2']),
        _grafico_participacion(puntos), Spacer(1, 12), Paragraph('¿Qué indican estos resultados?', styles['Heading2'])]
    if not cantidad:
        explicacion = 'No se encontraron ventas confirmadas en este período. El gráfico no representa valores inventados.'
    elif not puntos:
        explicacion = 'Se registraron ventas confirmadas, pero no existen datos suficientes para el desglose seleccionado.'
    else:
        destacado, valor = max(puntos, key=lambda x: x[1])
        unidad = 'unidades' if tipo == 'INVENTARIO' else 'S/'
        explicacion = (f'El grupo con mayor valor representado es {destacado}, con '
                       f'{valor:,.0f} {unidad}. Los gráficos corresponden únicamente al período seleccionado.')
    elementos.append(Paragraph(escape(explicacion), styles['BodyText']))
    def pie(canvas, documento):
        canvas.saveState()
        w, h = A4
        canvas.setStrokeColor(colors.HexColor('#D8E3F1'))
        canvas.line(43, 37, w-43, 37)
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#64748B'))
        canvas.drawString(43, 24, 'SalesIA Enterprise | Datos descriptivos, no predicción')
        canvas.drawRightString(w-43, 24, f'Página {documento.page}')
        canvas.restoreState()
    doc.build(elementos, onFirstPage=pie, onLaterPages=pie)
    return stream.getvalue()


def generar_pdf_directo(db, usuario_id, tipo: str, inicio: date, fin: date):
    # Siempre comprobar permiso y empresa antes de consultar datos comerciales.
    empresa_id = _tenant(db, usuario_id, 'reportes.generar')
    validar(tipo, inicio, fin)
    if tipo not in TIPOS_VISUALES:
        raise ReporteError('Tipo no disponible para PDF visual.')
    cantidad, total = db.execute(select(func.count(Venta.id), func.coalesce(func.sum(Venta.total), 0))
                                 .where(*_filtro_ventas(empresa_id, inicio, fin))).one()
    puntos = _serie(db, empresa_id, tipo, inicio, fin)
    contenido = _construir_pdf(tipo, inicio, fin, int(cantidad), total, puntos)
    if not contenido.startswith(b'%PDF-'):
        raise ReporteError('No fue posible generar el PDF.', 500)
    # Sin escrituras de archivos ni de reportes_generados.
    return contenido
