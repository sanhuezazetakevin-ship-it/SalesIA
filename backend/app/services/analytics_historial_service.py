"""MVP-01-F.1: persistencia interna con autorización y aislamiento empresarial.

No expone endpoints ni altera el esquema. Se usa sólo con una Session de Testing
hasta completar pruebas y autorización específica para escrituras HTTP.
"""
from datetime import date, datetime, time, timezone, timedelta
from decimal import Decimal, InvalidOperation
from sqlalchemy import select
from app.models.analisis_estadistico import AnalisisEstadistico
from app.models.analisis_probabilidad import AnalisisProbabilidad
from app.services.venta_service import _validar_operador, VentaServiceError

VERSION = '1.0'

class AnalyticsHistorialError(ValueError):
    pass


def _empresa_autorizada(db, usuario_id):
    try:
        _, empresa = _validar_operador(db, usuario_id=usuario_id, permiso='ventas.ver')
    except VentaServiceError as exc:
        raise AnalyticsHistorialError('No autorizado para consultar análisis.') from exc
    return empresa.id


def _periodo(fecha_inicio: date, fecha_fin: date):
    if not isinstance(fecha_inicio, date) or not isinstance(fecha_fin, date):
        raise AnalyticsHistorialError('Las fechas deben ser fechas válidas.')
    if fecha_fin < fecha_inicio or (fecha_fin - fecha_inicio).days > 366:
        raise AnalyticsHistorialError('Periodo inválido o mayor a 367 días.')
    inicio = datetime.combine(fecha_inicio, time.min, tzinfo=timezone.utc)
    # La BD almacena periodo inclusivo; el algoritmo de ventas usa fin exclusivo.
    fin = datetime.combine(fecha_fin + timedelta(days=1), time.min, tzinfo=timezone.utc) - timedelta(microseconds=1)
    return inicio, fin


def _json_seguro(value):
    """Convierte sólo tipos permitidos a JSON sin NaN/Infinity ni valores opacos."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise AnalyticsHistorialError('Número no finito en resultados.')
        return str(value)
    if isinstance(value, float):
        raise AnalyticsHistorialError('Use Decimal o cadenas, no float en resultados.')
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        if not all(isinstance(k, str) for k in value):
            raise AnalyticsHistorialError('Las claves JSON deben ser texto.')
        return {k: _json_seguro(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_seguro(x) for x in value]
    raise AnalyticsHistorialError('Tipo de dato no serializable.')


def guardar_estadistico(db, *, usuario_id: int, nombre: str, fecha_inicio: date,
                        fecha_fin: date, resultados: dict):
    if not isinstance(nombre, str) or not nombre.strip() or len(nombre.strip()) > 150:
        raise AnalyticsHistorialError('Nombre inválido.')
    if not isinstance(resultados, dict):
        raise AnalyticsHistorialError('Resultados inválidos.')
    inicio, fin = _periodo(fecha_inicio, fecha_fin)
    empresa_id = _empresa_autorizada(db, usuario_id)
    instante = datetime.now(timezone.utc)
    objeto = AnalisisEstadistico(
        empresa_id=empresa_id, nombre=nombre.strip(), tipo_analisis='VENTAS',
        estado='COMPLETADO', fecha_inicio=inicio, fecha_fin=fin,
        resultados={'origen': 'MVP-01', 'usuario_ejecutor_id': usuario_id,
                    'contenido': _json_seguro(resultados)},
        version_calculo=VERSION, fecha_calculo=instante,
    )
    db.add(objeto)
    db.flush()
    return objeto


def guardar_probabilidad(db, *, usuario_id: int, fecha_inicio: date, fecha_fin: date,
                          resultados: dict, umbral_importe: str | Decimal):
    if not isinstance(resultados, dict):
        raise AnalyticsHistorialError('Resultados inválidos.')
    inicio, fin = _periodo(fecha_inicio, fecha_fin)
    try:
        umbral = Decimal(str(umbral_importe))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise AnalyticsHistorialError('Umbral inválido.') from exc
    if not umbral.is_finite() or umbral < 0:
        raise AnalyticsHistorialError('Umbral inválido.')
    empresa_id = _empresa_autorizada(db, usuario_id)
    instante = datetime.now(timezone.utc)
    p = resultados.get('probabilidad_pagado')
    if p is not None:
        try:
            p = Decimal(str(p))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise AnalyticsHistorialError('Probabilidad inválida.') from exc
        if not p.is_finite() or not 0 <= p <= 1:
            raise AnalyticsHistorialError('Probabilidad fuera de rango.')
    objeto = AnalisisProbabilidad(
        empresa_id=empresa_id, tipo_analisis='OTRO',
        entidad='VENTAS', modelo_nombre='FRECUENCIAS_BAYES', modelo_version=VERSION,
        estado='COMPLETADO', probabilidad=p,
        resultado_predicho='ANALISIS_DESCRIPTIVO', fecha_prediccion=instante,
        datos_entrada={'fecha_inicio': inicio.isoformat(), 'fecha_fin': fin.isoformat(),
                       'umbral_importe_alto': str(umbral), 'usuario_ejecutor_id': usuario_id},
        resultados=_json_seguro(resultados),
    )
    db.add(objeto)
    db.flush()
    return objeto


def listar_historial(db, *, usuario_id: int, tipo: str = 'estadistico', limite: int = 20):
    if tipo not in ('estadistico', 'probabilidad'):
        raise AnalyticsHistorialError('Tipo inválido.')
    if not isinstance(limite, int) or isinstance(limite, bool) or not 1 <= limite <= 100:
        raise AnalyticsHistorialError('Límite fuera de rango.')
    empresa_id = _empresa_autorizada(db, usuario_id)
    modelo = AnalisisEstadistico if tipo == 'estadistico' else AnalisisProbabilidad
    return db.scalars(select(modelo).where(modelo.empresa_id == empresa_id)
                      .order_by(modelo.created_at.desc(), modelo.id.desc())
                      .limit(limite)).all()


def obtener_historial(db, *, usuario_id: int, tipo: str, analisis_id: int):
    if tipo not in ('estadistico', 'probabilidad'):
        raise AnalyticsHistorialError('Tipo inválido.')
    if not isinstance(analisis_id, int) or isinstance(analisis_id, bool) or analisis_id <= 0:
        raise AnalyticsHistorialError('Identificador inválido.')
    empresa_id = _empresa_autorizada(db, usuario_id)
    modelo = AnalisisEstadistico if tipo == 'estadistico' else AnalisisProbabilidad
    return db.scalar(select(modelo).where(modelo.id == analisis_id, modelo.empresa_id == empresa_id))
