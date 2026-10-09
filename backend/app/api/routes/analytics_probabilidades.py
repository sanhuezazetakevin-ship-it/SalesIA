"""API protegida para probabilidades y Bayes sobre ventas propias confirmadas."""
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user
from app.database.connection import get_db
from app.models.usuario import Usuario
from app.schemas.analytics_probabilidades import AnalyticsProbabilidadesResponse
from app.services.analytics_probabilidades_service import obtener_probabilidades, AnalyticsResumenError

router = APIRouter(prefix='/api/analytics', tags=['Analytics'])


@router.get('/probabilidades', response_model=AnalyticsProbabilidadesResponse)
def consultar_probabilidades(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    umbral_importe: Decimal = Query(Decimal('100.00'), ge=0, allow_inf_nan=False),
    usuario: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        return obtener_probabilidades(
            db, usuario_id=usuario.id, fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin, umbral_importe=umbral_importe,
        )
    except AnalyticsResumenError as exc:
        mensaje = str(exc)
        raise HTTPException(
            status_code=403 if mensaje.startswith('No autorizado') else 422,
            detail=mensaje,
        ) from exc
