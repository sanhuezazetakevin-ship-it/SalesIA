"""SalesIA FASE 09-D.1 — gestión multiempresa de proveedores."""
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.proveedor import Proveedor
from app.models.auditoria import Auditoria
from app.services.role_service import _obtener_permisos_efectivos


class ProveedorServiceError(Exception):
    """Error controlado de proveedores (no exponer detalles de SQL)."""


def _usuario_empresa(db: Session, usuario_id: int, permiso: str):
    if type(usuario_id) is not int or usuario_id <= 0:
        raise ProveedorServiceError('Usuario inválido.')
    usuario = db.scalar(select(Usuario).where(Usuario.id == usuario_id, Usuario.activo.is_(True)))
    if usuario is None:
        raise ProveedorServiceError('Usuario inactivo o inexistente.')
    empresa = db.scalar(select(Empresa).where(Empresa.id == usuario.empresa_id, Empresa.activo.is_(True)))
    if empresa is None:
        raise ProveedorServiceError('Empresa inactiva o inexistente.')
    if permiso not in _obtener_permisos_efectivos(db, usuario_id=usuario.id, empresa_id=empresa.id):
        raise ProveedorServiceError('No tiene autorización para esta operación.')
    return usuario, empresa


def _normalizar(razon_social: str, tipo_documento: str | None, numero_documento: str | None, email: str | None, telefono: str | None):
    if not isinstance(razon_social, str) or not 1 <= len(razon_social.strip()) <= 200:
        raise ProveedorServiceError('Razón social inválida.')
    if (tipo_documento is None) != (numero_documento is None):
        raise ProveedorServiceError('Tipo y número de documento deben proporcionarse juntos.')
    tipo = tipo_documento.strip().upper() if isinstance(tipo_documento, str) else None
    numero = numero_documento.strip() if isinstance(numero_documento, str) else None
    if tipo is not None and (not 1 <= len(tipo) <= 20 or not 1 <= len(numero) <= 30):
        raise ProveedorServiceError('Documento inválido.')
    correo = email.strip().lower() if isinstance(email, str) else None
    tel = telefono.strip() if isinstance(telefono, str) else None
    if correo is not None and (len(correo) > 254 or '@' not in correo or not correo):
        raise ProveedorServiceError('Correo inválido.')
    if tel is not None and len(tel) > 40:
        raise ProveedorServiceError('Teléfono inválido.')
    return {'razon_social': razon_social.strip(), 'tipo_documento': tipo, 'numero_documento': numero, 'email': correo, 'telefono': tel}


def _auditar(db, usuario, proveedor, accion, anteriores=None):
    db.add(Auditoria(empresa_id=usuario.empresa_id, usuario_id=usuario.id, accion=accion,
        entidad='proveedores', entidad_id=proveedor.id,
        descripcion='Gestión empresarial de proveedor.',
        datos_anteriores=anteriores,
        datos_nuevos={'razon_social': proveedor.razon_social, 'activo': proveedor.activo}, origen='SISTEMA'))


def crear_proveedor(db: Session, *, usuario_id: int, razon_social: str, tipo_documento: str | None = None,
                    numero_documento: str | None = None, email: str | None = None, telefono: str | None = None) -> Proveedor:
    try:
        usuario, empresa = _usuario_empresa(db, usuario_id, 'proveedores.crear')
        datos = _normalizar(razon_social, tipo_documento, numero_documento, email, telefono)
        if datos['tipo_documento'] and db.scalar(select(Proveedor.id).where(
            Proveedor.empresa_id == empresa.id, Proveedor.tipo_documento == datos['tipo_documento'],
            Proveedor.numero_documento == datos['numero_documento'])) is not None:
            raise ProveedorServiceError('El documento ya está registrado en esta empresa.')
        proveedor = Proveedor(empresa_id=empresa.id, activo=True, **datos)
        db.add(proveedor)
        db.flush()
        _auditar(db, usuario, proveedor, 'CREAR')
        db.commit()
        db.refresh(proveedor)
        return proveedor
    except IntegrityError as exc:
        db.rollback()
        raise ProveedorServiceError('Documento de proveedor duplicado o referencia inválida.') from exc
    except Exception:
        db.rollback()
        raise


def obtener_proveedor(db: Session, *, usuario_id: int, proveedor_id: int) -> Proveedor:
    _, empresa = _usuario_empresa(db, usuario_id, 'proveedores.ver')
    if type(proveedor_id) is not int or proveedor_id <= 0:
        raise ProveedorServiceError('Proveedor inválido.')
    proveedor = db.scalar(select(Proveedor).where(Proveedor.id == proveedor_id, Proveedor.empresa_id == empresa.id))
    if proveedor is None:
        raise ProveedorServiceError('Proveedor no encontrado en esta empresa.')
    return proveedor


def listar_proveedores(db: Session, *, usuario_id: int, pagina: int = 1, limite: int = 20,
                       busqueda: str | None = None, activo: bool | None = None) -> dict:
    _, empresa = _usuario_empresa(db, usuario_id, 'proveedores.ver')
    if type(pagina) is not int or pagina < 1 or type(limite) is not int or not 1 <= limite <= 100:
        raise ProveedorServiceError('Paginación inválida.')
    if busqueda is not None and (not isinstance(busqueda, str) or len(busqueda) > 200):
        raise ProveedorServiceError('Búsqueda inválida.')
    if activo is not None and type(activo) is not bool:
        raise ProveedorServiceError('Filtro de estado inválido.')
    filtros = [Proveedor.empresa_id == empresa.id]
    if busqueda and busqueda.strip():
        filtros.append(Proveedor.razon_social.ilike(f'%{busqueda.strip()}%'))
    if activo is not None:
        filtros.append(Proveedor.activo.is_(activo))
    total = db.scalar(select(func.count(Proveedor.id)).where(*filtros)) or 0
    items = db.scalars(select(Proveedor).where(*filtros).order_by(Proveedor.id.desc())
                       .limit(limite).offset((pagina - 1) * limite)).all()
    return {'items': items, 'total': total, 'pagina': pagina, 'limite': limite}


def actualizar_proveedor(db: Session, *, usuario_id: int, proveedor_id: int, **cambios) -> Proveedor:
    try:
        usuario, empresa = _usuario_empresa(db, usuario_id, 'proveedores.editar')
        permitidos = {'razon_social', 'tipo_documento', 'numero_documento', 'email', 'telefono'}
        if not cambios or not set(cambios).issubset(permitidos):
            raise ProveedorServiceError('Campos de actualización inválidos.')
        proveedor = db.scalar(select(Proveedor).where(Proveedor.id == proveedor_id,
             Proveedor.empresa_id == empresa.id).with_for_update())
        if proveedor is None:
            raise ProveedorServiceError('Proveedor no encontrado en esta empresa.')
        if not proveedor.activo:
            raise ProveedorServiceError('No puede editar un proveedor inactivo.')
        anteriores = {'razon_social': proveedor.razon_social, 'activo': proveedor.activo}
        datos = {k: cambios.get(k, getattr(proveedor, k)) for k in permitidos}
        normalizados = _normalizar(**datos)
        for campo, valor in normalizados.items():
            setattr(proveedor, campo, valor)
        db.flush()
        _auditar(db, usuario, proveedor, 'ACTUALIZAR', anteriores)
        db.commit()
        db.refresh(proveedor)
        return proveedor
    except IntegrityError as exc:
        db.rollback()
        raise ProveedorServiceError('Documento duplicado o referencia inválida.') from exc
    except Exception:
        db.rollback()
        raise


def desactivar_proveedor(db: Session, *, usuario_id: int, proveedor_id: int) -> Proveedor:
    try:
        usuario, empresa = _usuario_empresa(db, usuario_id, 'proveedores.editar')
        proveedor = db.scalar(select(Proveedor).where(Proveedor.id == proveedor_id,
                Proveedor.empresa_id == empresa.id).with_for_update())
        if proveedor is None:
            raise ProveedorServiceError('Proveedor no encontrado en esta empresa.')
        if not proveedor.activo:
            raise ProveedorServiceError('El proveedor ya está inactivo.')
        proveedor.activo = False
        db.flush()
        _auditar(db, usuario, proveedor, 'ACTUALIZAR', {'activo': True})
        db.commit()
        db.refresh(proveedor)
        return proveedor
    except Exception:
        db.rollback()
        raise
