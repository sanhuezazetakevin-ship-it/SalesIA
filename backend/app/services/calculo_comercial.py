
"""
SalesIA Enterprise — FASE 08-B

Motor comercial con precios que incluyen impuestos.

No utiliza conexiones ni modifica PostgreSQL.
El descuento es un importe monetario aplicado al total
bruto de cada linea, no un porcentaje.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENTIMO = Decimal("0.01")
MIL = Decimal("0.001")
CIEN = Decimal("100")
MAX_IMPORTE = Decimal("999999999999.99")


class CalculoComercialError(ValueError):
    """Error controlado de calculo comercial."""


def _decimal(valor, campo: str) -> Decimal:
    if isinstance(valor, bool) or isinstance(valor, float):
        raise CalculoComercialError(
            f"{campo} debe proporcionarse como Decimal, "
            "entero o cadena decimal; no como float."
        )

    try:
        resultado = Decimal(valor)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise CalculoComercialError(
            f"{campo} no es un numero decimal valido."
        ) from exc

    if not resultado.is_finite():
        raise CalculoComercialError(
            f"{campo} debe ser un numero finito."
        )

    return resultado


def _dinero(valor: Decimal, campo: str) -> Decimal:
    if valor < 0 or valor > MAX_IMPORTE:
        raise CalculoComercialError(
            f"{campo} esta fuera del rango permitido."
        )

    if valor != valor.quantize(CENTIMO):
        raise CalculoComercialError(
            f"{campo} admite como maximo dos decimales."
        )

    return valor.quantize(CENTIMO)


def _importe_calculado(valor: Decimal) -> Decimal:
    resultado = valor.quantize(
        CENTIMO,
        rounding=ROUND_HALF_UP,
    )

    if resultado < 0 or resultado > MAX_IMPORTE:
        raise CalculoComercialError(
            "El importe calculado supera el rango permitido."
        )

    return resultado


@dataclass(frozen=True)
class LineaCalculada:
    producto_id: int
    cantidad: Decimal
    precio_unitario: Decimal
    descuento: Decimal
    subtotal: Decimal
    impuesto: Decimal
    total: Decimal
    tasa_impuesto: Decimal


@dataclass(frozen=True)
class ResumenComercial:
    lineas: tuple[LineaCalculada, ...]
    subtotal: Decimal
    impuesto_total: Decimal
    total: Decimal


def calcular_linea(
    *,
    producto_id: int,
    cantidad,
    precio_unitario,
    descuento="0.00",
    tasa_impuesto="18",
) -> LineaCalculada:
    """
    precio_unitario: precio final CON impuestos.
    descuento: importe monetario final de la linea.
    tasa_impuesto: porcentaje, por ejemplo 18 para 18 %.
    """

    if type(producto_id) is not int or producto_id <= 0:
        raise CalculoComercialError(
            "El identificador del producto es invalido."
        )

    cantidad = _decimal(cantidad, "cantidad")

    if (
        cantidad <= 0
        or cantidad > Decimal("99999999999.999")
        or cantidad != cantidad.quantize(MIL)
    ):
        raise CalculoComercialError(
            "La cantidad debe ser positiva y admitir "
            "como maximo tres decimales."
        )

    precio = _dinero(
        _decimal(precio_unitario, "precio_unitario"),
        "precio_unitario",
    )

    descuento = _dinero(
        _decimal(descuento, "descuento"),
        "descuento",
    )

    tasa = _decimal(tasa_impuesto, "tasa_impuesto")

    if tasa < 0 or tasa > 100:
        raise CalculoComercialError(
            "La tasa debe estar entre 0 y 100."
        )

    if tasa != tasa.quantize(Decimal("0.0001")):
        raise CalculoComercialError(
            "La tasa admite como maximo cuatro decimales."
        )

    # Precio unitario ya incluye impuestos.
    bruto = _importe_calculado(cantidad * precio)

    if descuento > bruto:
        raise CalculoComercialError(
            "El descuento no puede superar el importe bruto."
        )

    total = _importe_calculado(bruto - descuento)

    # Extraemos el impuesto; NO lo sumamos al precio comercial.
    base = _importe_calculado(
        total / (Decimal("1") + tasa / CIEN)
    )

    impuesto = _importe_calculado(total - base)

    if base + impuesto != total:
        raise CalculoComercialError(
            "El desglose tributario no es consistente."
        )

    return LineaCalculada(
        producto_id=producto_id,
        cantidad=cantidad,
        precio_unitario=precio,
        descuento=descuento,
        subtotal=base,
        impuesto=impuesto,
        total=total,
        tasa_impuesto=tasa,
    )


def calcular_resumen(lineas) -> ResumenComercial:
    """
    Recibe lineas previamente calculadas.
    Rechaza productos repetidos: cada producto debe
    aparecer una sola vez por pedido o venta.
    """

    lineas = tuple(lineas)

    if not lineas:
        raise CalculoComercialError(
            "Debe existir al menos una linea."
        )

    if not all(
        isinstance(linea, LineaCalculada)
        for linea in lineas
    ):
        raise CalculoComercialError(
            "El resumen contiene lineas invalidas."
        )

    ids = [linea.producto_id for linea in lineas]

    if len(ids) != len(set(ids)):
        raise CalculoComercialError(
            "No se permite repetir un producto."
        )

    subtotal = _importe_calculado(
        sum(
            (linea.subtotal for linea in lineas),
            Decimal("0"),
        )
    )

    impuesto = _importe_calculado(
        sum(
            (linea.impuesto for linea in lineas),
            Decimal("0"),
        )
    )

    total = _importe_calculado(
        sum(
            (linea.total for linea in lineas),
            Decimal("0"),
        )
    )

    if subtotal + impuesto != total:
        raise CalculoComercialError(
            "Los importes del resumen no coinciden."
        )

    return ResumenComercial(
        lineas=lineas,
        subtotal=subtotal,
        impuesto_total=impuesto,
        total=total,
    )
