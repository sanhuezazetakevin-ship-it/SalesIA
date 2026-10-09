"""MVP-01-E.1: probabilidades descriptivas exactas a partir de ventas ya filtradas.

Este módulo no consulta bases de datos ni autentica usuarios. El futuro servicio HTTP
DEBE filtrar por empresa, periodo y estado CONFIRMADA antes de llamar estas funciones.
"""
from collections import Counter
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

PRECISION = Decimal('0.0001')
ESTADOS_PAGO = ('PENDIENTE', 'PARCIAL', 'PAGADO')


def _decimal_no_negativo(valor):
    if isinstance(valor, bool):
        raise ValueError('Importe inválido: booleano.')
    try:
        d = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError('Importe inválido.') from exc
    if not d.is_finite() or d < 0:
        raise ValueError('Importe inválido: debe ser finito y no negativo.')
    return d


def _razon(numerador: int, denominador: int) -> str | None:
    """None significa probabilidad indefinida por denominador cero."""
    if denominador == 0:
        return None
    if not (0 <= numerador <= denominador):
        raise ValueError('Frecuencia fuera de rango.')
    return str((Decimal(numerador) / Decimal(denominador)).quantize(
        PRECISION, rounding=ROUND_HALF_UP
    ))


def calcular_probabilidades(ventas, *, umbral_importe='100.00'):
    """Analiza una población de ventas confirmadas de una sola empresa y periodo.

    ventas: iterable de pares (importe_total, estado_pago). "Alto" significa
    importe >= umbral, inclusivo. Los estados deben ser los tres admitidos.
    Las probabilidades se entregan como cadenas decimales de cuatro cifras;
    si el denominador es cero se entrega None (JSON null).
    """
    umbral = _decimal_no_negativo(umbral_importe)
    totales = Counter({e: 0 for e in ESTADOS_PAGO})
    n = altos = pagados = altos_pagados = 0
    for importe, estado in ventas:
        valor = _decimal_no_negativo(importe)
        if estado not in ESTADOS_PAGO:
            raise ValueError('Estado de pago no admitido.')
        n += 1
        totales[estado] += 1
        alto = valor >= umbral
        pagado = estado == 'PAGADO'
        altos += int(alto)
        pagados += int(pagado)
        altos_pagados += int(alto and pagado)

    return {
        'total_observaciones': n,
        'umbral_importe_alto': str(umbral),
        'criterio_importe_alto': 'importe >= umbral_importe_alto',
        'conteos': {
            'importe_alto': altos,
            'pagado': pagados,
            'importe_alto_y_pagado': altos_pagados,
        },
        'variable_aleatoria_estado_pago': [
            {'estado': estado, 'frecuencia_absoluta': totales[estado],
             'probabilidad': _razon(totales[estado], n)}
            for estado in ESTADOS_PAGO
        ],
        'probabilidad_pagado': _razon(pagados, n),
        'probabilidad_importe_alto': _razon(altos, n),
        'probabilidad_conjunta_alto_y_pagado': _razon(altos_pagados, n),
        'probabilidad_pagado_dado_alto': _razon(altos_pagados, altos),
        # Bayes: P(Alto|Pagado) = P(Pagado|Alto)*P(Alto)/P(Pagado).
        # El cálculo mediante conteos evita errores por redondeos intermedios.
        'bayes_importe_alto_dado_pagado': _razon(altos_pagados, pagados),
    }
