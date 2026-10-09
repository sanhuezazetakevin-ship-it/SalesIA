"""SalesIA 09-F.4-B: JWT firmado, sesión SQL real y RBAC sobre TESTING.

NO sustituye get_current_user ni validar_sesion: solo get_db por db_testing.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.database.connection import get_db
from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.models.sesion import Sesion
from app.models.usuario import Usuario
from app.models.empresa import Empresa
from app.models.orden_compra import OrdenCompra
from app.services.orden_compra_service import crear_orden_compra
from tests.test_orden_compra_service import preparar

ORDENES = '/api/compras/ordenes'
PAGOS = '/api/compras/pagos'
RECEPCIONES = '/api/compras/recepciones'


@pytest.fixture
def cliente_seguro(db_testing):
    anteriores = app.dependency_overrides.copy()

    def solo_testing():
        yield db_testing

    # No desactivar la verificación de JWT, sesiones ni usuario activo.
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = solo_testing
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(anteriores)


def token_con_sesion(db, empresa_usuario, *, revocada=False, vencida=False, empresa_token=None):
    usuario_id = empresa_usuario['usuario_id']
    empresa_id = empresa_usuario['empresa_id']
    sesion = Sesion(
        usuario_id=usuario_id,
        empresa_id=empresa_id,
        token_hash=uuid4().hex + uuid4().hex,
        fecha_expiracion=datetime.now(timezone.utc) + (timedelta(minutes=-1) if vencida else timedelta(days=1)),
        revocada=revocada,
    )
    db.add(sesion)
    db.commit()
    token = create_access_token(usuario_id=usuario_id, empresa_id=empresa_token or empresa_id, sesion_id=sesion.id)
    return token, sesion


def headers(token):
    return {'Authorization': 'Bearer ' + token}


def escenario(db, permisos=None):
    if permisos is None:
        return preparar(db)
    return preparar(db, permisos=permisos)


def nueva_orden(db, e, proveedor, producto):
    return crear_orden_compra(db, usuario_id=e['usuario_id'], proveedor_id=proveedor.id,
        detalles=[{'producto_id': producto.id, 'cantidad': '2.000', 'precio_unitario': '30.00'}])


def test_jwt_valido_y_sesion_real(cliente_seguro, db_testing):
    e, _, _ = escenario(db_testing)
    token, _ = token_con_sesion(db_testing, e)
    r = cliente_seguro.get(ORDENES, headers=headers(token))
    assert r.status_code == 200, r.text


def test_sin_token_token_manipulado_y_token_refresh(cliente_seguro, db_testing):
    e, _, _ = escenario(db_testing)
    token, sesion = token_con_sesion(db_testing, e)
    assert cliente_seguro.get(ORDENES).status_code == 401
    partes = token.split('.')
    partes[2] = ('A' if partes[2][0] != 'A' else 'B') + partes[2][1:]
    assert cliente_seguro.get(ORDENES, headers=headers('.'.join(partes))).status_code == 401
    refresh = create_refresh_token(usuario_id=e['usuario_id'], empresa_id=e['empresa_id'], sesion_id=sesion.id)
    assert cliente_seguro.get(ORDENES, headers=headers(refresh)).status_code == 401


def test_jwt_expirado(cliente_seguro, db_testing):
    e, _, _ = escenario(db_testing)
    token, _ = token_con_sesion(db_testing, e)
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    payload['exp'] = datetime.now(timezone.utc) - timedelta(seconds=10)
    expirado = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    assert cliente_seguro.get(ORDENES, headers=headers(expirado)).status_code == 401


def test_sesion_revocada(cliente_seguro, db_testing):
    e, _, _ = escenario(db_testing)
    token, sesion = token_con_sesion(db_testing, e)
    assert cliente_seguro.get(ORDENES, headers=headers(token)).status_code == 200
    sesion.revocada = True
    db_testing.commit()
    assert cliente_seguro.get(ORDENES, headers=headers(token)).status_code == 401


def test_sesion_vencida(cliente_seguro, db_testing):
    e, _, _ = escenario(db_testing)
    token, _ = token_con_sesion(db_testing, e, vencida=True)
    assert cliente_seguro.get(ORDENES, headers=headers(token)).status_code == 401


def test_usuario_y_empresa_inactivos(cliente_seguro, db_testing):
    e, _, _ = escenario(db_testing)
    token, _ = token_con_sesion(db_testing, e)
    usuario = db_testing.get(Usuario, e['usuario_id'])
    usuario.activo = False
    db_testing.commit()
    assert cliente_seguro.get(ORDENES, headers=headers(token)).status_code == 401
    usuario.activo = True
    empresa = db_testing.get(Empresa, e['empresa_id'])
    empresa.activo = False
    db_testing.commit()
    assert cliente_seguro.get(ORDENES, headers=headers(token)).status_code == 401


def test_empresa_en_token_no_coincidente(cliente_seguro, db_testing):
    a, _, _ = escenario(db_testing)
    b, _, _ = escenario(db_testing)
    token, _ = token_con_sesion(db_testing, a, empresa_token=b['empresa_id'])
    assert cliente_seguro.get(ORDENES, headers=headers(token)).status_code == 401


def test_rbac_no_permite_confirmar_orden(cliente_seguro, db_testing):
    permisos = ('proveedores.ver', 'proveedores.crear', 'proveedores.editar', 'compras.crear', 'compras.ver')
    e, proveedor, producto = escenario(db_testing, permisos=permisos)
    orden = nueva_orden(db_testing, e, proveedor, producto)
    token, _ = token_con_sesion(db_testing, e)
    r = cliente_seguro.post(f'{ORDENES}/{orden.id}/confirmar', headers=headers(token))
    assert r.status_code == 403, r.text
    assert db_testing.get(OrdenCompra, orden.id).estado == 'BORRADOR'


def test_multiempresa_no_consulta_ni_confirma(cliente_seguro, db_testing):
    a, _, _ = escenario(db_testing)
    b, proveedor_b, producto_b = escenario(db_testing)
    orden_b = nueva_orden(db_testing, b, proveedor_b, producto_b)
    token_a, _ = token_con_sesion(db_testing, a)
    assert cliente_seguro.get(f'{ORDENES}/{orden_b.id}', headers=headers(token_a)).status_code == 404
    assert cliente_seguro.post(f'{ORDENES}/{orden_b.id}/confirmar', headers=headers(token_a)).status_code == 404
    assert db_testing.get(OrdenCompra, orden_b.id).estado == 'BORRADOR'
