"""FASE 14.5: JWT y autorización sin deshabilitar validación del token.
Estas pruebas simulan solamente la sesión consultada, no sustituyen el test con PG real.
"""
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from app.api.dependencies import get_current_user, get_current_active_user
from app.core.security import create_access_token, create_refresh_token, decode_token, TokenInvalidoError
from app.services import session_service
from app.services.session_service import SesionInvalidaError

class _Resultado:
    def __init__(self, value): self.value=value
    def scalar_one_or_none(self): return self.value

class _DB:
    def __init__(self, sesion): self.sesion=sesion; self.consultas=[]
    def execute(self, stmt):
        self.consultas.append(str(stmt))
        return _Resultado(self.sesion)

def _token():
    return create_access_token(usuario_id=12,empresa_id=7,sesion_id=9)

def test_jwt_valido_no_omite_validacion_sesion(monkeypatch):
    token=_token()
    db=_DB(SimpleNamespace(id=9,usuario_id=12,empresa_id=7,revocada=False))
    usuario=SimpleNamespace(id=12,empresa_id=7,activo=True)
    monkeypatch.setattr(session_service,'_verificar_usuario_empresa',lambda d,u,e: usuario)
    assert session_service.validar_sesion(db,access_token=token) is usuario
    assert db.consultas and 'sesiones' in db.consultas[0]
    assert 'empresa_id' in db.consultas[0]

def test_sesion_revocada_o_inexistente_no_accede():
    with pytest.raises(SesionInvalidaError):
        session_service.validar_sesion(_DB(None),access_token=_token())

def test_refresh_no_sirve_como_access():
    refresh=create_refresh_token(usuario_id=12,empresa_id=7,sesion_id=9)
    with pytest.raises(SesionInvalidaError):
        session_service.validar_sesion(_DB(None),access_token=refresh)

def test_token_empresa_firma_no_modificable():
    token=_token(); a,b,c=token.split('.')
    altered='.'.join((a,b,('x' if c[0]!='x' else 'y')+c[1:]))
    with pytest.raises(TokenInvalidoError):decode_token(altered,expected_type='access')

def test_dependency_rechaza_token_ausente():
    with pytest.raises(HTTPException) as ex:get_current_user(credentials=None,db=_DB(None))
    assert ex.value.status_code==401

def test_dependency_rechaza_usuario_inactivo():
    with pytest.raises(HTTPException) as ex:get_current_active_user(SimpleNamespace(activo=False))
    assert ex.value.status_code==403
