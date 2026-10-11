"""FASE 13: consulta de auditoría empresarial, exclusivamente lectura."""
from datetime import datetime
from sqlalchemy import select, func
from app.models.auditoria import Auditoria
from app.services.venta_service import _validar_operador, VentaServiceError

class AuditoriaConsultaError(ValueError):
    def __init__(self, mensaje, status_code=403):
        super().__init__(mensaje)
        self.status_code = status_code


def consultar_auditoria(db, *, usuario_id: int, limite: int = 25, desplazamiento: int = 0,
                       accion: str | None = None, entidad: str | None = None,
                       desde: datetime | None = None, hasta: datetime | None = None):
    try:
        _, empresa = _validar_operador(db, usuario_id=usuario_id, permiso='auditoria.ver')
    except VentaServiceError as exc:
        raise AuditoriaConsultaError('No autorizado para consultar auditoría.') from exc
    filtros = [Auditoria.empresa_id == empresa.id]
    if accion:
        filtros.append(Auditoria.accion == accion)
    if entidad:
        filtros.append(Auditoria.entidad == entidad)
    if desde:
        filtros.append(Auditoria.created_at >= desde)
    if hasta:
        filtros.append(Auditoria.created_at <= hasta)
    total = db.scalar(select(func.count(Auditoria.id)).where(*filtros)) or 0
    registros = db.scalars(select(Auditoria).where(*filtros)
        .order_by(Auditoria.created_at.desc(), Auditoria.id.desc())
        .offset(desplazamiento).limit(limite)).all()
    # Intencionalmente no exponemos datos_anteriores/datos_nuevos: pueden contener datos personales.
    items = [{'id': r.id, 'usuario_id': r.usuario_id, 'accion': r.accion,
              'entidad': r.entidad, 'entidad_id': r.entidad_id,
              'descripcion': r.descripcion, 'origen': r.origen,
              'created_at': r.created_at} for r in registros]
    return {'total': total, 'limite': limite, 'desplazamiento': desplazamiento, 'items': items}
