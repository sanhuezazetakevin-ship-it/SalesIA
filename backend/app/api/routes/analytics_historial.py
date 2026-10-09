"""MVP-01-F.3: API de historial. No acepta resultados calculados por clientes."""
from datetime import datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user
from app.database.connection import get_db
from app.models.usuario import Usuario
from app.services.venta_service import _validar_operador, VentaServiceError
from app.services.analytics_resumen_service import obtener_resumen, AnalyticsResumenError
from app.services.analytics_probabilidades_service import obtener_probabilidades
from app.services.analytics_historial_service import (
    AnalyticsHistorialError, guardar_estadistico, guardar_probabilidad,
    listar_historial, obtener_historial,
)
from app.schemas.analytics_historial import (
    CrearEstadisticoRequest, CrearProbabilidadRequest,
    AnalisisGuardado, HistorialListado,
)

router = APIRouter(prefix='/api/analytics/historial', tags=['Analytics - Historial'])


def _autorizacion_escritura(db: Session, usuario_id: int) -> None:
    # El servicio interno preserva ventas.ver; el límite HTTP exige también
    # permiso específico de ejecución, presente en el catálogo RBAC.
    try:
        _validar_operador(db, usuario_id=usuario_id, permiso='analitica.ejecutar')
    except VentaServiceError as exc:
        raise HTTPException(status_code=403, detail='No autorizado para ejecutar análisis.') from exc


def _error(exc: Exception) -> HTTPException:
    mensaje = str(exc)
    codigo = 403 if 'No autorizado' in mensaje else 422
    return HTTPException(status_code=codigo, detail=mensaje)


def _formatear(registro, tipo: str) -> dict:
    return {
        'id': registro.id,
        'tipo': tipo,
        'empresa_id': registro.empresa_id,
        'estado': registro.estado,
        'resultados': registro.resultados,
        'created_at': registro.created_at.isoformat() if registro.created_at else None,
    }


@router.post('/estadisticos', response_model=AnalisisGuardado, status_code=status.HTTP_201_CREATED)
def crear_estadistico(
    entrada: CrearEstadisticoRequest,
    usuario: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _autorizacion_escritura(db, usuario.id)
    try:
        # Servidor: calcula sobre empresa/periodo autenticados, no acepta resultados ajenos.
        datos = obtener_resumen(db, usuario_id=usuario.id,
                                fecha_inicio=entrada.fecha_inicio, fecha_fin=entrada.fecha_fin)
        registro = guardar_estadistico(db, usuario_id=usuario.id, nombre=entrada.nombre,
                                       fecha_inicio=entrada.fecha_inicio, fecha_fin=entrada.fecha_fin,
                                       resultados=datos)
        db.commit()
        db.refresh(registro)
        return _formatear(registro, 'estadistico')
    except (AnalyticsHistorialError, AnalyticsResumenError) as exc:
        db.rollback()
        raise _error(exc) from exc
    except Exception:
        db.rollback()
        raise


@router.post('/probabilidades', response_model=AnalisisGuardado, status_code=status.HTTP_201_CREATED)
def crear_probabilidad(
    entrada: CrearProbabilidadRequest,
    usuario: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _autorizacion_escritura(db, usuario.id)
    try:
        datos = obtener_probabilidades(db, usuario_id=usuario.id,
                                       fecha_inicio=entrada.fecha_inicio, fecha_fin=entrada.fecha_fin,
                                       umbral_importe=entrada.umbral_importe)
        registro = guardar_probabilidad(db, usuario_id=usuario.id,
                                        fecha_inicio=entrada.fecha_inicio, fecha_fin=entrada.fecha_fin,
                                        umbral_importe=entrada.umbral_importe, resultados=datos)
        db.commit()
        db.refresh(registro)
        return _formatear(registro, 'probabilidad')
    except (AnalyticsHistorialError, AnalyticsResumenError) as exc:
        db.rollback()
        raise _error(exc) from exc
    except Exception:
        db.rollback()
        raise


@router.get('', response_model=HistorialListado)
def consultar_historial(
    tipo: Literal['estadistico', 'probabilidad'] = Query('estadistico'),
    limite: int = Query(20, ge=1, le=100),
    usuario: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        items = listar_historial(db, usuario_id=usuario.id, tipo=tipo, limite=limite)
        return {'tipo': tipo, 'limite': limite, 'items': [_formatear(x, tipo) for x in items]}
    except AnalyticsHistorialError as exc:
        raise _error(exc) from exc


@router.get('/{tipo}/{analisis_id}', response_model=AnalisisGuardado)
def consultar_analisis(
    tipo: Literal['estadistico', 'probabilidad'],
    analisis_id: int,
    usuario: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        registro = obtener_historial(db, usuario_id=usuario.id,
                                     tipo=tipo, analisis_id=analisis_id)
    except AnalyticsHistorialError as exc:
        raise _error(exc) from exc
    if registro is None:
        raise HTTPException(status_code=404, detail='Análisis no encontrado.')
    return _formatear(registro, tipo)
