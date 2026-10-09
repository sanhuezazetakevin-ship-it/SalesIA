"""FASE 09-D.1: pruebas exclusivamente en PostgreSQL Testing con rollback."""
import pytest
from sqlalchemy import select, func
from app.models.proveedor import Proveedor
from app.models.auditoria import Auditoria
from tests.test_pedido_service import preparar_empresa
from app.services.proveedor_service import (
    ProveedorServiceError, crear_proveedor, obtener_proveedor,
    listar_proveedores, actualizar_proveedor, desactivar_proveedor,
)

PERMISOS = ('proveedores.ver', 'proveedores.crear', 'proveedores.editar')


def escenario(db, permisos=PERMISOS):
    return preparar_empresa(db, permisos=permisos, con_impuesto=False)


def test_crear_y_auditar_proveedor(db_testing):
    e = escenario(db_testing)
    p = crear_proveedor(db_testing, usuario_id=e['usuario_id'], razon_social='Proveedor Uno',
                       tipo_documento='RUC', numero_documento='20999999991')
    assert p.id and p.empresa_id == e['empresa_id'] and p.activo
    assert db_testing.scalar(select(func.count()).select_from(Auditoria).where(
        Auditoria.empresa_id == e['empresa_id'], Auditoria.entidad == 'proveedores')) == 1


def test_duplicado_rechazado(db_testing):
    e = escenario(db_testing)
    kwargs = dict(usuario_id=e['usuario_id'], razon_social='Uno', tipo_documento='RUC', numero_documento='20999999992')
    crear_proveedor(db_testing, **kwargs)
    with pytest.raises(ProveedorServiceError, match='ya está registrado'):
        crear_proveedor(db_testing, **kwargs)
    assert db_testing.scalar(select(func.count()).select_from(Proveedor).where(Proveedor.empresa_id == e['empresa_id'])) == 1


def test_listar_buscar_y_obtener(db_testing):
    e = escenario(db_testing)
    p = crear_proveedor(db_testing, usuario_id=e['usuario_id'], razon_social='Distribuidora Atlas')
    listado = listar_proveedores(db_testing, usuario_id=e['usuario_id'], busqueda='Atlas')
    assert listado['total'] == 1 and listado['items'][0].id == p.id
    assert obtener_proveedor(db_testing, usuario_id=e['usuario_id'], proveedor_id=p.id).id == p.id


def test_actualizar_y_desactivar(db_testing):
    e = escenario(db_testing)
    p = crear_proveedor(db_testing, usuario_id=e['usuario_id'], razon_social='Inicial')
    actualizar_proveedor(db_testing, usuario_id=e['usuario_id'], proveedor_id=p.id, razon_social='Modificado')
    assert db_testing.get(Proveedor, p.id).razon_social == 'Modificado'
    desactivar_proveedor(db_testing, usuario_id=e['usuario_id'], proveedor_id=p.id)
    assert listar_proveedores(db_testing, usuario_id=e['usuario_id'], activo=False)['total'] == 1


def test_sin_permiso_no_crea(db_testing):
    e = escenario(db_testing, permisos=('proveedores.ver',))
    with pytest.raises(ProveedorServiceError, match='autorización'):
        crear_proveedor(db_testing, usuario_id=e['usuario_id'], razon_social='Bloqueado')


def test_multiempresa_no_accede(db_testing):
    a = escenario(db_testing)
    b = escenario(db_testing)
    proveedor = crear_proveedor(db_testing, usuario_id=b['usuario_id'], razon_social='Solo B')
    with pytest.raises(ProveedorServiceError, match='no encontrado'):
        obtener_proveedor(db_testing, usuario_id=a['usuario_id'], proveedor_id=proveedor.id)
    assert listar_proveedores(db_testing, usuario_id=a['usuario_id'])['total'] == 0
