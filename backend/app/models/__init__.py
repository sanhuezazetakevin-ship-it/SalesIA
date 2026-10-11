
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.permiso import Permiso
from app.models.cliente import Cliente
from app.models.categoria import Categoria
from app.models.producto import Producto
from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario
from app.models.sesion import Sesion
from app.models.evento_auth import EventoAuth
from app.models.consentimiento_biometrico import ConsentimientoBiometrico
from app.models.registro_facial import RegistroFacial
from app.models.invitacion_usuario import InvitacionUsuario
from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle
from app.models.reserva_stock import ReservaStock
from app.models.venta import Venta
from app.models.venta_detalle import VentaDetalle
from app.models.pago import Pago
from app.models.entrega import Entrega
from app.models.configuracion_empresa import ConfiguracionEmpresa
from app.models.impuesto import Impuesto
from app.models.documento_facturacion import DocumentoFacturacion
from app.models.auditoria import Auditoria
from app.models.analisis_estadistico import AnalisisEstadistico
from app.models.analisis_probabilidad import AnalisisProbabilidad
from app.models.insight import Insight
from app.models.reporte_generado import ReporteGenerado







from app.models.asociaciones import (
    usuarios_roles,
    roles_permisos
)

# FASE 09-B: compras y proveedores
from app.models.proveedor import Proveedor
from app.models.orden_compra import OrdenCompra
from app.models.orden_compra_detalle import OrdenCompraDetalle
from app.models.recepcion_compra import RecepcionCompra
from app.models.recepcion_compra_detalle import RecepcionCompraDetalle
from app.models.pago_proveedor import PagoProveedor

from app.models.notificacion_empresarial import NotificacionEmpresarial
