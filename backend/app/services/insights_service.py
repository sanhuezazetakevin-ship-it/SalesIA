"""FASE 11: reglas explicables sobre análisis persistidos, sin modelos generativos.

Nunca acepta datos de soporte calculados por el navegador; todos provienen de
registros COMPLETADOS, consultados por empresa. La Session la administra la ruta.
"""
from decimal import Decimal, InvalidOperation
from sqlalchemy import select
from app.models.analisis_estadistico import AnalisisEstadistico
from app.models.analisis_probabilidad import AnalisisProbabilidad
from app.models.insight import Insight
from app.services.venta_service import _validar_operador, VentaServiceError

VERSION_REGLAS = '11.1'

class InsightsError(ValueError):
    def __init__(self, message, status_code=422):
        super().__init__(message)
        self.status_code = status_code


def _empresa(db, usuario_id, permiso):
    try:
        _, empresa = _validar_operador(db, usuario_id=usuario_id, permiso=permiso)
    except VentaServiceError as exc:
        raise InsightsError('No autorizado para Insights.', 403) from exc
    return empresa.id


def _decimal(valor):
    if isinstance(valor, bool) or valor is None:
        return None
    try:
        numero = Decimal(str(valor))
    except (TypeError, InvalidOperation, ValueError):
        return None
    return numero if numero.is_finite() else None


def generar_reglas(tipo, resultados):
    """Resultados compactos y deterministas; sin interpretación causal."""
    if not isinstance(resultados, dict):
        raise InsightsError('El análisis no contiene resultados válidos.')
    datos = resultados.get('contenido') if tipo == 'estadistico' else resultados
    if not isinstance(datos, dict):
        raise InsightsError('El análisis no contiene resultados válidos.')
    reglas = []
    if tipo == 'estadistico':
        cantidad = datos.get('cantidad_ventas')
        total = _decimal(datos.get('total_ventas'))
        media = _decimal(datos.get('ticket_promedio'))
        mediana = _decimal(datos.get('mediana_ventas'))
        if type(cantidad) is not int or cantidad < 0 or total is None or total < 0:
            raise InsightsError('Métricas de ventas inválidas.')
        if cantidad == 0 and total != 0:
            raise InsightsError('Total incompatible con cero ventas.')
        if cantidad == 0:
            reglas.append(dict(tipo_insight='VENTAS', prioridad='BAJA', titulo='Sin ventas confirmadas en el período',
                descripcion='El análisis contiene cero ventas confirmadas en el intervalo consultado.',
                recomendacion='Revisar el período y la actividad comercial antes de sacar conclusiones.',
                datos_soporte={'regla': 'SIN_VENTAS', 'cantidad_ventas': 0, 'total_ventas': str(total)}))
        elif media is not None and mediana is not None and media >= 0 and mediana >= 0:
            reglas.append(dict(tipo_insight='VENTAS', prioridad='BAJA', titulo='Resumen del ticket de ventas',
                descripcion='La media y la mediana describen el valor de las ventas confirmadas; no implican una tendencia.',
                recomendacion='Comparar con otros períodos equivalentes antes de decidir acciones.',
                datos_soporte={'regla': 'TICKET_DESCRIPTIVO', 'cantidad_ventas': cantidad,
                    'total_ventas': str(total), 'media': str(media), 'mediana': str(mediana)}))
        else:
            raise InsightsError('Media o mediana inválida en el análisis.')
    elif tipo == 'probabilidad':
        n = datos.get('total_observaciones')
        p = _decimal(datos.get('probabilidad_pagado'))
        conteos = datos.get('conteos')
        if type(n) is not int or n < 0 or not isinstance(conteos, dict):
            raise InsightsError('Frecuencias de probabilidad inválidas.')
        pagado = conteos.get('pagado')
        if type(pagado) is not int or not 0 <= pagado <= n:
            raise InsightsError('Conteo de ventas pagadas inválido.')
        if n == 0:
            if p is not None:
                raise InsightsError('Probabilidad inválida para una muestra vacía.')
            reglas.append(dict(tipo_insight='GENERAL', prioridad='BAJA', titulo='Sin observaciones para el análisis probabilístico',
                descripcion='No hay ventas confirmadas en la muestra; la probabilidad de pago es indefinida.',
                recomendacion='Ampliar el período o verificar la disponibilidad de datos.',
                datos_soporte={'regla': 'MUESTRA_VACIA', 'total_observaciones': 0}))
        elif p is not None and 0 <= p <= 1:
            if abs(p - Decimal(pagado) / Decimal(n)) > Decimal('0.00005'):
                raise InsightsError('Probabilidad incompatible con los conteos.')
            reglas.append(dict(tipo_insight='RENDIMIENTO', prioridad='MEDIA' if p < Decimal('0.50') else 'BAJA',
                titulo='Frecuencia observada de ventas pagadas',
                descripcion='La proporción de ventas marcadas como PAGADO se calculó sobre la muestra; no es una predicción de cobro futuro.',
                recomendacion='Revisar el estado de pagos y comparar con períodos similares.',
                datos_soporte={'regla': 'FRECUENCIA_PAGADO', 'total_observaciones': n,
                    'ventas_pagadas': pagado, 'probabilidad_pagado': str(p)}))
        else:
            raise InsightsError('Probabilidad de pago inválida.')
    else:
        raise InsightsError('Tipo de análisis inválido.')
    return reglas


def generar_insights(db, *, usuario_id, tipo, analisis_id):
    if tipo not in ('estadistico', 'probabilidad') or type(analisis_id) is not int or analisis_id <= 0:
        raise InsightsError('Origen de análisis inválido.')
    eid = _empresa(db, usuario_id, 'analitica.ejecutar')
    modelo = AnalisisEstadistico if tipo == 'estadistico' else AnalisisProbabilidad
    origen = db.scalar(select(modelo).where(modelo.id == analisis_id, modelo.empresa_id == eid))
    if origen is None:
        raise InsightsError('Análisis no encontrado.', 404)
    if origen.estado != 'COMPLETADO':
        raise InsightsError('El análisis debe estar COMPLETADO.')
    # Evita duplicaciones ante llamadas repetidas; bloqueo dentro de la transacción.
    db.scalar(select(modelo.id).where(modelo.id == analisis_id, modelo.empresa_id == eid).with_for_update())
    origen_col = (Insight.analisis_estadistico_id if tipo == 'estadistico' else Insight.analisis_probabilidad_id)
    existentes = db.scalars(select(Insight).where(Insight.empresa_id == eid, origen_col == analisis_id)
        .order_by(Insight.id)).all()
    if existentes:
        return existentes
    reglas = generar_reglas(tipo, origen.resultados)
    registros = []
    for regla in reglas:
        evidencia = dict(regla['datos_soporte'])
        evidencia.update({'version_reglas': VERSION_REGLAS, 'origen_tipo': tipo, 'origen_id': analisis_id})
        registro = Insight(empresa_id=eid, analisis_estadistico_id=analisis_id if tipo == 'estadistico' else None,
            analisis_probabilidad_id=analisis_id if tipo == 'probabilidad' else None,
            tipo_insight=regla['tipo_insight'], prioridad=regla['prioridad'],
            titulo=regla['titulo'], descripcion=regla['descripcion'],
            recomendacion=regla['recomendacion'], datos_soporte=evidencia,
            estado='NUEVO')
        db.add(registro)
        registros.append(registro)
    db.flush()
    return registros


def listar_insights(db, *, usuario_id, limite=20, estado=None, tipo=None):
    if type(limite) is not int or not 1 <= limite <= 100:
        raise InsightsError('Límite fuera de rango.')
    eid = _empresa(db, usuario_id, 'analitica.ver')
    consulta = select(Insight).where(Insight.empresa_id == eid)
    if estado is not None:
        consulta = consulta.where(Insight.estado == estado)
    if tipo is not None:
        consulta = consulta.where(Insight.tipo_insight == tipo)
    return db.scalars(consulta.order_by(Insight.created_at.desc(), Insight.id.desc()).limit(limite)).all()


def obtener_insight(db, *, usuario_id, insight_id):
    eid = _empresa(db, usuario_id, 'analitica.ver')
    return db.scalar(select(Insight).where(Insight.id == insight_id, Insight.empresa_id == eid))


def actualizar_estado(db, *, usuario_id, insight_id, estado):
    if estado not in ('REVISADO', 'DESCARTADO'):
        raise InsightsError('Estado inválido.')
    eid = _empresa(db, usuario_id, 'analitica.ejecutar')
    registro = db.scalar(select(Insight).where(Insight.id == insight_id, Insight.empresa_id == eid).with_for_update())
    if registro is None:
        raise InsightsError('Insight no encontrado.', 404)
    registro.estado = estado
    db.flush()
    return registro
