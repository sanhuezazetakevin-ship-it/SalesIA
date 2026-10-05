
"""
SalesIA Enterprise
FASE 07-B.2 — Servicio empresarial de categorias.

Incluye aislamiento multiempresa, RBAC, baja logica,
auditoria transaccional y validacion de duplicados.
"""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.categoria import Categoria
from app.models.producto import Producto
from app.models.auditoria import Auditoria

from app.schemas.categorias import (
    CategoriaCreate,
    CategoriaUpdate,
)

from app.services.role_service import _obtener_permisos_efectivos


PERMISO_VER = "categorias.ver"
PERMISO_CREAR = "categorias.crear"
PERMISO_EDITAR = "categorias.editar"


class CategoriaServiceError(Exception):
    """Error controlado del modulo de categorias."""


def _validar_acceso(
    db: Session,
    *,
    usuario_id: int,
    permiso: str,
) -> tuple[Usuario, Empresa]:
    if type(usuario_id) is not int or usuario_id <= 0:
        raise CategoriaServiceError(
            "Identificador de usuario invalido."
        )

    usuario = db.scalar(
        select(Usuario).where(
            Usuario.id == usuario_id,
            Usuario.activo.is_(True),
        )
    )

    if usuario is None:
        raise CategoriaServiceError(
            "Usuario no disponible."
        )

    empresa = db.scalar(
        select(Empresa).where(
            Empresa.id == usuario.empresa_id,
            Empresa.activo.is_(True),
        )
    )

    if empresa is None:
        raise CategoriaServiceError(
            "Empresa no disponible."
        )

    permisos = _obtener_permisos_efectivos(
        db,
        usuario_id=usuario.id,
        empresa_id=empresa.id,
    )

    if permiso not in permisos:
        raise CategoriaServiceError(
            "Operacion no autorizada."
        )

    return usuario, empresa


def _nombre_ocupado(
    db: Session,
    *,
    empresa_id: int,
    nombre: str,
    excluir_id: int | None = None,
) -> bool:
    consulta = select(Categoria.id).where(
        Categoria.empresa_id == empresa_id,
        Categoria.nombre == nombre,
    )

    if excluir_id is not None:
        consulta = consulta.where(Categoria.id != excluir_id)

    return db.scalar(consulta.limit(1)) is not None


def crear_categoria(
    db: Session,
    *,
    usuario_id: int,
    datos: CategoriaCreate,
) -> Categoria:
    try:
        if not isinstance(datos, CategoriaCreate):
            raise CategoriaServiceError(
                "Datos de categoria invalidos."
            )

        usuario, empresa = _validar_acceso(
            db,
            usuario_id=usuario_id,
            permiso=PERMISO_CREAR,
        )

        if _nombre_ocupado(
            db,
            empresa_id=empresa.id,
            nombre=datos.nombre,
        ):
            raise CategoriaServiceError(
                "La categoria ya existe en la empresa."
            )

        categoria = Categoria(
            empresa_id=empresa.id,
            nombre=datos.nombre,
            descripcion=datos.descripcion,
            activo=True,
        )

        db.add(categoria)
        db.flush()

        db.add(
            Auditoria(
                empresa_id=empresa.id,
                usuario_id=usuario.id,
                accion="CREAR",
                entidad="categorias",
                entidad_id=categoria.id,
                descripcion="Registro empresarial de categoria.",
                datos_anteriores=None,
                datos_nuevos={
                    "nombre": categoria.nombre,
                    "descripcion": categoria.descripcion,
                    "activo": True,
                },
                origen="SISTEMA",
            )
        )

        db.flush()
        db.commit()
        db.refresh(categoria)

        return categoria

    except IntegrityError as exc:
        db.rollback()
        raise CategoriaServiceError(
            "No fue posible registrar la categoria. "
            "Verifique que su nombre no este duplicado."
        ) from exc

    except Exception:
        db.rollback()
        raise


def obtener_categoria(
    db: Session,
    *,
    usuario_id: int,
    categoria_id: int,
) -> Categoria:
    if type(categoria_id) is not int or categoria_id <= 0:
        raise CategoriaServiceError(
            "Identificador de categoria invalido."
        )

    _, empresa = _validar_acceso(
        db,
        usuario_id=usuario_id,
        permiso=PERMISO_VER,
    )

    categoria = db.scalar(
        select(Categoria).where(
            Categoria.id == categoria_id,
            Categoria.empresa_id == empresa.id,
        )
    )

    if categoria is None:
        raise CategoriaServiceError(
            "Categoria no disponible en esta empresa."
        )

    return categoria


def listar_categorias(
    db: Session,
    *,
    usuario_id: int,
    pagina: int = 1,
    limite: int = 20,
    busqueda: str | None = None,
    activo: bool | None = None,
) -> dict:
    if type(pagina) is not int or pagina < 1:
        raise CategoriaServiceError("Pagina invalida.")

    if type(limite) is not int or not 1 <= limite <= 100:
        raise CategoriaServiceError(
            "El limite debe estar entre 1 y 100."
        )

    if activo is not None and type(activo) is not bool:
        raise CategoriaServiceError("Filtro activo invalido.")

    if busqueda is not None:
        if not isinstance(busqueda, str):
            raise CategoriaServiceError("Busqueda invalida.")

        busqueda = busqueda.strip()

        if len(busqueda) > 120:
            raise CategoriaServiceError(
                "La busqueda supera los 120 caracteres."
            )

        busqueda = busqueda or None

    _, empresa = _validar_acceso(
        db,
        usuario_id=usuario_id,
        permiso=PERMISO_VER,
    )

    condiciones = [Categoria.empresa_id == empresa.id]

    if activo is not None:
        condiciones.append(Categoria.activo.is_(activo))

    if busqueda is not None:
        condiciones.append(
            Categoria.nombre.icontains(
                busqueda,
                autoescape=True,
            )
        )

    total = db.scalar(
        select(func.count(Categoria.id)).where(*condiciones)
    )

    categorias = db.scalars(
        select(Categoria)
        .where(*condiciones)
        .order_by(Categoria.id.asc())
        .offset((pagina - 1) * limite)
        .limit(limite)
    ).all()

    return {
        "total": total,
        "pagina": pagina,
        "limite": limite,
        "categorias": categorias,
    }


def actualizar_categoria(
    db: Session,
    *,
    usuario_id: int,
    categoria_id: int,
    datos: CategoriaUpdate,
) -> Categoria:
    try:
        if type(categoria_id) is not int or categoria_id <= 0:
            raise CategoriaServiceError(
                "Identificador de categoria invalido."
            )

        if not isinstance(datos, CategoriaUpdate):
            raise CategoriaServiceError(
                "Datos de actualizacion invalidos."
            )

        usuario, empresa = _validar_acceso(
            db,
            usuario_id=usuario_id,
            permiso=PERMISO_EDITAR,
        )

        categoria = db.scalar(
            select(Categoria)
            .where(
                Categoria.id == categoria_id,
                Categoria.empresa_id == empresa.id,
            )
            .with_for_update()
        )

        if categoria is None:
            raise CategoriaServiceError(
                "Categoria no disponible en esta empresa."
            )

        cambios = datos.model_dump(exclude_unset=True)

        if not cambios:
            raise CategoriaServiceError(
                "Debe proporcionar al menos un campo."
            )

        if "nombre" in cambios and cambios["nombre"] is None:
            raise CategoriaServiceError(
                "El nombre no admite null."
            )

        valores_anteriores = {
            "nombre": categoria.nombre,
            "descripcion": categoria.descripcion,
        }

        valores_finales = {
            **valores_anteriores,
            **cambios,
        }

        datos_validados = CategoriaCreate.model_validate(
            valores_finales
        )

        valores_finales = datos_validados.model_dump()

        cambios_reales = {
            campo: valor
            for campo, valor in valores_finales.items()
            if valor != valores_anteriores[campo]
        }

        if not cambios_reales:
            raise CategoriaServiceError(
                "No se detectaron modificaciones."
            )

        if (
            "nombre" in cambios_reales
            and _nombre_ocupado(
                db,
                empresa_id=empresa.id,
                nombre=valores_finales["nombre"],
                excluir_id=categoria.id,
            )
        ):
            raise CategoriaServiceError(
                "Ya existe otra categoria con ese nombre."
            )

        anteriores = {
            campo: valores_anteriores[campo]
            for campo in cambios_reales
        }

        for campo, valor in cambios_reales.items():
            setattr(categoria, campo, valor)

        db.flush()

        db.add(
            Auditoria(
                empresa_id=empresa.id,
                usuario_id=usuario.id,
                accion="ACTUALIZAR",
                entidad="categorias",
                entidad_id=categoria.id,
                descripcion="Actualizacion empresarial de categoria.",
                datos_anteriores=anteriores,
                datos_nuevos=cambios_reales,
                origen="SISTEMA",
            )
        )

        db.flush()
        db.commit()
        db.refresh(categoria)

        return categoria

    except IntegrityError as exc:
        db.rollback()
        raise CategoriaServiceError(
            "No fue posible actualizar la categoria."
        ) from exc

    except Exception:
        db.rollback()
        raise


def desactivar_categoria(
    db: Session,
    *,
    usuario_id: int,
    categoria_id: int,
) -> Categoria:
    try:
        if type(categoria_id) is not int or categoria_id <= 0:
            raise CategoriaServiceError(
                "Identificador de categoria invalido."
            )

        usuario, empresa = _validar_acceso(
            db,
            usuario_id=usuario_id,
            permiso=PERMISO_EDITAR,
        )

        # Serializa las bajas de categorias y cambios
        # empresariales que adopten este mismo bloqueo.
        categoria = db.scalar(
            select(Categoria)
            .where(
                Categoria.id == categoria_id,
                Categoria.empresa_id == empresa.id,
            )
            .with_for_update()
        )

        if categoria is None:
            raise CategoriaServiceError(
                "Categoria no disponible en esta empresa."
            )

        if not categoria.activo:
            raise CategoriaServiceError(
                "La categoria ya se encuentra inactiva."
            )

        # No desactivar categorias con productos activos.
        # La futura asignacion de productos a categorias
        # tambien debera bloquear esta fila.
        producto_activo = db.scalar(
            select(Producto.id)
            .where(
                Producto.empresa_id == empresa.id,
                Producto.categoria_id == categoria.id,
                Producto.activo.is_(True),
            )
            .limit(1)
        )

        if producto_activo is not None:
            raise CategoriaServiceError(
                "La categoria tiene productos activos asociados."
            )

        categoria.activo = False
        db.flush()

        db.add(
            Auditoria(
                empresa_id=empresa.id,
                usuario_id=usuario.id,
                accion="ACTUALIZAR",
                entidad="categorias",
                entidad_id=categoria.id,
                descripcion="Desactivacion empresarial de categoria.",
                datos_anteriores={"activo": True},
                datos_nuevos={"activo": False},
                origen="SISTEMA",
            )
        )

        db.flush()
        db.commit()
        db.refresh(categoria)

        return categoria

    except Exception:
        db.rollback()
        raise
