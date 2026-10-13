export interface CatalogItem { id:number; empresa_id:number; nombre:string; activo:boolean; [key:string]:unknown }
export interface PedidoResumen { id:number; codigo:string; cliente_id:number; estado:string; total:string; [key:string]:unknown }
export interface VentaResumen { id:number; codigo:string; pedido_id:number|null; cliente_id:number; estado:string; estado_pago:string; total:string; [key:string]:unknown }
export interface ResumenPagos { venta_id:number; total_venta:string; total_pagado:string; saldo_pendiente:string; estado_pago:string; pagos:{id:number;codigo:string;monto:string;estado:string;medio_pago:string}[] }
export interface EntregaResumen { id:number;venta_id:number;codigo:string;estado:string;movimientos:unknown[] }
