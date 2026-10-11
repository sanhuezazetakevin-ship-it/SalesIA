"""API FASE 12: generación, historial, descarga y vista imprimible."""
from datetime import date
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_active_user
from app.database.connection import get_db
from app.models.usuario import Usuario
from app.services import reportes_service as svc
from app.services.reportes_pdf_directo import generar_pdf_directo

router = APIRouter(prefix='/api/reportes', tags=['Reportes'])
Tipo = Literal['VENTAS','ESTADISTICO','INVENTARIO','CLIENTES','RENDIMIENTO']
Formato = Literal['CSV','XLSX','PDF']

def ejecutar(fn, *args, **kwargs):
    try: return fn(*args, **kwargs)
    except svc.ReporteError as exc: raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

@router.get('/previsualizar')
def previsualizar(tipo: Tipo, fecha_inicio: date, fecha_fin: date,
                  limite: int = Query(100, ge=1, le=100), usuario: Usuario=Depends(get_current_active_user),
                  db: Session=Depends(get_db)):
    return ejecutar(svc.previsualizar, db, usuario.id, tipo, fecha_inicio, fecha_fin, limite)

@router.post('/generar', status_code=201)
def generar(tipo: Tipo, formato: Formato, fecha_inicio: date, fecha_fin: date,
            usuario: Usuario=Depends(get_current_active_user), db: Session=Depends(get_db)):
    r = ejecutar(svc.generar, db, usuario.id, tipo, formato, fecha_inicio, fecha_fin)
    return {'id':r.id,'tipo':r.tipo_reporte,'formato':r.formato,'estado':r.estado,'tamano_bytes':r.tamano_bytes}

@router.get('/imprimible')
def imprimible(tipo: Tipo, fecha_inicio: date, fecha_fin: date,
               usuario: Usuario=Depends(get_current_active_user), db: Session=Depends(get_db)):
    data = ejecutar(svc.imprimible, db, usuario.id, tipo, fecha_inicio, fecha_fin)
    return Response(content=data, media_type='text/html', headers={'Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; sandbox allow-scripts"})

@router.get('')
def listar(limite: int=Query(50, ge=1, le=100), usuario: Usuario=Depends(get_current_active_user),
          db: Session=Depends(get_db)):
    items = ejecutar(svc.listar, db, usuario.id, limite)
    return {'items':[{'id':r.id,'nombre':r.nombre,'tipo':r.tipo_reporte,'formato':r.formato,
              'estado':r.estado,'tamano_bytes':r.tamano_bytes,'created_at':r.created_at} for r in items]}



@router.get('/pdf-directo')
def pdf_directo(tipo: Tipo, fecha_inicio: date, fecha_fin: date,
               usuario: Usuario=Depends(get_current_active_user), db: Session=Depends(get_db)):
    """Genera un informe visual PDF sin escribir archivos persistentes en Railway."""
    data = ejecutar(generar_pdf_directo, db, usuario.id, tipo, fecha_inicio, fecha_fin)
    return Response(content=data, media_type='application/pdf', headers={
        'Content-Disposition': 'attachment; filename="SalesIA_reporte_visual.pdf"',
        'Cache-Control': 'private, no-store',
        'X-Content-Type-Options': 'nosniff',
    })


@router.get('/{reporte_id}')
def detalle(reporte_id:int, usuario: Usuario=Depends(get_current_active_user),db:Session=Depends(get_db)):
    r = ejecutar(svc.consultar, db, usuario.id, reporte_id, 'reportes.ver')
    return {'id':r.id,'nombre':r.nombre,'tipo':r.tipo_reporte,'formato':r.formato,
            'estado':r.estado,'parametros':r.parametros,'tamano_bytes':r.tamano_bytes,'created_at':r.created_at}

@router.get('/{reporte_id}/descargar')
def descargar(reporte_id:int,usuario:Usuario=Depends(get_current_active_user),db:Session=Depends(get_db)):
    r, path = ejecutar(svc.descargar, db, usuario.id, reporte_id)
    media = {'CSV':'text/csv; charset=utf-8','XLSX':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','PDF':'application/pdf'}[r.formato]
    return FileResponse(path, media_type=media, filename=f'SalesIA_reporte_{r.id}.{r.formato.lower()}',
                        headers={'X-Content-Type-Options':'nosniff','Cache-Control':'private, no-store'})
