"""Pruebas sin escritura de base de datos: seguridad y contratos de administración."""
import pytest
from fastapi import HTTPException
from types import SimpleNamespace
from app.api.routes.plataforma_empresas import exigir_operador, AprobarSolicitud


def test_plataforma_deshabilitada_por_defecto(monkeypatch):
    monkeypatch.delenv('SALESIA_PLATFORM_ADMIN_EMAILS', raising=False)
    with pytest.raises(HTTPException) as err:
        exigir_operador(SimpleNamespace(email='admin@prueba.local'))
    assert err.value.status_code == 403


def test_plataforma_deniega_empresario_no_permitido(monkeypatch):
    monkeypatch.setenv('SALESIA_PLATFORM_ADMIN_EMAILS', 'operador@prueba.local')
    with pytest.raises(HTTPException) as err:
        exigir_operador(SimpleNamespace(email='otro@prueba.local'))
    assert err.value.status_code == 403


def test_plataforma_autoriza_solo_correo_configurado(monkeypatch):
    monkeypatch.setenv('SALESIA_PLATFORM_ADMIN_EMAILS', ' operador@prueba.local ')
    usuario = SimpleNamespace(email='Operador@Prueba.Local')
    assert exigir_operador(usuario) is usuario


def test_password_inicial_no_acepta_contrasena_corta():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        AprobarSolicitud(email_administrador='uno@prueba.local', nombre_administrador='Uno', password_inicial='corta')
