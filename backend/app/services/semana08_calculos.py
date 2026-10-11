"""Semana 08. Estadística reproducible. Resultados descriptivos, no consejos comerciales automáticos."""
from math import erf, sqrt, isfinite
from statistics import mean, median, variance, pvariance, stdev, pstdev


def resumen_semana08(valores, *, hipotesis_media=None, alfa=0.05):
    """Prueba t bilateral de una muestra; requiere scipy, sin interpolaciones del valor p."""
    xs = [float(x) for x in valores]
    if len(xs) > 50000:
        raise ValueError('Máximo 50000 observaciones.')
    if any(not isfinite(x) or x < 0 for x in xs):
        raise ValueError('Los valores deben ser números finitos no negativos.')
    if not 0 < alfa < 1:
        raise ValueError('alfa debe encontrarse entre 0 y 1.')
    if hipotesis_media is not None and (not isfinite(float(hipotesis_media)) or float(hipotesis_media) < 0):
        raise ValueError('La media hipotética debe ser finita y no negativa.')
    if not xs:
        return {'cantidad': 0, 'sin_datos': True, 'media': None, 'mediana': None,
                'varianza_poblacional': None, 'desviacion_poblacional': None,
                'varianza_muestral': None, 'desviacion_muestral': None,
                'esperanza_empirica': None, 'histograma': {'tipo':'barra','etiquetas':[],'valores':[]},
                'contraste': None, 'explicacion': 'No hay ventas confirmadas en el período.'}
    n=len(xs)
    mu=mean(xs)
    lo=min(xs); hi=max(xs)
    if lo==hi:
        labels=[f'{lo:.2f}']; counts=[n]
    else:
        bins=min(12, max(1, round(sqrt(n))))
        width=(hi-lo)/bins
        counts=[0]*bins
        for v in xs:
            idx=min(bins-1,int((v-lo)/width))
            counts[idx]+=1
        labels=[f'{lo+i*width:.2f}–{lo+(i+1)*width:.2f}' for i in range(bins)]
    prueba=None
    if hipotesis_media is not None:
        if n<2:
            prueba={'estado':'INSUFICIENTE','explicacion':'Se requieren al menos dos ventas para la prueba t.'}
        elif stdev(xs)==0:
            prueba={'estado':'NO_CALCULABLE','explicacion':'Todas las ventas tienen el mismo importe; no se estima una prueba t convencional.'}
        else:
            from scipy.stats import t as distribucion_t
            estadistico=(mu-float(hipotesis_media))/(stdev(xs)/sqrt(n))
            pvalor=float(2*distribucion_t.sf(abs(estadistico),df=n-1))
            rechaza=pvalor<alfa
            prueba={'estado':'CALCULADO','metodo':'t de Student bilateral, una muestra',
                    'hipotesis_nula': f'La media de ventas equivale a {float(hipotesis_media):.2f}.',
                    'estadistico_t':round(estadistico,6),'grados_libertad':n-1,
                    'valor_p':round(pvalor,8),'alfa':alfa,'rechazar_hipotesis_nula':rechaza,
                    'explicacion': ('La muestra ofrece evidencia estadística contra la media propuesta.' if rechaza else
                                    'La muestra no ofrece evidencia suficiente para rechazar la media propuesta.'),
                    'advertencia':'El valor p no es la probabilidad de que la hipótesis nula sea verdadera. Las ventas pueden no ser observaciones independientes.'}
    return {'cantidad':n,'sin_datos':False,'media':round(mu,4),'mediana':round(median(xs),4),
            'varianza_poblacional':round(pvariance(xs),4),'desviacion_poblacional':round(pstdev(xs),4),
            'varianza_muestral':round(variance(xs),4) if n>=2 else None,
            'desviacion_muestral':round(stdev(xs),4) if n>=2 else None,
            'esperanza_empirica':round(mu,4),
            'histograma':{'tipo':'barra','titulo':'Frecuencia por importe de venta','etiquetas':labels,'valores':counts,
                         'eje_x':'Importe de venta (PEN)','eje_y':'Cantidad de ventas'},
            'contraste':prueba,
            'explicacion':'La media describe el ingreso por venta confirmada; la dispersión describe cuánto varían sus importes. La esperanza es empírica, no una predicción.',
            'advertencia':'Ventas confirmadas no son necesariamente pagos cobrados.'}


def tabla_probabilidades(conteos):
    if any(v < 0 for v in conteos.values()):
        raise ValueError('Conteos no negativos requeridos.')
    total=sum(conteos.values())
    return {'tipo':'barra','titulo':'Distribución empírica de eventos','etiquetas':list(conteos),
            'valores':[round(v/total,6) if total else 0 for v in conteos.values()],
            'unidad':'probabilidad','sin_datos':total==0}
