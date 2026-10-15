"""
Script para generar el PDF ejecutivo con la propuesta de mejoras gráficas y UI/UX para SalesIA Enterprise.
"""
import sys
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """Canvas que calcula el número total de páginas dinámicamente."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header (en páginas > 1)
        if self._pageNumber > 1:
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(40, letter[1] - 35, letter[0] - 40, letter[1] - 35)
            self.drawString(40, letter[1] - 30, "SalesIA Enterprise · Propuesta de Mejoras Gráficas y UI/UX")
            self.drawRightString(letter[0] - 40, letter[1] - 30, "Octubre 2026")
        
        # Footer
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(40, 40, letter[0] - 40, 40)
        self.drawString(40, 28, "Confidencial · Documento de Arquitectura y Diseño Frontend")
        self.drawRightString(letter[0] - 40, 28, f"Página {self._pageNumber} de {page_count}")
        self.restoreState()

def generar_pdf():
    pdf_path = "c:/Users/Gabriel/Desktop/SalesIA/Propuesta_Mejoras_Graficas_SalesIA.pdf"
    
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=45,
        bottomMargin=50
    )
    
    styles = getSampleStyleSheet()
    
    # Colores corporativos SalesIA
    c_primary = colors.HexColor("#0F172A")    # Slate 900
    c_cyan = colors.HexColor("#0891B2")       # Cyan 600
    c_cyan_light = colors.HexColor("#ECFEFF") # Cyan 50
    c_blue = colors.HexColor("#2563EB")       # Blue 600
    c_dark = colors.HexColor("#1E293B")       # Slate 800
    c_muted = colors.HexColor("#64748B")      # Slate 500
    c_bg_card = colors.HexColor("#F8FAFC")    # Slate 50
    c_border = colors.HexColor("#E2E8F0")     # Slate 200
    c_green = colors.HexColor("#10B981")      # Emerald 500
    c_amber = colors.HexColor("#F59E0B")      # Amber 500
    c_rose = colors.HexColor("#EF4444")       # Rose 500

    # Estilos de texto
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=c_primary,
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10.5,
        leading=14,
        textColor=c_muted,
        spaceAfter=12
    )

    badge_style = ParagraphStyle(
        'KickerBadge',
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=c_cyan,
        spaceAfter=6
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=c_primary,
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'ItemTitle',
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=c_primary,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyDark',
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=c_dark,
        spaceAfter=4
    )

    body_muted = ParagraphStyle(
        'BodyMuted',
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=c_muted
    )

    table_header = ParagraphStyle(
        'TableHeader',
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )

    table_cell = ParagraphStyle(
        'TableCell',
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=c_dark
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=c_primary
    )

    story = []

    # ------------------ ENCABEZADO / BANNER SUPERIOR ------------------
    story.append(Paragraph("SALESIA ENTERPRISE · CONSULTORÍA ESTRATÉGICA UI/UX & DATA VISUALIZATION", badge_style))
    story.append(Paragraph("Propuesta de Mejoras Gráficas y Visuales de Alto Impacto", title_style))
    story.append(Paragraph(
        "Optimizaciones visuales fundamentadas en la arquitectura actual para transformar datos operativos en decisiones empresariales inmediatas.",
        subtitle_style
    ))
    
    # Metadata Box
    meta_data = [
        [
            Paragraph("<b>Fecha:</b> Octubre 2026", body_style),
            Paragraph("<b>Stack:</b> React 19 + Tailwind + Recharts", body_style),
            Paragraph("<b>Enfoque:</b> Cero backend extra (100% endpoints actuales)", body_style)
        ]
    ]
    t_meta = Table(meta_data, colWidths=[150, 190, 192])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_bg_card),
        ('BOX', (0,0), (-1,-1), 1, c_border),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))

    # ------------------ INTRODUCCIÓN ------------------
    story.append(Paragraph("1. Objetivo y Criterios de Selección", h1_style))
    story.append(Paragraph(
        "El objetivo de estas propuestas es <b>maximizar el valor visual y analítico</b> que perciben tanto la gerencia como los operadores comerciales y de almacén de la empresa. "
        "Todas las sugerencias respetan la regla crítica de <b>no requerir nuevos endpoints en el backend</b>, aprovechando datos ya estructurados en FastAPI (ventas, pedidos, inventario, pagos, entregas y RFM) para presentarlos de forma accionable y moderna.",
        body_style
    ))
    story.append(Spacer(1, 8))

    # ------------------ LAS 7 PROPUESTAS ------------------
    story.append(Paragraph("2. Catálogo de Mejoras Gráficas Recomendadas", h1_style))

    propuestas = [
        {
            "num": "01",
            "titulo": "Embudo Visual del Ciclo Comercial (Pipeline & Funnel Chart)",
            "cat": "GERENCIA COMERCIAL Y FINANZAS",
            "color_cat": c_blue,
            "desc": "Representación gráfica de embudo o diagrama de flujo con tasas de conversión porcentuales y volumen monetario retenido entre cada fase: <b>Borrador &rarr; Confirmado &rarr; Venta &rarr; Cobrado &rarr; Entregado</b>.",
            "valor": "Permite a la dirección financiera identificar <b>cuellos de botella en segundos</b> (por ejemplo: pedidos confirmados pendientes de cobro vs ventas pagadas pendientes de despacho en almacén) sin necesidad de revisar tablas individuales.",
            "datos": "Agrupaciones ya provistas en <code>api.listarPedidos</code>, <code>api.getVentas</code>, <code>api.resumenPagos</code> y <code>api.obtenerEntregaVenta</code>."
        },
        {
            "num": "02",
            "titulo": "Medidor Visual de Cobertura de Stock (Stock Runway & Gauges)",
            "cat": "OPERACIONES Y ALMACÉN",
            "color_cat": c_amber,
            "desc": "Indicador tipo velocímetro/gauge y barra de salud que calcula los <b>días de inventario disponible restante</b> basado en la velocidad de consumo: <i>(Stock Actual / Ventas Promedio Diarias)</i>.",
            "valor": "Alertas preventivas visuales: 🟢 <b>> 30 días</b> (Óptimo), 🟡 <b>8–15 días</b> (Reabastecimiento preventivo recomendado), 🔴 <b>< 7 días</b> (Riesgo crítico de quiebre de stock). Evita ventas que no puedan surtirse.",
            "datos": "Cruce reactivo entre <code>api.listarInventarioOperativo</code> y <code>api.getSerieVentas</code>."
        },
        {
            "num": "03",
            "titulo": "Matriz Visual RFM de Clientes (Scatter Plot / Matriz 2x2)",
            "cat": "VENTAS Y RETENCIÓN DE CLIENTES",
            "color_cat": c_cyan,
            "desc": "Gráfico de dispersión (Scatter Plot en Recharts) donde cada cliente es una burbuja posicionada en 4 cuadrantes según su <b>Recencia</b> (tiempo desde su última compra) y su <b>Frecuencia/Monto</b> acumulado.",
            "valor": "Segmenta visualmente en: <i>Clientes Estrella</i>, <i>Nuevos Prometedores</i>, <i>En Riesgo de Abandono</i> y <i>Perdidos</i>. Facilita que los ejecutivos comerciales sepan a quién llamar inmediatamente para fidelizar.",
            "datos": "Directamente alimentado por el endpoint especializado <code>api.getClientesVisual</code> (/api/mejoras/clientes)."
        },
        {
            "num": "04",
            "titulo": "Stepper Interactivo de Trazabilidad del Pedido (Order Journey)",
            "cat": "OPERACIÓN DIARIA Y SERVICIO AL CLIENTE",
            "color_cat": c_green,
            "desc": "Línea de tiempo horizontal con iconos de estado dentro del detalle de cada pedido/venta: <b>1. Creado &rarr; 2. Reserva confirmada &rarr; 3. Facturación &rarr; 4. Cobranza validada &rarr; 5. Despacho completado</b>.",
            "valor": "Elimina las llamadas y fricciones internas entre vendedores, facturación y almacén. Cualquier usuario puede responder a un cliente el estado exacto de su pedido en 3 segundos.",
            "datos": "Consultas combinadas a <code>api.obtenerPedido</code>, <code>api.obtenerVenta</code>, <code>api.resumenPagos</code> y <code>api.obtenerEntregaVenta</code>."
        },
        {
            "num": "05",
            "titulo": "Mini-gráficos de Tendencia (Sparklines) Incrustados en Tablas",
            "cat": "MONITOREO RÁPIDO DE CATÁLOGO",
            "color_cat": c_primary,
            "desc": "Diminuta curva gráfica (SVG/Recharts de 60x18px) incrustada en cada fila de las tablas de productos y clientes, mostrando la tendencia de ventas de los últimos 14 a 30 días.",
            "valor": "Detecta de un vistazo qué productos están acelerando su demanda ↗ y cuáles se están estancando ↘ sin necesidad de abrir fichas individuales ni exportar reportes a Excel.",
            "datos": "Serie de puntos temporales obtenida mediante <code>api.getSerieVentas</code> filtrada por ítem."
        },
        {
            "num": "06",
            "titulo": "Paleta de Comandos Global Rápida (Command Palette: Ctrl + K)",
            "cat": "PRODUCTIVIDAD Y EXPERIENCIA DE USUARIO (UX)",
            "color_cat": c_blue,
            "desc": "Buscador flotante estilo Spotlight que se activa en cualquier parte del portal presionando <b>Ctrl + K</b> (o Cmd + K), permitiendo buscar simultáneamente por código de pedido, RUC, cliente o SKU.",
            "valor": "Aumenta drásticamente la velocidad de trabajo para cajeros, administradores y operadores habituales, reduciendo el uso del ratón y el tiempo de consulta de 25 segundos a menos de 2 segundos.",
            "datos": "Búsquedas cacheadas en cliente con filtros en los endpoints existentes de clientes, productos y órdenes."
        },
        {
            "num": "07",
            "titulo": "Mapa de Calor Semanal de Actividad Comercial (Activity Heatmap)",
            "cat": "PLANIFICACIÓN Y LOGÍSTICA",
            "color_cat": c_dark,
            "desc": "Matriz visual de 7 días de la semana &times; bloques horarios (mañana, tarde, noche) coloreada según la intensidad de facturación y generación de pedidos.",
            "valor": "Permite a la gerencia identificar con precisión quirúrgica las horas punta de operación para programar turnos de vendedores, refuerzos en caja o ventanas seguras de inventario físico.",
            "datos": "Marcas de tiempo <code>created_at</code> de ventas y pedidos ya provistas por la base de datos."
        }
    ]

    for p in propuestas:
        p_card = [
            [
                Paragraph(f"<b>PROPUESTA #{p['num']} · {p['cat']}</b>", ParagraphStyle('CatBadge', fontName='Helvetica-Bold', fontSize=7.5, textColor=p['color_cat'])),
            ],
            [
                Paragraph(p['titulo'], h2_style),
            ],
            [
                Paragraph(f"<b>¿Qué es y cómo se visualiza?</b> {p['desc']}", body_style),
            ],
            [
                Paragraph(f"<b>Valor tangible para la empresa:</b> {p['valor']}", body_style),
            ],
            [
                Paragraph(f"<b>Endpoints ya existentes que lo alimentan:</b> {p['datos']}", body_muted),
            ]
        ]
        t_card = Table(p_card, colWidths=[532])
        t_card.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), c_bg_card),
            ('BOX', (0,0), (-1,-1), 1, c_border),
            ('LINELEFT', (0,0), (0,-1), 3.5, p['color_cat']),
            ('PADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,-1), (-1,-1), 8),
        ]))
        story.append(t_card)
        story.append(Spacer(1, 8))

    # ------------------ MATRIZ DE PRIORIZACIÓN ------------------
    story.append(KeepTogether([
        Paragraph("3. Matriz de Priorización: Impacto vs. Esfuerzo de Implementación", h1_style),
        Paragraph("Evaluación estratégica para definir el orden óptimo de desarrollo según el retorno para la operación:", body_style),
        Spacer(1, 6)
    ]))

    tabla_data = [
        [
            Paragraph("Propuesta Visual", table_header),
            Paragraph("Área de Impacto", table_header),
            Paragraph("Impacto Negocio", table_header),
            Paragraph("Esfuerzo UI", table_header),
            Paragraph("Prioridad Recomendada", table_header),
        ],
        [
            Paragraph("<b>1. Stepper Trazabilidad Pedido</b>", table_cell_bold),
            Paragraph("Ventas / Almacén / Caja", table_cell),
            Paragraph("⭐⭐⭐⭐⭐ (Crítico)", table_cell),
            Paragraph("Bajo (1–2 días)", table_cell),
            Paragraph("<b>FASE 1 (Inmediata)</b>", table_cell_bold),
        ],
        [
            Paragraph("<b>2. Embudo Visual de Pipeline</b>", table_cell_bold),
            Paragraph("Gerencia y Finanzas", table_cell),
            Paragraph("⭐⭐⭐⭐⭐ (Alto)", table_cell),
            Paragraph("Medio (2–3 días)", table_cell),
            Paragraph("<b>FASE 1 (Inmediata)</b>", table_cell_bold),
        ],
        [
            Paragraph("<b>3. Cobertura de Stock (Runway)</b>", table_cell_bold),
            Paragraph("Compras e Inventario", table_cell),
            Paragraph("⭐⭐⭐⭐⭐ (Alto)", table_cell),
            Paragraph("Bajo (1–2 días)", table_cell),
            Paragraph("<b>FASE 1 (Inmediata)</b>", table_cell_bold),
        ],
        [
            Paragraph("<b>4. Matriz RFM Clientes</b>", table_cell_bold),
            Paragraph("Marketing / Fidelización", table_cell),
            Paragraph("⭐⭐⭐⭐ (Medio-Alto)", table_cell),
            Paragraph("Medio (2 días)", table_cell),
            Paragraph("<b>FASE 2 (Táctica)</b>", table_cell),
        ],
        [
            Paragraph("<b>5. Mini-gráficos Sparklines</b>", table_cell_bold),
            Paragraph("Catálogo y Gestión", table_cell),
            Paragraph("⭐⭐⭐ (Medio)", table_cell),
            Paragraph("Medio (2 días)", table_cell),
            Paragraph("<b>FASE 2 (Táctica)</b>", table_cell),
        ],
        [
            Paragraph("<b>6. Command Palette (Ctrl+K)</b>", table_cell_bold),
            Paragraph("Productividad Operativa", table_cell),
            Paragraph("⭐⭐⭐⭐ (Alto uso)", table_cell),
            Paragraph("Medio (2–3 días)", table_cell),
            Paragraph("<b>FASE 3 (Productividad)</b>", table_cell),
        ],
        [
            Paragraph("<b>7. Mapa Calor Semanal</b>", table_cell_bold),
            Paragraph("Planificación de Turnos", table_cell),
            Paragraph("⭐⭐⭐ (Estratégico)", table_cell),
            Paragraph("Bajo (1–2 días)", table_cell),
            Paragraph("<b>FASE 3 (Productividad)</b>", table_cell),
        ]
    ]

    t_prioridad = Table(tabla_data, colWidths=[150, 110, 95, 87, 90])
    t_prioridad.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('PADDING', (0,0), (-1,-1), 5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_card]),
    ]))
    story.append(t_prioridad)
    story.append(Spacer(1, 12))

    # ------------------ HOJA DE RUTA RECOMENDADA ------------------
    story.append(KeepTogether([
        Paragraph("4. Hoja de Ruta de Implementación Sugerida (Roadmap)", h1_style),
        Paragraph(
            "<b>Fase 1 · Quick Wins Operativos (Semana 1):</b><br/>"
            "Implementar el <b>Stepper de Trazabilidad</b> en el modal de pedidos/ventas y el <b>Medidor de Cobertura de Stock</b> en el inventario. Ambas mejoras resuelven problemas diarios de coordinación entre áreas sin tocar el backend.<br/><br/>"
            "<b>Fase 2 · Inteligencia Comercial Ejecutiva (Semana 2):</b><br/>"
            "Integrar el <b>Embudo Visual de Pipeline</b> en el Dashboard principal y el <b>Scatter Plot RFM</b> en la vista de clientes para facilitar la retención comercial proactiva.<br/><br/>"
            "<b>Fase 3 · Experiencia y Alta Productividad (Semana 3):</b><br/>"
            "Agregar los <b>Sparklines</b> en las tablas de mayor densidad y habilitar la <b>Command Palette (Ctrl + K)</b> para navegación ultra-rápida.",
            body_style
        ),
        Spacer(1, 14),
        HRFlowable(width="100%", thickness=1, color=c_border, spaceBefore=4, spaceAfter=8),
        Paragraph(
            "<i>Documento generado automáticamente para el proyecto SalesIA Enterprise. Todos los derechos reservados.</i>",
            ParagraphStyle('FooterNote', fontName='Helvetica-Oblique', fontSize=8, textColor=c_muted, alignment=1)
        )
    ]))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF generado exitosamente en: {pdf_path}")

if __name__ == "__main__":
    generar_pdf()
