"""Reglas puras para presentar resultados empresariales; no son predicciones ML entrenadas."""
from decimal import Decimal
from datetime import date


def cambio_porcentual(actual, anterior):
    a, b = Decimal(str(actual)), Decimal(str(anterior))
    return None if not b else round(float((a-b)*100/b), 2)


def presentacion_kpi(actual, anterior, unidad='PEN', titulo='Ventas'):
    delta = cambio_porcentual(actual, anterior)
    mensaje = ('No hay período anterior comparable.' if delta is None else
               ('Aumentó respecto al período anterior.' if delta > 0 else
                'Disminuyó respecto al período anterior.' if delta < 0 else
                'Se mantuvo igual al período anterior.'))
    return {'titulo': titulo, 'valor': str(actual), 'unidad': unidad,
            'variacion_porcentual': delta, 'explicacion': mensaje,
            'grafico': {'tipo': 'barra', 'etiquetas': ['Anterior', 'Actual'],
                        'valores': [float(anterior), float(actual)]}}


def analizar_stock(stock, unidades_vendidas, dias, horizonte=14):
    """Proyección simple por promedio móvil del rango consultado, sin afirmar precisión ML."""
    if dias < 1 or horizonte < 1:
        raise ValueError('Los días y horizonte deben ser positivos.')
    stock, unidades = Decimal(str(stock)), Decimal(str(unidades_vendidas))
    if stock < 0 or unidades < 0:
        raise ValueError('Cantidades inválidas.')
    diario = unidades / Decimal(dias)
    pronostico = diario * horizonte
    cobertura = round(float(stock / diario), 1) if diario else None
    riesgo = 'SIN_HISTORIAL' if not unidades else 'ALTO' if stock < pronostico else 'NORMAL'
    return {'stock_actual': float(stock), 'demanda_estimada': round(float(pronostico),3),
            'dias_cobertura': cobertura, 'riesgo': riesgo,
            'metodo': 'promedio_historico_simple', 'es_modelo_entrenado': False,
            'advertencia': ('Sin ventas suficientes para estimar demanda.' if not unidades else
                            'Proyección orientativa basada en ventas observadas; no garantiza demanda futura.'),
            'grafico': {'tipo': 'barra', 'etiquetas': ['Stock actual', 'Demanda estimada'],
                        'valores': [float(stock), round(float(pronostico),3)]}}


def segmento_cliente(ultima_compra: date | None, compras: int, gasto, referencia: date):
    if ultima_compra is None or not compras:
        return 'SIN_COMPRAS'
    dias = (referencia - ultima_compra).days
    if dias < 0:
        raise ValueError('Fecha de compra posterior a referencia.')
    if dias > 90:
        return 'INACTIVO'
    if compras >= 5:
        return 'FRECUENTE'
    if compras >= 2:
        return 'RECURRENTE'
    return 'NUEVO'


def tarjeta_alerta(codigo, titulo, descripcion, nivel, referencia=None):
    return {'codigo': codigo, 'titulo': titulo, 'descripcion': descripcion,
            'nivel': nivel, 'referencia': referencia, 'leida': None,
            'persistida': False}


def rfm_cliente(ultima_compra, compras, gasto, referencia):
    """RFM interpretable de 1 a 5, con umbrales declarados en vez de cuantiles inestables."""
    from datetime import date
    n=int(compras)
    v=Decimal(str(gasto))
    if n<0 or v<0:
        raise ValueError('Compras e importes no negativos.')
    if n==0 or ultima_compra is None:
        return {'recencia_dias':None,'frecuencia':0,'valor_monetario':0.0,
                'r':1,'f':1,'m':1,'codigo_rfm':'111','segmento':'SIN_COMPRAS',
                'explicacion':'El cliente no tiene compras confirmadas hasta la fecha de referencia.'}
    dias=(referencia-ultima_compra).days
    if dias<0:
        raise ValueError('La última compra no puede estar en el futuro.')
    r=5 if dias<=30 else 4 if dias<=60 else 3 if dias<=90 else 2 if dias<=180 else 1
    freq=5 if n>=10 else 4 if n>=5 else 3 if n>=3 else 2 if n==2 else 1
    mont=5 if v>=Decimal('5000') else 4 if v>=Decimal('2000') else 3 if v>=Decimal('500') else 2 if v>=Decimal('100') else 1
    if r<=2:
        segmento='REACTIVACION'
    elif r>=4 and freq>=4 and mont>=4:
        segmento='ALTO_VALOR'
    elif freq>=3:
        segmento='FRECUENTE'
    else:
        segmento='OCASIONAL'
    return {'recencia_dias':dias,'frecuencia':n,'valor_monetario':float(v),
            'r':r,'f':freq,'m':mont,'codigo_rfm':f'{r}{freq}{mont}','segmento':segmento,
            'explicacion':f'Última compra hace {dias} días; {n} compras confirmadas por S/ {v:.2f}.'}
