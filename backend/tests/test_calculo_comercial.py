
"""Pruebas puras del motor comercial SalesIA."""

from decimal import Decimal

import pytest

from app.services.calculo_comercial import (
    CalculoComercialError,
    calcular_linea,
    calcular_resumen,
)


def test_precio_con_igv_incluido():
    resultado = calcular_linea(
        producto_id=1,
        cantidad="1",
        precio_unitario="118.00",
        tasa_impuesto="18",
    )
    assert resultado.subtotal == Decimal("100.00")
    assert resultado.impuesto == Decimal("18.00")
    assert resultado.total == Decimal("118.00")


def test_descuento_aplicado_antes_del_desglose():
    resultado = calcular_linea(
        producto_id=1,
        cantidad="1",
        precio_unitario="118.00",
        descuento="11.80",
        tasa_impuesto="18",
    )
    assert resultado.subtotal == Decimal("90.00")
    assert resultado.impuesto == Decimal("16.20")
    assert resultado.total == Decimal("106.20")


def test_cantidad_con_tres_decimales():
    resultado = calcular_linea(
        producto_id=1,
        cantidad="1.500",
        precio_unitario="20.00",
        tasa_impuesto="0",
    )
    assert resultado.total == Decimal("30.00")


def test_impuesto_configurable():
    resultado = calcular_linea(
        producto_id=1,
        cantidad="1",
        precio_unitario="110.00",
        tasa_impuesto="10",
    )
    assert resultado.subtotal == Decimal("100.00")
    assert resultado.impuesto == Decimal("10.00")


def test_resumen_de_dos_productos():
    a = calcular_linea(
        producto_id=1,
        cantidad="1",
        precio_unitario="118.00",
    )
    b = calcular_linea(
        producto_id=2,
        cantidad="2",
        precio_unitario="59.00",
    )
    resumen = calcular_resumen([a, b])

    assert resumen.subtotal == Decimal("200.00")
    assert resumen.impuesto_total == Decimal("36.00")
    assert resumen.total == Decimal("236.00")


@pytest.mark.parametrize(
    "cambios",
    [
        {"cantidad": "0"},
        {"cantidad": "-1"},
        {"cantidad": "1.0001"},
        {"precio_unitario": "-1"},
        {"precio_unitario": "NaN"},
        {"precio_unitario": 10.5},
        {"descuento": "200.00"},
        {"tasa_impuesto": "-1"},
        {"tasa_impuesto": "101"},
        {"tasa_impuesto": "18.12345"},
        {"producto_id": 0},
    ],
)
def test_rechazar_datos_invalidos(cambios):
    datos = {
        "producto_id": 1,
        "cantidad": "1",
        "precio_unitario": "118.00",
        "tasa_impuesto": "18",
    }
    datos.update(cambios)

    with pytest.raises(CalculoComercialError):
        calcular_linea(**datos)


def test_rechazar_resumen_vacio():
    with pytest.raises(CalculoComercialError):
        calcular_resumen([])


def test_rechazar_producto_duplicado():
    linea = calcular_linea(
        producto_id=1,
        cantidad="1",
        precio_unitario="118.00",
    )

    with pytest.raises(CalculoComercialError):
        calcular_resumen([linea, linea])
