
"""
SalesIA Enterprise
FASE 06-B.2

Servicio empresarial de clientes.

Primera etapa:
- Validacion de usuario y empresa.
- Autorizacion mediante RBAC.
- Registro seguro de clientes.
- Prevencion de documentos duplicados.
- Auditoria transaccional.
"""

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.cliente import Cliente
from app.models.auditoria import Auditoria

from app.schemas.clientes import ClienteCreate, ClienteUpdate
from pydantic import ValidationError

from app.services.role_service import (
    _obtener_permisos_efectivos,
)


PERMISO_CREAR_CLIENTES = "clientes.crear"
PERMISO_VER_CLIENTES = "clientes.ver"
PERMISO_EDITAR_CLIENTES = "clientes.editar"


class ClienteServiceError(Exception):
    """Error controlado del servicio empresarial de clientes."""


def _validar_usuario_clientes(
    db: Session,
    *,
    usuario_id: int,
    permiso_requerido: str,
) -> tuple[Usuario, Empresa]:
    """
    Verifica usuario, empresa y permisos efectivos.

    La empresa se obtiene exclusivamente desde el
    usuario registrado en PostgreSQL.
    """

    if type(usuario_id) is not int or usuario_id <= 0:
        raise ClienteServiceError(
            "Identificador de usuario invalido."
        )

    usuario = db.scalar(
        select(Usuario).where(
            Usuario.id == usuario_id,
            Usuario.activo.is_(True),
        )
    )

    if usuario is None:
        raise ClienteServiceError(
            "El usuario no existe o esta inactivo."
        )

    empresa = db.scalar(
        select(Empresa).where(
            Empresa.id == usuario.empresa_id,
            Empresa.activo.is_(True),
        )
    )

    if empresa is None:
        raise ClienteServiceError(
            "La empresa no existe o esta inactiva."
        )

    permisos = _obtener_permisos_efectivos(
        db,
        usuario_id=usuario.id,
        empresa_id=empresa.id,
    )

    if permiso_requerido not in permisos:
        raise ClienteServiceError(
            "No tiene autorizacion para esta operacion."
        )

    return usuario, empresa


def crear_cliente(
    db: Session,
    *,
    usuario_id: int,
    datos: ClienteCreate,
) -> Cliente:
    """
    Registra un cliente dentro de la empresa del usuario.

    No acepta empresa_id externo.

    La creacion y su auditoria forman una unica
    transaccion.
    """

    try:
        if not isinstance(datos, ClienteCreate):
            raise ClienteServiceError(
                "Los datos del cliente son invalidos."
            )

        usuario, empresa = _validar_usuario_clientes(
            db,
            usuario_id=usuario_id,
            permiso_requerido=PERMISO_CREAR_CLIENTES,
        )

        # Comprobar duplicados cuando existe documento.
        if (
            datos.tipo_documento is not None
            and datos.numero_documento is not None
        ):
            existente = db.scalar(
                select(Cliente.id).where(
                    Cliente.empresa_id == empresa.id,
                    Cliente.tipo_documento ==
                    datos.tipo_documento,
                    Cliente.numero_documento ==
                    datos.numero_documento,
                )
            )

            if existente is not None:
                raise ClienteServiceError(
                    "Ya existe un cliente con este documento "
                    "en la empresa."
                )

        cliente = Cliente(
            empresa_id=empresa.id,
            nombre=datos.nombre,
            tipo_documento=datos.tipo_documento,
            numero_documento=datos.numero_documento,
            email=datos.email,
            telefono=datos.telefono,
            direccion=datos.direccion,
            activo=True,
        )

        db.add(cliente)
        db.flush()

        auditoria = Auditoria(
            empresa_id=empresa.id,
            usuario_id=usuario.id,
            accion="CREAR",
            entidad="clientes",
            entidad_id=cliente.id,
            descripcion="Registro empresarial de cliente.",
            datos_anteriores=None,
            datos_nuevos={
                "cliente_id": cliente.id,
                "empresa_id": empresa.id,
                "activo": True,
            },
            origen="SISTEMA",
        )

        db.add(auditoria)
        db.flush()

        db.commit()
        db.refresh(cliente)

        return cliente

    except IntegrityError as exc:
        db.rollback()
        raise ClienteServiceError(
            "No fue posible registrar el cliente. "
            "Verifique que sus datos no esten duplicados."
        ) from exc

    except Exception:
        db.rollback()
        raise


# ==========================================================
# FASE 06-C.1
# CONSULTA Y LISTADO EMPRESARIAL DE CLIENTES
# ==========================================================


def obtener_cliente(
    db: Session,
    *,
    usuario_id: int,
    cliente_id: int,
) -> Cliente:
    """
    Obtiene un cliente perteneciente exclusivamente
    a la empresa del usuario autenticado.

    Requiere clientes.ver.
    """

    if type(cliente_id) is not int or cliente_id <= 0:
        raise ClienteServiceError(
            "Identificador de cliente invalido."
        )

    usuario, empresa = _validar_usuario_clientes(
        db,
        usuario_id=usuario_id,
        permiso_requerido=PERMISO_VER_CLIENTES,
    )

    cliente = db.scalar(
        select(Cliente).where(
            Cliente.id == cliente_id,
            Cliente.empresa_id == empresa.id,
        )
    )

    if cliente is None:
        raise ClienteServiceError(
            "El cliente no existe en esta empresa."
        )

    return cliente


def listar_clientes(
    db: Session,
    *,
    usuario_id: int,
    pagina: int = 1,
    limite: int = 20,
    busqueda: str | None = None,
    activo: bool | None = None,
) -> dict:
    """
    Lista clientes exclusivamente de la empresa
    del usuario.

    Permite:
    - Busqueda por nombre o numero de documento.
    - Filtrado por estado activo/inactivo.
    - Paginacion.
    - Orden estable por ID.
    """

    if type(pagina) is not int or pagina < 1:
        raise ClienteServiceError(
            "La pagina debe ser un entero positivo."
        )

    if type(limite) is not int or not 1 <= limite <= 100:
        raise ClienteServiceError(
            "El limite debe estar entre 1 y 100."
        )

    if activo is not None and type(activo) is not bool:
        raise ClienteServiceError(
            "El filtro activo debe ser booleano."
        )

    if busqueda is not None:
        if not isinstance(busqueda, str):
            raise ClienteServiceError(
                "La busqueda debe ser texto."
            )

        busqueda = busqueda.strip()

        if len(busqueda) > 200:
            raise ClienteServiceError(
                "La busqueda supera los 200 caracteres."
            )

        if not busqueda:
            busqueda = None

    usuario, empresa = _validar_usuario_clientes(
        db,
        usuario_id=usuario_id,
        permiso_requerido=PERMISO_VER_CLIENTES,
    )

    condiciones = [
        Cliente.empresa_id == empresa.id,
    ]

    if activo is not None:
        condiciones.append(
            Cliente.activo.is_(activo)
        )

    if busqueda is not None:
        condiciones.append(
            or_(
                Cliente.nombre.icontains(
                    busqueda,
                    autoescape=True,
                ),
                Cliente.numero_documento.icontains(
                    busqueda,
                    autoescape=True,
                ),
            )
        )

    total = db.scalar(
        select(func.count(Cliente.id)).where(
            *condiciones
        )
    )

    clientes = db.scalars(
        select(Cliente)
        .where(*condiciones)
        .order_by(Cliente.id.asc())
        .offset((pagina - 1) * limite)
        .limit(limite)
    ).all()

    return {
        "total": total,
        "pagina": pagina,
        "limite": limite,
        "clientes": clientes,
    }

# ==========================================================
# FASE 06-C.3
# ACTUALIZACION EMPRESARIAL DE CLIENTES
# ==========================================================


def actualizar_cliente(
    db: Session,
    *,
    usuario_id: int,
    cliente_id: int,
    datos: ClienteUpdate,
) -> Cliente:
    """
    Actualiza parcialmente un cliente de la empresa
    del usuario autorizado.

    La modificacion y su auditoria se confirman
    dentro de una unica transaccion.
    """

    try:
        if type(cliente_id) is not int or cliente_id <= 0:
            raise ClienteServiceError(
                "Identificador de cliente invalido."
            )

        if not isinstance(datos, ClienteUpdate):
            raise ClienteServiceError(
                "Los datos de actualizacion son invalidos."
            )

        usuario, empresa = _validar_usuario_clientes(
            db,
            usuario_id=usuario_id,
            permiso_requerido=PERMISO_EDITAR_CLIENTES,
        )

        cliente = db.scalar(
            select(Cliente)
            .where(
                Cliente.id == cliente_id,
                Cliente.empresa_id == empresa.id,
            )
            .with_for_update()
        )

        if cliente is None:
            raise ClienteServiceError(
                "El cliente no existe en esta empresa."
            )

        cambios = datos.model_dump(exclude_unset=True)

        if not cambios:
            raise ClienteServiceError(
                "Debe proporcionar al menos un campo."
            )

        campos_editables = (
            "nombre",
            "tipo_documento",
            "numero_documento",
            "email",
            "telefono",
            "direccion",
        )

        valores_anteriores = {
            campo: getattr(cliente, campo)
            for campo in campos_editables
        }

        # Combinar los datos existentes con los cambios.
        # Los campos omitidos conservan su valor anterior.
        valores_finales = {
            **valores_anteriores,
            **cambios,
        }

        # Reutilizamos las validaciones de creacion para
        # comprobar que el estado final sea coherente.
        try:
            datos_validados = ClienteCreate.model_validate(
                valores_finales
            )
        except ValidationError as exc:
            raise ClienteServiceError(
                "La actualizacion produce datos invalidos. "
                "Verifique especialmente el documento."
            ) from exc

        valores_finales = datos_validados.model_dump()

        cambios_reales = {
            campo: valor
            for campo, valor in valores_finales.items()
            if valor != valores_anteriores[campo]
        }

        if not cambios_reales:
            raise ClienteServiceError(
                "No se detectaron modificaciones."
            )

        # Comprobar que el documento final no pertenece
        # a otro cliente de la misma empresa.
        tipo = valores_finales["tipo_documento"]
        numero = valores_finales["numero_documento"]

        if tipo is not None and numero is not None:
            duplicado = db.scalar(
                select(Cliente.id).where(
                    Cliente.empresa_id == empresa.id,
                    Cliente.id != cliente.id,
                    Cliente.tipo_documento == tipo,
                    Cliente.numero_documento == numero,
                )
            )

            if duplicado is not None:
                raise ClienteServiceError(
                    "Ya existe otro cliente con este "
                    "documento en la empresa."
                )

        datos_anteriores_auditoria = {
            campo: valores_anteriores[campo]
            for campo in cambios_reales
        }

        for campo, valor in cambios_reales.items():
            setattr(cliente, campo, valor)

        db.flush()

        db.add(
            Auditoria(
                empresa_id=empresa.id,
                usuario_id=usuario.id,
                accion="ACTUALIZAR",
                entidad="clientes",
                entidad_id=cliente.id,
                descripcion=(
                    "Actualizacion empresarial de cliente."
                ),
                datos_anteriores=datos_anteriores_auditoria,
                datos_nuevos=cambios_reales,
                origen="SISTEMA",
            )
        )

        db.flush()
        db.commit()
        db.refresh(cliente)

        return cliente

    except IntegrityError as exc:
        db.rollback()
        raise ClienteServiceError(
            "No fue posible actualizar el cliente. "
            "Verifique que el documento no este duplicado."
        ) from exc

    except Exception:
        db.rollback()
        raise


# ==========================================================
# FASE 06-C.5
# BAJA LOGICA EMPRESARIAL DE CLIENTES
# ==========================================================


def desactivar_cliente(
    db: Session,
    *,
    usuario_id: int,
    cliente_id: int,
) -> Cliente:
    """
    Desactiva un cliente sin eliminar su registro.

    Requiere clientes.editar y mantiene el historial
    mediante una auditoria transaccional.
    """

    try:
        if type(cliente_id) is not int or cliente_id <= 0:
            raise ClienteServiceError(
                "Identificador de cliente invalido."
            )

        usuario, empresa = _validar_usuario_clientes(
            db,
            usuario_id=usuario_id,
            permiso_requerido=PERMISO_EDITAR_CLIENTES,
        )

        cliente = db.scalar(
            select(Cliente)
            .where(
                Cliente.id == cliente_id,
                Cliente.empresa_id == empresa.id,
            )
            .with_for_update()
        )

        if cliente is None:
            raise ClienteServiceError(
                "El cliente no existe en esta empresa."
            )

        if not cliente.activo:
            raise ClienteServiceError(
                "El cliente ya se encuentra inactivo."
            )

        cliente.activo = False

        db.flush()

        db.add(
            Auditoria(
                empresa_id=empresa.id,
                usuario_id=usuario.id,
                accion="ACTUALIZAR",
                entidad="clientes",
                entidad_id=cliente.id,
                descripcion="Desactivacion empresarial de cliente.",
                datos_anteriores={"activo": True},
                datos_nuevos={"activo": False},
                origen="SISTEMA",
            )
        )

        db.flush()
        db.commit()
        db.refresh(cliente)

        return cliente

    except Exception:
        db.rollback()
        raise
