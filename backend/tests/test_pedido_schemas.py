
"""
FASE 08-C.1 — Validaciones de contratos de pedidos.

No necesita PostgreSQL.
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.pedidos import PedidoCreate


def pedido_valido():
    return {
        "cliente_id": 1,
        "detalles": [
            {
                "producto_id": 10,
                "cantidad": "2.500",
                "descuento": "5.00",
            }
        ],
        "observaciones": "Pedido empresarial",
    }


def test_pedido_valido():
    pedido = PedidoCreate.model_validate(pedido_valido())

    assert pedido.cliente_id == 1
    assert pedido.detalles[0].cantidad == Decimal("2.500")
    assert pedido.detalles[0].descuento == Decimal("5.00")


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("empresa_id", 999),
        ("usuario_id", 999),
        ("subtotal", "10.00"),
        ("impuesto_total", "1.80"),
        ("total", "11.80"),
        ("estado", "CONFIRMADO"),
    ],
)
def test_prohibir_campos_controlados_por_backend(campo, valor):
    datos = pedido_valido()
    datos[campo] = valor

    with pytest.raises(ValidationError):
        PedidoCreate.model_validate(datos)


@pytest.mark.parametrize(
    "cantidad",
    ["0", "-1", "1.0001", "NaN"],
)
def test_rechazar_cantidades_invalidas(cantidad):
    datos = pedido_valido()
    datos["detalles"][0]["cantidad"] = cantidad

    with pytest.raises(ValidationError):
        PedidoCreate.model_validate(datos)


def test_rechazar_detalles_vacios():
    datos = pedido_valido()
    datos["detalles"] = []

    with pytest.raises(ValidationError):
        PedidoCreate.model_validate(datos)


def test_rechazar_productos_repetidos():
    datos = pedido_valido()
    datos["detalles"].append({
        "producto_id": 10,
        "cantidad": "1.000",
    })

    with pytest.raises(ValidationError):
        PedidoCreate.model_validate(datos)


def test_rechazar_descuento_negativo():
    datos = pedido_valido()
    datos["detalles"][0]["descuento"] = "-0.01"

    with pytest.raises(ValidationError):
        PedidoCreate.model_validate(datos)


def test_rechazar_cliente_invalido():
    datos = pedido_valido()
    datos["cliente_id"] = 0

    with pytest.raises(ValidationError):
        PedidoCreate.model_validate(datos)


def test_descuento_predeterminado():
    pedido = PedidoCreate(
        cliente_id=1,
        detalles=[
            {
                "producto_id": 10,
                "cantidad": "1",
            }
        ],
    )

    assert pedido.detalles[0].descuento == Decimal("0.00")
