"""
Script para inicializar el entorno local de SalesIA con datos de prueba:
- Empresa Demo
- Catálogo de permisos y roles (ADMINISTRADOR, GERENTE, VENDEDOR, ANALISTA, ALMACEN)
- Usuario administrador: admin@salesia.com / admin123456
- Clientes, productos y ventas de prueba
"""
from datetime import datetime, timezone
from decimal import Decimal

from app.database.connection import SessionLocal
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.cliente import Cliente
from app.models.producto import Producto
from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle
from app.models.venta import Venta
from app.models.venta_detalle import VentaDetalle
from app.models.pago import Pago
from app.core.security import hash_password
from scripts.seed_roles_permisos import ejecutar_seed


def inicializar():
    with SessionLocal() as db:
        # 1. Crear Empresa
        empresa = db.query(Empresa).filter_by(id=1).first()
        if not empresa:
            empresa = Empresa(
                id=1,
                razon_social="SalesIA Enterprise Demo S.A.C.",
                ruc="20601234567",
                moneda_base="PEN",
                activo=True
            )
            db.add(empresa)
            db.commit()
            print("Empresa creada: SalesIA Enterprise Demo S.A.C. (ID: 1)")
        else:
            print("Empresa ya existe (ID: 1)")

    # 2. Poblar Roles y Permisos para empresa 1
    ejecutar_seed(empresa_id=1, aplicar=True, session_factory=SessionLocal)

    with SessionLocal() as db:
        # 3. Crear Usuario Admin
        admin = db.query(Usuario).filter_by(email="admin@salesia.com").first()
        if not admin:
            admin = Usuario(
                empresa_id=1,
                nombre="Administrador SalesIA",
                email="admin@salesia.com",
                password_hash=hash_password("admin123456"),
                activo=True
            )
            db.add(admin)
            db.flush()

            rol_admin = db.query(Rol).filter_by(empresa_id=1, nombre="ADMINISTRADOR").first()
            if rol_admin:
                admin.roles.append(rol_admin)

            db.commit()
            print("Usuario administrador creado: admin@salesia.com (Clave: admin123456)")
        else:
            print("Usuario admin@salesia.com ya existe.")

        # 4. Datos de prueba: Clientes
        cliente = db.query(Cliente).filter_by(empresa_id=1).first()
        if not cliente:
            cliente1 = Cliente(
                empresa_id=1,
                nombre="Corporación Lima Tech S.A.",
                tipo_documento="RUC",
                numero_documento="20556789012",
                email="contacto@limatech.com",
                telefono="998877665",
                direccion="Av. Javier Prado 1234, San Isidro",
                activo=True
            )
            cliente2 = Cliente(
                empresa_id=1,
                nombre="Juan Pérez Gonzales",
                tipo_documento="DNI",
                numero_documento="45678901",
                email="juan.perez@gmail.com",
                telefono="987654321",
                direccion="Calle Las Flores 456, Miraflores",
                activo=True
            )
            db.add_all([cliente1, cliente2])
            db.flush()
            print("Clientes de prueba creados.")

        # 5. Datos de prueba: Productos
        producto = db.query(Producto).filter_by(empresa_id=1).first()
        if not producto:
            prod1 = Producto(
                empresa_id=1,
                sku="PROD-001",
                nombre="Laptop Corporativa Dell 15",
                tipo_item="PRODUCTO",
                precio_venta=Decimal("3500.00"),
                costo_referencia=Decimal("2800.00"),
                controla_stock=True,
                activo=True
            )
            prod2 = Producto(
                empresa_id=1,
                sku="PROD-002",
                nombre="Monitor IPS 27 4K",
                tipo_item="PRODUCTO",
                precio_venta=Decimal("1200.00"),
                costo_referencia=Decimal("950.00"),
                controla_stock=True,
                activo=True
            )
            prod3 = Producto(
                empresa_id=1,
                sku="PROD-003",
                nombre="Teclado Mecánico Ergonómico",
                tipo_item="PRODUCTO",
                precio_venta=Decimal("250.00"),
                costo_referencia=Decimal("180.00"),
                controla_stock=True,
                activo=True
            )
            db.add_all([prod1, prod2, prod3])
            db.flush()
            print("Productos de prueba creados.")

        # 6. Datos de prueba: Ventas confirmadas para Analytics y Dashboard
        venta = db.query(Venta).filter_by(empresa_id=1).first()
        if not venta and admin:
            c1 = db.query(Cliente).filter_by(empresa_id=1).first()
            p1 = db.query(Producto).filter_by(empresa_id=1).first()

            v1 = Venta(
                empresa_id=1,
                usuario_id=admin.id,
                cliente_id=c1.id if c1 else None,
                codigo="V-2026-0001",
                estado="CONFIRMADA",
                estado_pago="PAGADO",
                subtotal=Decimal("3500.00"),
                impuesto_total=Decimal("0.00"),
                total=Decimal("3500.00"),
                created_at=datetime.now(timezone.utc)
            )
            v2 = Venta(
                empresa_id=1,
                usuario_id=admin.id,
                cliente_id=c1.id if c1 else None,
                codigo="V-2026-0002",
                estado="CONFIRMADA",
                estado_pago="PAGADO",
                subtotal=Decimal("1450.00"),
                impuesto_total=Decimal("0.00"),
                total=Decimal("1450.00"),
                created_at=datetime.now(timezone.utc)
            )
            v3 = Venta(
                empresa_id=1,
                usuario_id=admin.id,
                cliente_id=c1.id if c1 else None,
                codigo="V-2026-0003",
                estado="CONFIRMADA",
                estado_pago="PENDIENTE",
                subtotal=Decimal("500.00"),
                impuesto_total=Decimal("0.00"),
                total=Decimal("500.00"),
                created_at=datetime.now(timezone.utc)
            )
            db.add_all([v1, v2, v3])
            db.flush()

            # Detalle y pagos
            pago1 = Pago(
                empresa_id=1,
                venta_id=v1.id,
                registrado_por_id=admin.id,
                codigo="PAG-0001",
                monto=Decimal("3500.00"),
                medio_pago="TRANSFERENCIA",
                estado="REGISTRADO"
            )
            pago2 = Pago(
                empresa_id=1,
                venta_id=v2.id,
                registrado_por_id=admin.id,
                codigo="PAG-0002",
                monto=Decimal("1450.00"),
                medio_pago="TARJETA",
                estado="REGISTRADO"
            )
            db.add_all([pago1, pago2])
            db.commit()
            print("Ventas y pagos de prueba registrados exitosamente.")
        else:
            db.commit()


if __name__ == "__main__":
    inicializar()
