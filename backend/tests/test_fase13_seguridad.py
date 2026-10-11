"""FASE 13: contratos y aislamiento de auditoría."""
from datetime import datetime, timezone
from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from app.core.config import Settings
from app.services import auditoria_consulta_service as svc


def test_jwt_solo_algoritmo_aprobado():
    base = dict(DATABASE_URL='postgresql://u:p@localhost/test', JWT_SECRET_KEY='x'*40, JWT_ALGORITHM='none')
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **base)
    base['JWT_ALGORITHM'] = 'HS256'
    assert Settings(_env_file=None, **base).JWT_ALGORITHM == 'HS256'


def test_auditoria_exige_permiso(monkeypatch):
    from app.services.venta_service import VentaServiceError
    def denegar(*args, **kwargs):
        assert kwargs['permiso'] == 'auditoria.ver'
        raise VentaServiceError('denegado')
    monkeypatch.setattr(svc, '_validar_operador', denegar)
    with pytest.raises(svc.AuditoriaConsultaError) as info:
        svc.consultar_auditoria(object(), usuario_id=2)
    assert info.value.status_code == 403


def test_auditoria_filtra_por_empresa_y_no_expone_payload(monkeypatch):
    monkeypatch.setattr(svc, '_validar_operador', lambda *a, **k: (object(), SimpleNamespace(id=7)))
    class DB:
        def __init__(self): self.consultas=[]
        def scalar(self, q): self.consultas.append(str(q)); return 1
        def scalars(self,q):
            self.consultas.append(str(q))
            return SimpleNamespace(all=lambda: [SimpleNamespace(id=4, usuario_id=3, accion='CREAR',
                entidad='productos', entidad_id=11, descripcion='Registro', origen='API',
                created_at=datetime(2026,1,1,tzinfo=timezone.utc),
                datos_anteriores={'password':'secret'}, datos_nuevos={'token':'secret'})])
    db=DB()
    r=svc.consultar_auditoria(db, usuario_id=3, limite=5)
    assert r['total']==1 and r['items'][0]['id']==4
    assert 'datos_anteriores' not in r['items'][0] and 'datos_nuevos' not in r['items'][0]
    assert all('auditoria.empresa_id' in sql for sql in db.consultas)
    assert all(':empresa_id' in sql or 'empresa_id_1' in sql for sql in db.consultas)


def test_endpoint_auditoria_y_headers(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.dependencies import get_current_active_user
    from app.database.connection import get_db
    from app.api.routes import auditoria
    old=dict(app.dependency_overrides)
    app.dependency_overrides[get_current_active_user]=lambda:SimpleNamespace(id=3)
    app.dependency_overrides[get_db]=lambda:object()
    monkeypatch.setattr(auditoria,'consultar_auditoria',lambda *a,**k:dict(total=0,limite=k['limite'],desplazamiento=k['desplazamiento'],items=[]))
    try:
        with TestClient(app) as client:
            r=client.get('/api/auditoria')
            bad=client.get('/api/auditoria?limite=101')
            dates=client.get('/api/auditoria?desde=2026-01-01T00:00:00')
        assert r.status_code==200 and r.json()['items']==[]
        assert r.headers['x-content-type-options']=='nosniff'
        assert r.headers['cache-control']=='no-store'
        assert bad.status_code==422 and dates.status_code==422
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(old)
