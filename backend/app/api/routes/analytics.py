"""Endpoint read-only MVP-01-B; JWT real, RBAC ventas.ver y aislamiento por empresa."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_active_user
from app.database.connection import get_db
from app.models.usuario import Usuario
from app.schemas.analytics_resumen import AnalyticsResumenResponse
from app.services.analytics_resumen_service import obtener_resumen, AnalyticsResumenError

router = APIRouter(prefix='/api/analytics', tags=['Analytics'])

@router.get('/resumen', response_model=AnalyticsResumenResponse)
def resumen_analytics(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    usuario: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        return obtener_resumen(db, usuario_id=usuario.id, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)
    except AnalyticsResumenError as exc:
        mensaje = str(exc)
        raise HTTPException(status_code=403 if 'No autorizado' in mensaje else 422, detail=mensaje) from exc
