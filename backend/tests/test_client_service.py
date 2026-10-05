
"""
SalesIA Enterprise
FASE 06-B.3

Pruebas del registro empresarial de clientes.
Exclusivamente PostgreSQL Testing.
"""

from uuid import uuid4

import pytest

from sqlalchemy import func, select

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.permiso import Permiso
from app.models.cliente import Cliente
from app.models.auditoria import Auditoria
from app.models.asociaciones import usuarios_roles, roles_permisos

from app.schemas.clientes import ClienteCreate
from app.services.client_service import (
    ClienteServiceError,
    crear_cliente,
)


def preparar_escenario_clientes(
    db,
    *,
    conceder_permiso=True,
):
    identificador = uuid4().hex

    empresa = Empresa(
        razon_social=f"Clientes Testing {identificador[:12]}",
        ruc=str(uuid4().int % 10**11).zfill(11),
        moneda_base="PEN",
        activo=True,
    )

    db.add(empresa)
    db.flush()

    rol = Rol(
        empresa_id=empresa.id,
        nombre=f"CLIENTES_TEST_{identificador[:8]}",
        descripcion="Rol temporal para pruebas de clientes",
    )

    db.add(rol)
    db.flush()

    if conceder_permiso:
        permiso = db.scalar(
            select(Permiso).where(
                Permiso.codigo == "clientes.crear"
            )
        )

        if permiso is None:
            permiso = Permiso(
                codigo="clientes.crear",
                descripcion="Crear clientes empresariales",
            )
            db.add(permiso)
            db.flush()

        db.execute(
            roles_permisos.insert().values(
                rol_id=rol.id,
                permiso_id=permiso.id,
            )
        )

    usuario = Usuario(
        empresa_id=empresa.id,
        nombre="Operador Clientes Testing",
        email=f"clientes-{identificador}@example.com",
        password_hash="hash-ficticio-no-utilizable",
        activo=True,
    )

    db.add(usuario)
    db.flush()

    db.execute(
        usuarios_roles.insert().values(
            usuario_id=usuario.id,
            rol_id=rol.id,
            empresa_id=empresa.id,
        )
    )

    # Confirma el escenario dentro del savepoint protegido.
    # La transaccion exterior de db_testing no se confirma.
    db.commit()

    return {
        "empresa_id": empresa.id,
        "usuario_id": usuario.id,
        "rol_id": rol.id,
    }


def datos_cliente(*, documento="12345678"):
    return ClienteCreate(
        nombre="Cliente Empresarial Testing",
        tipo_documento="DNI" if documento else None,
        numero_documento=documento,
        email="cliente@example.com",
        telefono="999888777",
        direccion="Direccion de prueba",
    )


def test_creacion_cliente_autorizada_y_auditada(db_testing):
    escenario = preparar_escenario_clientes(db_testing)

    cliente = crear_cliente(
        db_testing,
        usuario_id=escenario["usuario_id"],
        datos=datos_cliente(),
    )

    assert cliente.id > 0
    assert cliente.empresa_id == escenario["empresa_id"]
    assert cliente.activo is True

    auditorias = db_testing.scalars(
        select(Auditoria).where(
            Auditoria.empresa_id == escenario["empresa_id"],
            Auditoria.usuario_id == escenario["usuario_id"],
            Auditoria.entidad == "clientes",
            Auditoria.entidad_id == cliente.id,
            Auditoria.accion == "CREAR",
        )
    ).all()

    assert len(auditorias) == 1
    assert auditorias[0].datos_nuevos["cliente_id"] == cliente.id


def test_usuario_sin_permiso_no_puede_crear_cliente(db_testing):
    escenario = preparar_escenario_clientes(
        db_testing,
        conceder_permiso=False,
    )

    with pytest.raises(ClienteServiceError):
        crear_cliente(
            db_testing,
            usuario_id=escenario["usuario_id"],
            datos=datos_cliente(),
        )

    cantidad = db_testing.scalar(
        select(func.count(Cliente.id)).where(
            Cliente.empresa_id == escenario["empresa_id"]
        )
    )

    assert cantidad == 0


def test_documento_duplicado_en_misma_empresa(db_testing):
    escenario = preparar_escenario_clientes(db_testing)

    primero = crear_cliente(
        db_testing,
        usuario_id=escenario["usuario_id"],
        datos=datos_cliente(),
    )

    with pytest.raises(
        ClienteServiceError,
        match="Ya existe un cliente",
    ):
        crear_cliente(
            db_testing,
            usuario_id=escenario["usuario_id"],
            datos=datos_cliente(),
        )

    cantidad = db_testing.scalar(
        select(func.count(Cliente.id)).where(
            Cliente.empresa_id == escenario["empresa_id"],
            Cliente.tipo_documento == "DNI",
            Cliente.numero_documento == "12345678",
        )
    )

    assert cantidad == 1

    auditorias = db_testing.scalars(
        select(Auditoria).where(
            Auditoria.entidad == "clientes",
            Auditoria.entidad_id == primero.id,
        )
    ).all()

    assert len(auditorias) == 1


def test_mismo_documento_en_empresas_distintas(db_testing):
    empresa_a = preparar_escenario_clientes(db_testing)
    empresa_b = preparar_escenario_clientes(db_testing)

    cliente_a = crear_cliente(
        db_testing,
        usuario_id=empresa_a["usuario_id"],
        datos=datos_cliente(),
    )

    cliente_b = crear_cliente(
        db_testing,
        usuario_id=empresa_b["usuario_id"],
        datos=datos_cliente(),
    )

    assert cliente_a.id != cliente_b.id
    assert cliente_a.empresa_id == empresa_a["empresa_id"]
    assert cliente_b.empresa_id == empresa_b["empresa_id"]

    assert cliente_a.numero_documento == cliente_b.numero_documento


def test_permite_cliente_sin_documento(db_testing):
    escenario = preparar_escenario_clientes(db_testing)

    cliente = crear_cliente(
        db_testing,
        usuario_id=escenario["usuario_id"],
        datos=datos_cliente(documento=None),
    )

    assert cliente.tipo_documento is None
    assert cliente.numero_documento is None
    assert cliente.activo is True


def test_empresa_inactiva_no_puede_crear_cliente(db_testing):
    escenario = preparar_escenario_clientes(db_testing)

    empresa = db_testing.get(
        Empresa,
        escenario["empresa_id"],
    )

    empresa.activo = False
    db_testing.commit()

    with pytest.raises(ClienteServiceError):
        crear_cliente(
            db_testing,
            usuario_id=escenario["usuario_id"],
            datos=datos_cliente(),
        )

    cantidad = db_testing.scalar(
        select(func.count(Cliente.id)).where(
            Cliente.empresa_id == escenario["empresa_id"]
        )
    )

    assert cantidad == 0


# ==========================================================
# FASE 06-B.4
# SEGURIDAD E INTEGRIDAD TRANSACCIONAL
# ==========================================================


def test_fallo_de_auditoria_revierte_creacion(
    db_testing,
    monkeypatch,
):
    """
    Si falla el registro de auditoria, el cliente
    tampoco debe permanecer guardado.
    """

    escenario = preparar_escenario_clientes(db_testing)

    agregar_original = db_testing.add

    def simular_fallo_auditoria(objeto):
        if isinstance(objeto, Auditoria):
            raise RuntimeError(
                "Fallo simulado de auditoria."
            )

        return agregar_original(objeto)

    monkeypatch.setattr(
        db_testing,
        "add",
        simular_fallo_auditoria,
    )

    with pytest.raises(
        RuntimeError,
        match="Fallo simulado de auditoria",
    ):
        crear_cliente(
            db_testing,
            usuario_id=escenario["usuario_id"],
            datos=datos_cliente(),
        )

    cantidad_clientes = db_testing.scalar(
        select(func.count(Cliente.id)).where(
            Cliente.empresa_id == escenario["empresa_id"]
        )
    )

    cantidad_auditorias = db_testing.scalar(
        select(func.count(Auditoria.id)).where(
            Auditoria.empresa_id == escenario["empresa_id"],
            Auditoria.entidad == "clientes",
        )
    )

    assert cantidad_clientes == 0
    assert cantidad_auditorias == 0


def test_usuario_inactivo_no_puede_crear_cliente(
    db_testing,
):
    escenario = preparar_escenario_clientes(db_testing)

    usuario = db_testing.get(
        Usuario,
        escenario["usuario_id"],
    )

    usuario.activo = False
    db_testing.commit()

    with pytest.raises(ClienteServiceError):
        crear_cliente(
            db_testing,
            usuario_id=escenario["usuario_id"],
            datos=datos_cliente(),
        )

    cantidad = db_testing.scalar(
        select(func.count(Cliente.id)).where(
            Cliente.empresa_id == escenario["empresa_id"]
        )
    )

    assert cantidad == 0

# ==========================================================
# FASE 06-C.2
# PRUEBAS DE CONSULTA, BUSQUEDA Y PAGINACION
# ==========================================================

from app.services.client_service import (
    obtener_cliente,
    listar_clientes,
)


def conceder_permiso_ver_clientes(db, escenario):
    """
    Agrega clientes.ver al rol existente del escenario.

    El commit confirma solamente el savepoint de Testing;
    la transaccion exterior sigue protegida.
    """

    permiso = db.scalar(
        select(Permiso).where(
            Permiso.codigo == "clientes.ver"
        )
    )

    if permiso is None:
        permiso = Permiso(
            codigo="clientes.ver",
            descripcion="Consultar clientes empresariales",
        )
        db.add(permiso)
        db.flush()

    db.execute(
        roles_permisos.insert().values(
            rol_id=escenario["rol_id"],
            permiso_id=permiso.id,
        )
    )

    db.commit()


def crear_clientes_para_consulta(db, escenario, cantidad=5):
    """
    Crea datos temporales usando el servicio empresarial.
    """

    clientes = []

    for numero in range(1, cantidad + 1):
        cliente = crear_cliente(
            db,
            usuario_id=escenario["usuario_id"],
            datos=ClienteCreate(
                nombre=f"Cliente Consulta {numero}",
                tipo_documento="DNI",
                numero_documento=f"{numero:08d}",
            ),
        )

        clientes.append(cliente)

    return clientes


def test_consulta_individual_cliente_propio(db_testing):
    escenario = preparar_escenario_clientes(db_testing)
    conceder_permiso_ver_clientes(db_testing, escenario)

    cliente = crear_cliente(
        db_testing,
        usuario_id=escenario["usuario_id"],
        datos=datos_cliente(),
    )

    resultado = obtener_cliente(
        db_testing,
        usuario_id=escenario["usuario_id"],
        cliente_id=cliente.id,
    )

    assert resultado.id == cliente.id
    assert resultado.empresa_id == escenario["empresa_id"]
    assert resultado.numero_documento == "12345678"


def test_usuario_sin_permiso_ver_no_puede_consultar(db_testing):
    escenario = preparar_escenario_clientes(db_testing)

    cliente = crear_cliente(
        db_testing,
        usuario_id=escenario["usuario_id"],
        datos=datos_cliente(),
    )

    with pytest.raises(ClienteServiceError):
        obtener_cliente(
            db_testing,
            usuario_id=escenario["usuario_id"],
            cliente_id=cliente.id,
        )

    with pytest.raises(ClienteServiceError):
        listar_clientes(
            db_testing,
            usuario_id=escenario["usuario_id"],
        )


def test_no_puede_consultar_clientes_otra_empresa(db_testing):
    empresa_a = preparar_escenario_clientes(db_testing)
    empresa_b = preparar_escenario_clientes(db_testing)

    conceder_permiso_ver_clientes(db_testing, empresa_a)
    conceder_permiso_ver_clientes(db_testing, empresa_b)

    cliente_b = crear_cliente(
        db_testing,
        usuario_id=empresa_b["usuario_id"],
        datos=datos_cliente(),
    )

    with pytest.raises(ClienteServiceError):
        obtener_cliente(
            db_testing,
            usuario_id=empresa_a["usuario_id"],
            cliente_id=cliente_b.id,
        )

    listado_a = listar_clientes(
        db_testing,
        usuario_id=empresa_a["usuario_id"],
    )

    assert listado_a["total"] == 0
    assert listado_a["clientes"] == []


def test_busqueda_por_nombre_y_documento(db_testing):
    escenario = preparar_escenario_clientes(db_testing)
    conceder_permiso_ver_clientes(db_testing, escenario)

    crear_clientes_para_consulta(
        db_testing,
        escenario,
        cantidad=3,
    )

    por_nombre = listar_clientes(
        db_testing,
        usuario_id=escenario["usuario_id"],
        busqueda="consulta 2",
    )

    assert por_nombre["total"] == 1
    assert por_nombre["clientes"][0].nombre == "Cliente Consulta 2"

    por_documento = listar_clientes(
        db_testing,
        usuario_id=escenario["usuario_id"],
        busqueda="00000003",
    )

    assert por_documento["total"] == 1
    assert por_documento["clientes"][0].numero_documento == "00000003"


def test_filtrado_por_estado_activo(db_testing):
    escenario = preparar_escenario_clientes(db_testing)
    conceder_permiso_ver_clientes(db_testing, escenario)

    clientes = crear_clientes_para_consulta(
        db_testing,
        escenario,
        cantidad=3,
    )

    cliente_inactivo_id = clientes[0].id

    cliente_inactivo = db_testing.get(
        Cliente,
        cliente_inactivo_id,
    )

    cliente_inactivo.activo = False
    db_testing.commit()

    activos = listar_clientes(
        db_testing,
        usuario_id=escenario["usuario_id"],
        activo=True,
    )

    inactivos = listar_clientes(
        db_testing,
        usuario_id=escenario["usuario_id"],
        activo=False,
    )

    assert activos["total"] == 2
    assert inactivos["total"] == 1
    assert inactivos["clientes"][0].id == cliente_inactivo_id


def test_paginacion_y_parametros_invalidos(db_testing):
    escenario = preparar_escenario_clientes(db_testing)
    conceder_permiso_ver_clientes(db_testing, escenario)

    crear_clientes_para_consulta(
        db_testing,
        escenario,
        cantidad=5,
    )

    pagina_1 = listar_clientes(
        db_testing,
        usuario_id=escenario["usuario_id"],
        pagina=1,
        limite=2,
    )

    pagina_2 = listar_clientes(
        db_testing,
        usuario_id=escenario["usuario_id"],
        pagina=2,
        limite=2,
    )

    assert pagina_1["total"] == 5
    assert pagina_2["total"] == 5

    assert len(pagina_1["clientes"]) == 2
    assert len(pagina_2["clientes"]) == 2

    ids_1 = [cliente.id for cliente in pagina_1["clientes"]]
    ids_2 = [cliente.id for cliente in pagina_2["clientes"]]

    assert ids_1 == sorted(ids_1)
    assert ids_2 == sorted(ids_2)
    assert set(ids_1).isdisjoint(ids_2)
    assert max(ids_1) < min(ids_2)

    with pytest.raises(ClienteServiceError):
        listar_clientes(
            db_testing,
            usuario_id=escenario["usuario_id"],
            pagina=0,
        )

    with pytest.raises(ClienteServiceError):
        listar_clientes(
            db_testing,
            usuario_id=escenario["usuario_id"],
            limite=101,
        )

# ==========================================================
# FASE 06-C.4
# PRUEBAS DE ACTUALIZACION EMPRESARIAL
# ==========================================================

from app.schemas.clientes import ClienteUpdate
from app.services.client_service import actualizar_cliente


def conceder_permiso_editar_clientes(db, escenario):
    permiso = db.scalar(
        select(Permiso).where(
            Permiso.codigo == "clientes.editar"
        )
    )

    if permiso is None:
        permiso = Permiso(
            codigo="clientes.editar",
            descripcion="Editar clientes empresariales",
        )
        db.add(permiso)
        db.flush()

    db.execute(
        roles_permisos.insert().values(
            rol_id=escenario["rol_id"],
            permiso_id=permiso.id,
        )
    )

    # Confirma solamente el savepoint de db_testing.
    db.commit()


def test_actualizacion_parcial_registra_auditoria(db_testing):
    escenario = preparar_escenario_clientes(db_testing)
    conceder_permiso_editar_clientes(db_testing, escenario)

    cliente = crear_cliente(
        db_testing,
        usuario_id=escenario["usuario_id"],
        datos=datos_cliente(),
    )

    resultado = actualizar_cliente(
        db_testing,
        usuario_id=escenario["usuario_id"],
        cliente_id=cliente.id,
        datos=ClienteUpdate(
            nombre="Cliente Actualizado",
            telefono="987654321",
        ),
    )

    assert resultado.nombre == "Cliente Actualizado"
    assert resultado.telefono == "987654321"

    # Los campos omitidos deben conservar su valor.
    assert resultado.numero_documento == "12345678"
    assert resultado.email == "cliente@example.com"

    auditorias = db_testing.scalars(
        select(Auditoria).where(
            Auditoria.empresa_id == escenario["empresa_id"],
            Auditoria.entidad == "clientes",
            Auditoria.entidad_id == cliente.id,
            Auditoria.accion == "ACTUALIZAR",
        )
    ).all()

    assert len(auditorias) == 1
    assert auditorias[0].datos_anteriores == {
        "nombre": "Cliente Empresarial Testing",
        "telefono": "999888777",
    }
    assert auditorias[0].datos_nuevos == {
        "nombre": "Cliente Actualizado",
        "telefono": "987654321",
    }


def test_actualizacion_exige_permiso_editar(db_testing):
    escenario = preparar_escenario_clientes(db_testing)

    cliente = crear_cliente(
        db_testing,
        usuario_id=escenario["usuario_id"],
        datos=datos_cliente(),
    )

    with pytest.raises(ClienteServiceError):
        actualizar_cliente(
            db_testing,
            usuario_id=escenario["usuario_id"],
            cliente_id=cliente.id,
            datos=ClienteUpdate(nombre="Nombre Prohibido"),
        )

    db_testing.expire_all()

    conservado = db_testing.get(Cliente, cliente.id)
    assert conservado.nombre == "Cliente Empresarial Testing"


def test_no_actualiza_cliente_de_otra_empresa(db_testing):
    empresa_a = preparar_escenario_clientes(db_testing)
    empresa_b = preparar_escenario_clientes(db_testing)

    conceder_permiso_editar_clientes(db_testing, empresa_a)

    cliente_b = crear_cliente(
        db_testing,
        usuario_id=empresa_b["usuario_id"],
        datos=datos_cliente(),
    )

    with pytest.raises(ClienteServiceError):
        actualizar_cliente(
            db_testing,
            usuario_id=empresa_a["usuario_id"],
            cliente_id=cliente_b.id,
            datos=ClienteUpdate(nombre="Cambio Externo"),
        )

    db_testing.expire_all()

    conservado = db_testing.get(Cliente, cliente_b.id)
    assert conservado.nombre == "Cliente Empresarial Testing"
    assert conservado.empresa_id == empresa_b["empresa_id"]


def test_actualizacion_rechaza_documento_duplicado(db_testing):
    escenario = preparar_escenario_clientes(db_testing)
    conceder_permiso_editar_clientes(db_testing, escenario)

    primero = crear_cliente(
        db_testing,
        usuario_id=escenario["usuario_id"],
        datos=datos_cliente(documento="12345678"),
    )

    segundo = crear_cliente(
        db_testing,
        usuario_id=escenario["usuario_id"],
        datos=datos_cliente(documento="87654321"),
    )

    with pytest.raises(
        ClienteServiceError,
        match="Ya existe otro cliente",
    ):
        actualizar_cliente(
            db_testing,
            usuario_id=escenario["usuario_id"],
            cliente_id=segundo.id,
            datos=ClienteUpdate(
                numero_documento=primero.numero_documento,
            ),
        )

    db_testing.expire_all()

    conservado = db_testing.get(Cliente, segundo.id)
    assert conservado.numero_documento == "87654321"


def test_actualizacion_rechaza_documento_incompleto(db_testing):
    escenario = preparar_escenario_clientes(db_testing)
    conceder_permiso_editar_clientes(db_testing, escenario)

    cliente = crear_cliente(
        db_testing,
        usuario_id=escenario["usuario_id"],
        datos=datos_cliente(),
    )

    with pytest.raises(ClienteServiceError):
        actualizar_cliente(
            db_testing,
            usuario_id=escenario["usuario_id"],
            cliente_id=cliente.id,
            datos=ClienteUpdate(numero_documento=None),
        )

    db_testing.expire_all()

    conservado = db_testing.get(Cliente, cliente.id)
    assert conservado.tipo_documento == "DNI"
    assert conservado.numero_documento == "12345678"


def test_fallo_auditoria_revierte_actualizacion(
    db_testing,
    monkeypatch,
):
    escenario = preparar_escenario_clientes(db_testing)
    conceder_permiso_editar_clientes(db_testing, escenario)

    cliente = crear_cliente(
        db_testing,
        usuario_id=escenario["usuario_id"],
        datos=datos_cliente(),
    )

    agregar_original = db_testing.add

    def simular_fallo(objeto):
        if (
            isinstance(objeto, Auditoria)
            and objeto.accion == "ACTUALIZAR"
            and objeto.entidad == "clientes"
        ):
            raise RuntimeError(
                "Fallo simulado de auditoria de actualizacion."
            )

        return agregar_original(objeto)

    monkeypatch.setattr(db_testing, "add", simular_fallo)

    with pytest.raises(
        RuntimeError,
        match="Fallo simulado de auditoria",
    ):
        actualizar_cliente(
            db_testing,
            usuario_id=escenario["usuario_id"],
            cliente_id=cliente.id,
            datos=ClienteUpdate(nombre="Cambio No Confirmado"),
        )

    db_testing.expire_all()

    conservado = db_testing.get(Cliente, cliente.id)
    assert conservado.nombre == "Cliente Empresarial Testing"

    cantidad_auditorias = db_testing.scalar(
        select(func.count(Auditoria.id)).where(
            Auditoria.empresa_id == escenario["empresa_id"],
            Auditoria.entidad == "clientes",
            Auditoria.entidad_id == cliente.id,
            Auditoria.accion == "ACTUALIZAR",
        )
    )

    assert cantidad_auditorias == 0


def test_actualizacion_sin_cambios_es_rechazada(db_testing):
    escenario = preparar_escenario_clientes(db_testing)
    conceder_permiso_editar_clientes(db_testing, escenario)

    cliente = crear_cliente(
        db_testing,
        usuario_id=escenario["usuario_id"],
        datos=datos_cliente(),
    )

    with pytest.raises(
        ClienteServiceError,
        match="No se detectaron modificaciones",
    ):
        actualizar_cliente(
            db_testing,
            usuario_id=escenario["usuario_id"],
            cliente_id=cliente.id,
            datos=ClienteUpdate(
                nombre="Cliente Empresarial Testing",
            ),
        )

    db_testing.expire_all()

    conservado = db_testing.get(Cliente, cliente.id)
    assert conservado.nombre == "Cliente Empresarial Testing"


# ==========================================================
# FASE 06-C.5A
# PRUEBAS DE BAJA LOGICA EMPRESARIAL
# ==========================================================

from app.services.client_service import desactivar_cliente


def test_desactivacion_cliente_registra_auditoria(db_testing):
    escenario = preparar_escenario_clientes(db_testing)
    conceder_permiso_editar_clientes(db_testing, escenario)

    cliente = crear_cliente(
        db_testing,
        usuario_id=escenario["usuario_id"],
        datos=datos_cliente(),
    )

    cliente_id = cliente.id

    resultado = desactivar_cliente(
        db_testing,
        usuario_id=escenario["usuario_id"],
        cliente_id=cliente_id,
    )

    assert resultado.id == cliente_id
    assert resultado.activo is False

    # Baja logica: el registro debe continuar existiendo.
    db_testing.expire_all()
    conservado = db_testing.get(Cliente, cliente_id)

    assert conservado is not None
    assert conservado.activo is False

    auditorias = db_testing.scalars(
        select(Auditoria).where(
            Auditoria.empresa_id == escenario["empresa_id"],
            Auditoria.entidad == "clientes",
            Auditoria.entidad_id == cliente_id,
            Auditoria.descripcion ==
            "Desactivacion empresarial de cliente.",
        )
    ).all()

    assert len(auditorias) == 1
    assert auditorias[0].accion == "ACTUALIZAR"
    assert auditorias[0].datos_anteriores == {"activo": True}
    assert auditorias[0].datos_nuevos == {"activo": False}


def test_no_permite_desactivar_dos_veces(db_testing):
    escenario = preparar_escenario_clientes(db_testing)
    conceder_permiso_editar_clientes(db_testing, escenario)

    cliente = crear_cliente(
        db_testing,
        usuario_id=escenario["usuario_id"],
        datos=datos_cliente(),
    )

    cliente_id = cliente.id

    desactivar_cliente(
        db_testing,
        usuario_id=escenario["usuario_id"],
        cliente_id=cliente_id,
    )

    with pytest.raises(
        ClienteServiceError,
        match="ya se encuentra inactivo",
    ):
        desactivar_cliente(
            db_testing,
            usuario_id=escenario["usuario_id"],
            cliente_id=cliente_id,
        )

    cantidad_auditorias = db_testing.scalar(
        select(func.count(Auditoria.id)).where(
            Auditoria.empresa_id == escenario["empresa_id"],
            Auditoria.entidad == "clientes",
            Auditoria.entidad_id == cliente_id,
            Auditoria.descripcion ==
            "Desactivacion empresarial de cliente.",
        )
    )

    assert cantidad_auditorias == 1
    assert db_testing.get(Cliente, cliente_id).activo is False


def test_desactivacion_exige_permiso_editar(db_testing):
    escenario = preparar_escenario_clientes(db_testing)

    cliente = crear_cliente(
        db_testing,
        usuario_id=escenario["usuario_id"],
        datos=datos_cliente(),
    )

    cliente_id = cliente.id

    with pytest.raises(ClienteServiceError):
        desactivar_cliente(
            db_testing,
            usuario_id=escenario["usuario_id"],
            cliente_id=cliente_id,
        )

    db_testing.expire_all()

    assert db_testing.get(Cliente, cliente_id).activo is True


def test_no_desactiva_cliente_de_otra_empresa(db_testing):
    empresa_a = preparar_escenario_clientes(db_testing)
    empresa_b = preparar_escenario_clientes(db_testing)

    conceder_permiso_editar_clientes(db_testing, empresa_a)

    cliente_b = crear_cliente(
        db_testing,
        usuario_id=empresa_b["usuario_id"],
        datos=datos_cliente(),
    )

    cliente_b_id = cliente_b.id

    with pytest.raises(ClienteServiceError):
        desactivar_cliente(
            db_testing,
            usuario_id=empresa_a["usuario_id"],
            cliente_id=cliente_b_id,
        )

    db_testing.expire_all()

    conservado = db_testing.get(Cliente, cliente_b_id)

    assert conservado.activo is True
    assert conservado.empresa_id == empresa_b["empresa_id"]


def test_fallo_auditoria_revierte_desactivacion(
    db_testing,
    monkeypatch,
):
    escenario = preparar_escenario_clientes(db_testing)
    conceder_permiso_editar_clientes(db_testing, escenario)

    cliente = crear_cliente(
        db_testing,
        usuario_id=escenario["usuario_id"],
        datos=datos_cliente(),
    )

    cliente_id = cliente.id
    agregar_original = db_testing.add

    def simular_fallo(objeto):
        if (
            isinstance(objeto, Auditoria)
            and objeto.descripcion ==
            "Desactivacion empresarial de cliente."
        ):
            raise RuntimeError(
                "Fallo simulado de auditoria de baja logica."
            )

        return agregar_original(objeto)

    monkeypatch.setattr(
        db_testing,
        "add",
        simular_fallo,
    )

    with pytest.raises(
        RuntimeError,
        match="Fallo simulado de auditoria",
    ):
        desactivar_cliente(
            db_testing,
            usuario_id=escenario["usuario_id"],
            cliente_id=cliente_id,
        )

    db_testing.expire_all()

    conservado = db_testing.get(Cliente, cliente_id)

    assert conservado is not None
    assert conservado.activo is True

    cantidad_auditorias = db_testing.scalar(
        select(func.count(Auditoria.id)).where(
            Auditoria.empresa_id == escenario["empresa_id"],
            Auditoria.entidad == "clientes",
            Auditoria.entidad_id == cliente_id,
            Auditoria.descripcion ==
            "Desactivacion empresarial de cliente.",
        )
    )

    assert cantidad_auditorias == 0
