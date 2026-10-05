
"""
SalesIA Enterprise — FASE 07-C.2
Servicio empresarial de Productos.

- Aislamiento multiempresa.
- Autorizacion RBAC.
- Validacion de SKU y categoria.
- Precios con Decimal.
- Auditoria transaccional.
- Baja logica, sin modificar inventario.
"""

from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.producto import Producto
from app.models.categoria import Categoria
from app.models.auditoria import Auditoria

from app.schemas.productos import ProductoCreate, ProductoUpdate
from app.services.role_service import _obtener_permisos_efectivos


PERMISO_VER = "productos.ver"
PERMISO_CREAR = "productos.crear"
PERMISO_EDITAR = "productos.editar"

CAMPOS_PRODUCTO = (
    "categoria_id",
    "sku",
    "nombre",
    "descripcion",
    "tipo_item",
    "precio_venta",
    "costo_referencia",
    "controla_stock",
)


class ProductoServiceError(Exception):
    """Error controlado del servicio de productos."""


def _validar_acceso(
    db: Session,
    *,
    usuario_id: int,
    permiso: str,
) -> tuple[Usuario, Empresa]:
    if type(usuario_id) is not int or usuario_id <= 0:
        raise ProductoServiceError("Usuario invalido.")

    usuario = db.scalar(
        select(Usuario).where(
            Usuario.id == usuario_id,
            Usuario.activo.is_(True),
        )
    )

    if usuario is None:
        raise ProductoServiceError("Usuario no disponible.")

    empresa = db.scalar(
        select(Empresa).where(
            Empresa.id == usuario.empresa_id,
            Empresa.activo.is_(True),
        )
    )

    if empresa is None:
        raise ProductoServiceError("Empresa no disponible.")

    permisos = _obtener_permisos_efectivos(
        db,
        usuario_id=usuario.id,
        empresa_id=empresa.id,
    )

    if permiso not in permisos:
        raise ProductoServiceError("Operacion no autorizada.")

    return usuario, empresa


def _validar_categoria(
    db: Session,
    *,
    empresa_id: int,
    categoria_id: int | None,
) -> None:
    if categoria_id is None:
        return

    if type(categoria_id) is not int or categoria_id <= 0:
        raise ProductoServiceError("Categoria invalida.")

    # Coordina la asignacion de productos con la baja logica
    # de categorias, que bloquea esta misma fila.
    categoria = db.scalar(
        select(Categoria)
        .where(
            Categoria.id == categoria_id,
            Categoria.empresa_id == empresa_id,
            Categoria.activo.is_(True),
        )
        .with_for_update()
    )

    if categoria is None:
        raise ProductoServiceError(
            "La categoria no existe, esta inactiva "
            "o no pertenece a esta empresa."
        )


def _sku_ocupado(
    db: Session,
    *,
    empresa_id: int,
    sku: str,
    excluir_id: int | None = None,
) -> bool:
    consulta = select(Producto.id).where(
        Producto.empresa_id == empresa_id,
        Producto.sku == sku,
    )

    if excluir_id is not None:
        consulta = consulta.where(Producto.id != excluir_id)

    return db.scalar(consulta.limit(1)) is not None


def crear_producto(
    db: Session,
    *,
    usuario_id: int,
    datos: ProductoCreate,
) -> Producto:
    try:
        if not isinstance(datos, ProductoCreate):
            raise ProductoServiceError(
                "Datos de producto invalidos."
            )

        usuario, empresa = _validar_acceso(
            db,
            usuario_id=usuario_id,
            permiso=PERMISO_CREAR,
        )

        _validar_categoria(
            db,
            empresa_id=empresa.id,
            categoria_id=datos.categoria_id,
        )

        if _sku_ocupado(
            db,
            empresa_id=empresa.id,
            sku=datos.sku,
        ):
            raise ProductoServiceError(
                "Ya existe un producto con este SKU "
                "en la empresa."
            )

        producto = Producto(
            empresa_id=empresa.id,
            **datos.model_dump(),
            activo=True,
        )

        db.add(producto)
        db.flush()

        db.add(
            Auditoria(
                empresa_id=empresa.id,
                usuario_id=usuario.id,
                accion="CREAR",
                entidad="productos",
                entidad_id=producto.id,
                descripcion="Registro empresarial de producto.",
                datos_anteriores=None,
                datos_nuevos={
                    "producto_id": producto.id,
                    "empresa_id": empresa.id,
                    "sku": producto.sku,
                    "categoria_id": producto.categoria_id,
                    "activo": True,
                },
                origen="SISTEMA",
            )
        )

        db.flush()
        db.commit()
        db.refresh(producto)

        return producto

    except IntegrityError as exc:
        db.rollback()
        raise ProductoServiceError(
            "No fue posible registrar el producto. "
            "Verifique SKU y categoria."
        ) from exc

    except Exception:
        db.rollback()
        raise


def obtener_producto(
    db: Session,
    *,
    usuario_id: int,
    producto_id: int,
) -> Producto:
    if type(producto_id) is not int or producto_id <= 0:
        raise ProductoServiceError("Producto invalido.")

    _, empresa = _validar_acceso(
        db,
        usuario_id=usuario_id,
        permiso=PERMISO_VER,
    )

    producto = db.scalar(
        select(Producto).where(
            Producto.id == producto_id,
            Producto.empresa_id == empresa.id,
        )
    )

    if producto is None:
        raise ProductoServiceError(
            "Producto no disponible en esta empresa."
        )

    return producto


def listar_productos(
    db: Session,
    *,
    usuario_id: int,
    pagina: int = 1,
    limite: int = 20,
    busqueda: str | None = None,
    categoria_id: int | None = None,
    tipo_item: str | None = None,
    activo: bool | None = None,
) -> dict:
    if type(pagina) is not int or pagina < 1:
        raise ProductoServiceError("Pagina invalida.")

    if type(limite) is not int or not 1 <= limite <= 100:
        raise ProductoServiceError(
            "El limite debe estar entre 1 y 100."
        )

    if activo is not None and type(activo) is not bool:
        raise ProductoServiceError("Filtro activo invalido.")

    if categoria_id is not None and (
        type(categoria_id) is not int or categoria_id <= 0
    ):
        raise ProductoServiceError("Filtro categoria invalido.")

    if tipo_item is not None and tipo_item not in (
        "PRODUCTO", "SERVICIO", "INSUMO", "MISCELANEO"
    ):
        raise ProductoServiceError("Tipo de item invalido.")

    if busqueda is not None:
        if not isinstance(busqueda, str):
            raise ProductoServiceError("Busqueda invalida.")

        busqueda = busqueda.strip()

        if len(busqueda) > 200:
            raise ProductoServiceError(
                "La busqueda supera los 200 caracteres."
            )

        busqueda = busqueda or None

    _, empresa = _validar_acceso(
        db,
        usuario_id=usuario_id,
        permiso=PERMISO_VER,
    )

    condiciones = [Producto.empresa_id == empresa.id]

    if activo is not None:
        condiciones.append(Producto.activo.is_(activo))

    if categoria_id is not None:
        condiciones.append(
            Producto.categoria_id == categoria_id
        )

    if tipo_item is not None:
        condiciones.append(Producto.tipo_item == tipo_item)

    if busqueda is not None:
        condiciones.append(
            or_(
                Producto.nombre.icontains(
                    busqueda,
                    autoescape=True,
                ),
                Producto.sku.icontains(
                    busqueda,
                    autoescape=True,
                ),
            )
        )

    total = db.scalar(
        select(func.count(Producto.id)).where(*condiciones)
    )

    productos = db.scalars(
        select(Producto)
        .where(*condiciones)
        .order_by(Producto.id.asc())
        .offset((pagina - 1) * limite)
        .limit(limite)
    ).all()

    return {
        "total": total,
        "pagina": pagina,
        "limite": limite,
        "productos": productos,
    }


def actualizar_producto(
    db: Session,
    *,
    usuario_id: int,
    producto_id: int,
    datos: ProductoUpdate,
) -> Producto:
    try:
        if type(producto_id) is not int or producto_id <= 0:
            raise ProductoServiceError("Producto invalido.")

        if not isinstance(datos, ProductoUpdate):
            raise ProductoServiceError(
                "Datos de actualizacion invalidos."
            )

        cambios = datos.model_dump(exclude_unset=True)

        if not cambios:
            raise ProductoServiceError(
                "Debe proporcionar al menos un campo."
            )

        usuario, empresa = _validar_acceso(
            db,
            usuario_id=usuario_id,
            permiso=PERMISO_EDITAR,
        )

        # Lectura inicial para conocer la categoria de destino.
        referencia = db.scalar(
            select(Producto).where(
                Producto.id == producto_id,
                Producto.empresa_id == empresa.id,
            )
        )

        if referencia is None:
            raise ProductoServiceError(
                "Producto no disponible en esta empresa."
            )

        # Si se cambia la categoria, bloquear primero la
        # categoria de destino para coordinarla con su baja.
        if (
            "categoria_id" in cambios
            and cambios["categoria_id"] is not None
        ):
            _validar_categoria(
                db,
                empresa_id=empresa.id,
                categoria_id=cambios["categoria_id"],
            )

        producto = db.scalar(
            select(Producto)
            .where(
                Producto.id == producto_id,
                Producto.empresa_id == empresa.id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )

        if producto is None:
            raise ProductoServiceError(
                "Producto no disponible en esta empresa."
            )

        anteriores = {
            campo: getattr(producto, campo)
            for campo in CAMPOS_PRODUCTO
        }

        finales = {**anteriores, **cambios}

        try:
            validados = ProductoCreate.model_validate(finales)
        except ValidationError as exc:
            raise ProductoServiceError(
                "La actualizacion produce datos invalidos."
            ) from exc

        finales = validados.model_dump()

        cambios_reales = {
            campo: valor
            for campo, valor in finales.items()
            if valor != anteriores[campo]
        }

        if not cambios_reales:
            raise ProductoServiceError(
                "No se detectaron modificaciones."
            )

        if (
            "sku" in cambios_reales
            and _sku_ocupado(
                db,
                empresa_id=empresa.id,
                sku=finales["sku"],
                excluir_id=producto.id,
            )
        ):
            raise ProductoServiceError(
                "Ya existe otro producto con este SKU."
            )

        auditoria_anteriores = {
            campo: anteriores[campo]
            for campo in cambios_reales
        }

        # Los valores Decimal se serializan como texto para JSON.
        def serializar(valores):
            return {
                clave: (
                    str(valor)
                    if hasattr(valor, "as_tuple")
                    else valor
                )
                for clave, valor in valores.items()
            }

        for campo, valor in cambios_reales.items():
            setattr(producto, campo, valor)

        db.flush()

        db.add(
            Auditoria(
                empresa_id=empresa.id,
                usuario_id=usuario.id,
                accion="ACTUALIZAR",
                entidad="productos",
                entidad_id=producto.id,
                descripcion="Actualizacion empresarial de producto.",
                datos_anteriores=serializar(auditoria_anteriores),
                datos_nuevos=serializar(cambios_reales),
                origen="SISTEMA",
            )
        )

        db.flush()
        db.commit()
        db.refresh(producto)

        return producto

    except IntegrityError as exc:
        db.rollback()
        raise ProductoServiceError(
            "No fue posible actualizar el producto. "
            "Verifique SKU y categoria."
        ) from exc

    except Exception:
        db.rollback()
        raise


def desactivar_producto(
    db: Session,
    *,
    usuario_id: int,
    producto_id: int,
) -> Producto:
    try:
        if type(producto_id) is not int or producto_id <= 0:
            raise ProductoServiceError("Producto invalido.")

        usuario, empresa = _validar_acceso(
            db,
            usuario_id=usuario_id,
            permiso=PERMISO_EDITAR,
        )

        producto = db.scalar(
            select(Producto)
            .where(
                Producto.id == producto_id,
                Producto.empresa_id == empresa.id,
            )
            .with_for_update()
        )

        if producto is None:
            raise ProductoServiceError(
                "Producto no disponible en esta empresa."
            )

        if not producto.activo:
            raise ProductoServiceError(
                "El producto ya se encuentra inactivo."
            )

        producto.activo = False
        db.flush()

        db.add(
            Auditoria(
                empresa_id=empresa.id,
                usuario_id=usuario.id,
                accion="ACTUALIZAR",
                entidad="productos",
                entidad_id=producto.id,
                descripcion="Desactivacion empresarial de producto.",
                datos_anteriores={"activo": True},
                datos_nuevos={"activo": False},
                origen="SISTEMA",
            )
        )

        db.flush()
        db.commit()
        db.refresh(producto)

        return producto

    except Exception:
        db.rollback()
        raise
