"""SalesIA Enterprise - FASE 08-E.3. Pruebas de integracion de pagos.

Usa exclusivamente db_testing (PostgreSQL aislado), nunca la BD principal.
"""
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.auditoria import Auditoria
from app.models.pago import Pago
from app.models.venta import Venta
from app.services.pedido_service import confirmar_pedido
from app.services.venta_service import crear_venta_desde_pedido
from app.services.pago_service import (
    PagoServiceError,
    anular_pago,
    registrar_pago,
    resumen_pagos,
)
from tests.test_pedido_service import (
    _escenario_confirmacion,
    _crear_borrador_confirmacion,
)

PERMISOS_BASE = (
    "pedidos.crear", "pedidos.ver", "pedidos.confirmar",
    "ventas.crear", "ventas.ver",
)
PERMISOS_PAGOS = ("pagos.ver", "pagos.registrar", "pagos.anular")


def preparar_venta_pago(db, *, permisos=PERMISOS_BASE + PERMISOS_PAGOS):
    """Mismo escenario de integracion utilizado en las pruebas de ventas."""
    e = _escenario_confirmacion(db, permisos=permisos)
    pedido = _crear_borrador_confirmacion(db, e, cantidad="2.000")
    confirmar_pedido(db, usuario_id=e["usuario_id"], pedido_id=pedido.id)
    venta = crear_venta_desde_pedido(
        db, usuario_id=e["usuario_id"], pedido_id=pedido.id,
    )["venta"]
    return e, venta


def pagar(db, e, venta, monto, medio_pago="EFECTIVO"):
    return registrar_pago(
        db, usuario_id=e["usuario_id"], venta_id=venta.id,
        monto=Decimal(monto), medio_pago=medio_pago,
    )


def resumen(db, e, venta):
    return resumen_pagos(db, usuario_id=e["usuario_id"], venta_id=venta.id)


def test_venta_sin_pagos(db_testing):
    db = db_testing
    e, venta = preparar_venta_pago(db)
    r = resumen(db, e, venta)
    assert r["total_venta"] == venta.total
    assert r["total_pagado"] == Decimal("0.00")
    assert r["saldo_pendiente"] == venta.total
    assert r["estado_pago"] == "PENDIENTE"
    assert r["pagos"] == []


def test_pago_parcial_actualiza_saldo_y_estado(db_testing):
    db = db_testing
    e, venta = preparar_venta_pago(db)
    pago = pagar(db, e, venta, "20.00", medio_pago="YAPE")
    assert pago.estado == "REGISTRADO"
    assert pago.monto == Decimal("20.00")
    assert pago.medio_pago == "YAPE"
    r = resumen(db, e, venta)
    assert r["total_pagado"] == Decimal("20.00")
    assert r["saldo_pendiente"] == venta.total - Decimal("20.00")
    assert r["estado_pago"] == "PARCIAL"
    db.expire_all()
    assert db.get(Venta, venta.id).estado_pago == "PARCIAL"


def test_pago_completo_en_una_operacion(db_testing):
    db = db_testing
    e, venta = preparar_venta_pago(db)
    pagar(db, e, venta, str(venta.total), medio_pago="TRANSFERENCIA")
    r = resumen(db, e, venta)
    assert r["saldo_pendiente"] == Decimal("0.00")
    assert r["total_pagado"] == venta.total
    assert r["estado_pago"] == "PAGADO"
    assert db.get(Venta, venta.id).estado_pago == "PAGADO"


def test_dos_abonos_completan_venta(db_testing):
    db = db_testing
    e, venta = preparar_venta_pago(db)
    pagar(db, e, venta, "10.00")
    saldo = resumen(db, e, venta)["saldo_pendiente"]
    pagar(db, e, venta, str(saldo), medio_pago="PLIN")
    r = resumen(db, e, venta)
    assert len(r["pagos"]) == 2
    assert r["estado_pago"] == "PAGADO"
    assert r["saldo_pendiente"] == 0


def test_rechaza_sobrepago_y_no_inserta_pago(db_testing):
    db = db_testing
    e, venta = preparar_venta_pago(db)
    with pytest.raises(PagoServiceError, match="excede el saldo"):
        pagar(db, e, venta, str(venta.total + Decimal("0.01")))
    r = resumen(db, e, venta)
    assert not r["pagos"]
    assert r["estado_pago"] == "PENDIENTE"


def test_rechaza_segundo_pago_tras_pago_completo(db_testing):
    db = db_testing
    e, venta = preparar_venta_pago(db)
    pagar(db, e, venta, str(venta.total))
    with pytest.raises(PagoServiceError, match="ya esta pagada"):
        pagar(db, e, venta, "0.01")
    assert len(resumen(db, e, venta)["pagos"]) == 1


@pytest.mark.parametrize("monto", [Decimal("0"), Decimal("-1"), Decimal("1.001")])
def test_importe_invalido_rechazado(db_testing, monto):
    db = db_testing
    e, venta = preparar_venta_pago(db)
    with pytest.raises(PagoServiceError):
        registrar_pago(
            db, usuario_id=e["usuario_id"], venta_id=venta.id,
            monto=monto, medio_pago="EFECTIVO",
        )
    assert resumen(db, e, venta)["pagos"] == []


def test_rechaza_medio_pago_invalido(db_testing):
    db = db_testing
    e, venta = preparar_venta_pago(db)
    with pytest.raises(PagoServiceError, match="Medio de pago"):
        pagar(db, e, venta, "5.00", medio_pago="CRIPTOMONEDA")
    assert not resumen(db, e, venta)["pagos"]


def test_anular_pago_recalcula_saldo(db_testing):
    db = db_testing
    e, venta = preparar_venta_pago(db)
    pago = pagar(db, e, venta, "10.00")
    anulado = anular_pago(db, usuario_id=e["usuario_id"], pago_id=pago.id, motivo="Pago duplicado")
    assert anulado.estado == "ANULADO"
    r = resumen(db, e, venta)
    assert r["total_pagado"] == Decimal("0.00")
    assert r["saldo_pendiente"] == venta.total
    assert r["estado_pago"] == "PENDIENTE"
    assert len(r["pagos"]) == 1  # registro historico conservado
    assert db.get(Venta, venta.id).estado_pago == "PENDIENTE"


def test_anular_uno_de_dos_pagos_recalcula_estado(db_testing):
    db = db_testing
    e, venta = preparar_venta_pago(db)
    primero = pagar(db, e, venta, "10.00")
    pagar(db, e, venta, str(venta.total - Decimal("10.00")))
    assert resumen(db, e, venta)["estado_pago"] == "PAGADO"
    anular_pago(db, usuario_id=e["usuario_id"], pago_id=primero.id, motivo="Error administrativo")
    r = resumen(db, e, venta)
    assert r["estado_pago"] == "PARCIAL"
    assert r["saldo_pendiente"] == Decimal("10.00")


def test_no_permite_anular_dos_veces(db_testing):
    db = db_testing
    e, venta = preparar_venta_pago(db)
    pago = pagar(db, e, venta, "5.00")
    anular_pago(db, usuario_id=e["usuario_id"], pago_id=pago.id, motivo="Error detectado")
    with pytest.raises(PagoServiceError, match="ya esta anulado"):
        anular_pago(db, usuario_id=e["usuario_id"], pago_id=pago.id, motivo="Otra anulacion")


def test_auditoria_registro_y_anulacion(db_testing):
    db = db_testing
    e, venta = preparar_venta_pago(db)
    pago = pagar(db, e, venta, "5.00")
    anular_pago(db, usuario_id=e["usuario_id"], pago_id=pago.id, motivo="Correccion de caja")
    entradas = db.scalars(select(Auditoria).where(
        Auditoria.empresa_id == e["empresa_id"],
        Auditoria.entidad == "pagos", Auditoria.entidad_id == pago.id,
    ).order_by(Auditoria.id)).all()
    assert [a.accion for a in entradas] == ["CREAR", "ANULAR"]
    assert all(a.usuario_id == e["usuario_id"] for a in entradas)


def test_sin_permiso_registrar_no_puede_pagar(db_testing):
    db = db_testing
    e, venta = preparar_venta_pago(db, permisos=PERMISOS_BASE + ("pagos.ver",))
    with pytest.raises(PagoServiceError, match="autorizacion"):
        pagar(db, e, venta, "5.00")
    assert resumen(db, e, venta)["pagos"] == []


def test_sin_permiso_anular_no_puede_anular(db_testing):
    db = db_testing
    e, venta = preparar_venta_pago(db, permisos=PERMISOS_BASE + ("pagos.ver", "pagos.registrar"))
    pago = pagar(db, e, venta, "5.00")
    with pytest.raises(PagoServiceError, match="autorizacion"):
        anular_pago(db, usuario_id=e["usuario_id"], pago_id=pago.id, motivo="Prueba negativa")
    assert db.get(Pago, pago.id).estado == "REGISTRADO"


def test_pago_aislado_por_empresa(db_testing):
    db = db_testing
    a, _ = preparar_venta_pago(db)
    b, venta_b = preparar_venta_pago(db)
    pago_b = pagar(db, b, venta_b, "5.00")
    with pytest.raises(PagoServiceError, match="no existe en esta empresa"):
        registrar_pago(db, usuario_id=a["usuario_id"], venta_id=venta_b.id,
                       monto=Decimal("1.00"), medio_pago="EFECTIVO")
    with pytest.raises(PagoServiceError, match="no existe en esta empresa"):
        anular_pago(db, usuario_id=a["usuario_id"], pago_id=pago_b.id, motivo="Sin acceso")
    with pytest.raises(PagoServiceError, match="no existe en esta empresa"):
        resumen_pagos(db, usuario_id=a["usuario_id"], venta_id=venta_b.id)
    assert db.get(Pago, pago_b.id).estado == "REGISTRADO"


# FASE 08-E.6 — Idempotencia de pagos
def test_idempotencia_reintento_no_duplicado(db_testing):
    e, venta = preparar_venta_pago(db_testing)
    datos = dict(usuario_id=e["usuario_id"], venta_id=venta.id, monto=Decimal("10.00"),
                 medio_pago="YAPE", idempotency_key="reintento-seguro-0001")
    primero = registrar_pago(db_testing, **datos)
    segundo = registrar_pago(db_testing, **datos)
    assert segundo.id == primero.id
    assert len(resumen(db_testing, e, venta)["pagos"]) == 1
    auditorias = db_testing.scalars(select(Auditoria).where(
        Auditoria.empresa_id == e["empresa_id"], Auditoria.entidad == "pagos",
        Auditoria.entidad_id == primero.id,
    )).all()
    assert len(auditorias) == 1


def test_idempotencia_payload_distinto_rechazado(db_testing):
    e, venta = preparar_venta_pago(db_testing)
    datos = dict(usuario_id=e["usuario_id"], venta_id=venta.id,
                 medio_pago="PLIN", idempotency_key="payload-distinto-0001")
    registrar_pago(db_testing, monto=Decimal("5.00"), **datos)
    with pytest.raises(PagoServiceError, match="idempotencia"):
        registrar_pago(db_testing, monto=Decimal("7.00"), **datos)
    assert len(resumen(db_testing, e, venta)["pagos"]) == 1


def test_idempotencia_no_reutilizable_tras_anulacion(db_testing):
    e, venta = preparar_venta_pago(db_testing)
    datos = dict(usuario_id=e["usuario_id"], venta_id=venta.id,
                 monto=Decimal("5.00"), medio_pago="EFECTIVO",
                 idempotency_key="anulado-sin-reuso-0001")
    pago = registrar_pago(db_testing, **datos)
    anular_pago(db_testing, usuario_id=e["usuario_id"], pago_id=pago.id,
                motivo="Pago duplicado")
    with pytest.raises(PagoServiceError, match="idempotencia"):
        registrar_pago(db_testing, **datos)
    assert len(resumen(db_testing, e, venta)["pagos"]) == 1


@pytest.mark.parametrize("clave", ["corta", "con espacios invalidos 0001", "ä" * 20])
def test_idempotencia_clave_invalida(db_testing, clave):
    e, venta = preparar_venta_pago(db_testing)
    with pytest.raises(PagoServiceError, match="idempotencia invalida"):
        registrar_pago(db_testing, usuario_id=e["usuario_id"], venta_id=venta.id,
                       monto=Decimal("5.00"), medio_pago="YAPE", idempotency_key=clave)
