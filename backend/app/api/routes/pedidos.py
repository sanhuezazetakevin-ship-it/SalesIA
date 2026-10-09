"""
SalesIA Enterprise
FASE 08-C.10

API REST empresarial de pedidos.

Seguridad:
- JWT + sesion persistida.
- RBAC validado dentro de pedido_service.
- Aislamiento multiempresa.
- El frontend nunca envia empresa_id ni usuario_id.
- Confirmar reserva stock, pero no descuenta stock fisico.
- Cancelar libera reservas cuando corresponde.
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

from app.schemas.pedidos import (
    EstadoPedido,
    PedidoCreate,
    PedidoResponse,
    PedidoConDetallesResponse,
    PedidoListadoResponse,
)

from app.services.pedido_service import (
    PedidoServiceError,
    crear_pedido,
    obtener_pedido,
    listar_pedidos,
    confirmar_pedido,
    cancelar_pedido,
)


router = APIRouter(
    prefix="/api/pedidos",
    tags=["Pedidos"],
)


def _pedido_con_detalles(resultado: dict) -> PedidoConDetallesResponse:
    """
    Convierte el resultado interno del servicio:

    {
        "pedido": Pedido,
        "detalles": list[PedidoDetalle]
    }

    al contrato HTTP público.
    """

    pedido = PedidoResponse.model_validate(
        resultado["pedido"]
    )

    return PedidoConDetallesResponse(
        **pedido.model_dump(),
        detalles=resultado["detalles"],
    )


def _rechazar_operacion_pedido(
    exc: PedidoServiceError,
):
    """
    Traduce errores controlados del dominio a HTTP.

    No revela recursos pertenecientes a otras empresas.
    """

    mensaje = str(exc)
    mensaje_normalizado = mensaje.lower()

    # Seguridad / RBAC
    if (
        "autorizacion" in mensaje_normalizado
        or "autorización" in mensaje_normalizado
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "No tiene autorización para realizar "
                "esta operación de pedidos."
            ),
        ) from exc

    # No revelar si el identificador realmente existe
    # en otra empresa.
    if "no existe en esta empresa" in mensaje_normalizado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El pedido solicitado no está disponible.",
        ) from exc

    # Conflictos de estado o negocio.
    conflictos = (
        "stock insuficiente",
        "solo se pueden confirmar",
        "ya se encuentra cancelado",
        "no puede cancelarse",
        "estado actual",
        "configuracion tributaria",
        "configuración tributaria",
        "debe actualizarse",
        "importes del pedido son inconsistentes",
        "reservas activas inconsistentes",
        "no fue posible bloquear",
    )

    if any(
        texto in mensaje_normalizado
        for texto in conflictos
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=mensaje,
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="No fue posible completar la operación de pedidos.",
    ) from exc


@router.post(
    "",
    response_model=PedidoConDetallesResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_pedido_http(
    datos: PedidoCreate,
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        resultado = crear_pedido(
            db,
            usuario_id=usuario_actual.id,
            datos=datos,
        )

        return _pedido_con_detalles(resultado)

    except PedidoServiceError as exc:
        _rechazar_operacion_pedido(exc)


@router.get(
    "",
    response_model=PedidoListadoResponse,
)
def listar_pedidos_http(
    pagina: int = Query(
        default=1,
        ge=1,
    ),
    limite: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    estado: EstadoPedido | None = Query(
        default=None,
    ),
    cliente_id: int | None = Query(
        default=None,
        gt=0,
    ),
    busqueda: str | None = Query(
        default=None,
        max_length=40,
    ),
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return listar_pedidos(
            db,
            usuario_id=usuario_actual.id,
            pagina=pagina,
            limite=limite,
            estado=estado,
            cliente_id=cliente_id,
            busqueda=busqueda,
        )

    except PedidoServiceError as exc:
        _rechazar_operacion_pedido(exc)


@router.get(
    "/{pedido_id}",
    response_model=PedidoConDetallesResponse,
)
def obtener_pedido_http(
    pedido_id: int,
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        resultado = obtener_pedido(
            db,
            usuario_id=usuario_actual.id,
            pedido_id=pedido_id,
        )

        return _pedido_con_detalles(resultado)

    except PedidoServiceError as exc:
        _rechazar_operacion_pedido(exc)


@router.post(
    "/{pedido_id}/confirmar",
    response_model=PedidoResponse,
)
def confirmar_pedido_http(
    pedido_id: int,
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return confirmar_pedido(
            db,
            usuario_id=usuario_actual.id,
            pedido_id=pedido_id,
        )

    except PedidoServiceError as exc:
        _rechazar_operacion_pedido(exc)


@router.post(
    "/{pedido_id}/cancelar",
    response_model=PedidoResponse,
)
def cancelar_pedido_http(
    pedido_id: int,
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return cancelar_pedido(
            db,
            usuario_id=usuario_actual.id,
            pedido_id=pedido_id,
        )

    except PedidoServiceError as exc:
        _rechazar_operacion_pedido(exc)