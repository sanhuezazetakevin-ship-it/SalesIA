"""
SalesIA Enterprise
FASE 08-D.11

API REST empresarial de ventas.
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database.connection import get_db
from app.models.usuario import Usuario

from app.schemas.ventas import (
    EstadoPagoVenta,
    EstadoVenta,
    VentaDesdePedidoCreate,
    VentaResponse,
    VentaConDetallesResponse,
    VentaListadoResponse,
)

from app.services.venta_service import (
    VentaServiceError,
    crear_venta_desde_pedido,
    obtener_venta,
    listar_ventas,
)


router = APIRouter(
    prefix="/api/ventas",
    tags=["Ventas"],
)


def _venta_con_detalles(
    resultado: dict,
) -> VentaConDetallesResponse:

    venta = VentaResponse.model_validate(
        resultado["venta"]
    )

    return VentaConDetallesResponse(
        **venta.model_dump(),
        detalles=resultado["detalles"],
    )


def _rechazar_operacion_venta(
    exc: VentaServiceError,
):
    mensaje = str(exc)
    normalizado = mensaje.lower()

    if (
        "autorizacion" in normalizado
        or "autorización" in normalizado
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "No tiene autorización para realizar "
                "esta operación de ventas."
            ),
        ) from exc

    if "no existe en esta empresa" in normalizado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La venta solicitada no está disponible.",
        ) from exc

    conflictos = (
        "solo un pedido confirmado",
        "ya fue convertido",
        "importes del pedido son inconsistentes",
        "no contiene detalles",
    )

    if any(
        texto in normalizado
        for texto in conflictos
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=mensaje,
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="No fue posible completar la operación de ventas.",
    ) from exc


@router.post(
    "/desde-pedido/{pedido_id}",
    response_model=VentaConDetallesResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_venta_desde_pedido_http(
    pedido_id: int,
    datos: VentaDesdePedidoCreate,
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        resultado = crear_venta_desde_pedido(
            db,
            usuario_id=usuario_actual.id,
            pedido_id=pedido_id,
            observaciones=datos.observaciones,
        )

        return _venta_con_detalles(resultado)

    except VentaServiceError as exc:
        _rechazar_operacion_venta(exc)


@router.get(
    "",
    response_model=VentaListadoResponse,
)
def listar_ventas_http(
    pagina: int = Query(default=1, ge=1),
    limite: int = Query(default=20, ge=1, le=100),
    estado: EstadoVenta | None = Query(default=None),
    estado_pago: EstadoPagoVenta | None = Query(default=None),
    cliente_id: int | None = Query(default=None, gt=0),
    busqueda: str | None = Query(
        default=None,
        max_length=40,
    ),
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return listar_ventas(
            db,
            usuario_id=usuario_actual.id,
            pagina=pagina,
            limite=limite,
            estado=estado,
            estado_pago=estado_pago,
            cliente_id=cliente_id,
            busqueda=busqueda,
        )

    except VentaServiceError as exc:
        _rechazar_operacion_venta(exc)


@router.get(
    "/{venta_id}",
    response_model=VentaConDetallesResponse,
)
def obtener_venta_http(
    venta_id: int,
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        resultado = obtener_venta(
            db,
            usuario_id=usuario_actual.id,
            venta_id=venta_id,
        )

        return _venta_con_detalles(resultado)

    except VentaServiceError as exc:
        _rechazar_operacion_venta(exc)