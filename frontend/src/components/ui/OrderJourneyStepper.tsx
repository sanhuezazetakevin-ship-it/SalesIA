import React from 'react';
import { 
  FileText, 
  CheckCircle2, 
  Receipt, 
  CreditCard, 
  Truck, 
  XCircle,
  AlertCircle
} from 'lucide-react';

export interface OrderJourneyStepperProps {
  tipo: 'pedido' | 'venta';
  estadoPedido?: string | null;
  estadoVenta?: string | null;
  estadoPago?: string | null;
  estadoEntrega?: string | null;
  codigo?: string;
  fecha?: string;
  className?: string;
}

type StepStatus = 'completed' | 'current' | 'pending' | 'cancelled' | 'warning';

interface Step {
  id: string;
  label: string;
  sublabel: string;
  icon: React.ElementType;
  status: StepStatus;
  badgeText?: string;
}

export const OrderJourneyStepper: React.FC<OrderJourneyStepperProps> = ({
  tipo,
  estadoPedido,
  estadoVenta,
  estadoPago,
  estadoEntrega,
  className = '',
}) => {
  // Normalizar strings
  const ep = (estadoPedido || '').toUpperCase().trim();
  const ev = (estadoVenta || '').toUpperCase().trim();
  const eg = (estadoPago || '').toUpperCase().trim();
  const ee = (estadoEntrega || '').toUpperCase().trim();

  const esCancelado = ep === 'CANCELADO' || ev === 'ANULADA' || ee === 'CANCELADO';

  // 1. Registro / Borrador
  const step1Status: StepStatus = 'completed';

  // 2. Reserva / Confirmación
  let step2Status: StepStatus = 'pending';
  let step2Badge: string | undefined = undefined;
  if (esCancelado && ep === 'CANCELADO') {
    step2Status = 'cancelled';
    step2Badge = 'Cancelado';
  } else if (tipo === 'venta' || ep === 'CONFIRMADO') {
    step2Status = 'completed';
    step2Badge = 'Confirmado';
  } else if (ep === 'BORRADOR') {
    step2Status = 'current';
    step2Badge = 'En Borrador';
  } else {
    step2Status = 'completed';
  }

  // 3. Facturación / Venta Formalizada
  let step3Status: StepStatus = 'pending';
  let step3Badge: string | undefined = undefined;
  if (esCancelado && ev === 'ANULADA') {
    step3Status = 'cancelled';
    step3Badge = 'Anulada';
  } else if (tipo === 'venta' || ev === 'EMITIDA' || ev === 'COMPLETADO') {
    step3Status = 'completed';
    step3Badge = 'Emitida';
  } else if (step2Status === 'completed' && ep === 'CONFIRMADO') {
    step3Status = 'current';
    step3Badge = 'Listo p/ Venta';
  }

  // 4. Cobranza Validada
  let step4Status: StepStatus = 'pending';
  let step4Badge: string | undefined = undefined;
  if (eg === 'PAGADO' || eg === 'COMPLETADO' || eg === 'COBRADO') {
    step4Status = 'completed';
    step4Badge = '100% Pagado';
  } else if (eg === 'PARCIAL' || eg === 'PAGO_PARCIAL') {
    step4Status = 'warning';
    step4Badge = 'Pago Parcial';
  } else if (step3Status === 'completed' || tipo === 'venta') {
    step4Status = 'current';
    step4Badge = 'Pendiente Pago';
  }

  // 5. Despacho / Logística
  let step5Status: StepStatus = 'pending';
  let step5Badge: string | undefined = undefined;
  if (ee === 'ENTREGADO' || ee === 'COMPLETADO') {
    step5Status = 'completed';
    step5Badge = 'Entregado';
  } else if (ee === 'EN_RUTA' || ee === 'DESPACHADO' || ee === 'EN_CAMINO') {
    step5Status = 'current';
    step5Badge = 'En Tránsito';
  } else if (step3Status === 'completed' && step4Status === 'completed') {
    step5Status = 'current';
    step5Badge = 'Listo p/ Despacho';
  } else if (ee === 'CANCELADO') {
    step5Status = 'cancelled';
    step5Badge = 'No entregado';
  }

  const steps: Step[] = [
    {
      id: 'registro',
      label: '1. Pedido Registrado',
      sublabel: 'Captura comercial',
      icon: FileText,
      status: step1Status,
      badgeText: 'Creado',
    },
    {
      id: 'reserva',
      label: '2. Reserva Stock',
      sublabel: 'Aprobación interna',
      icon: CheckCircle2,
      status: step2Status,
      badgeText: step2Badge,
    },
    {
      id: 'venta',
      label: '3. Facturación',
      sublabel: 'Comprobante formal',
      icon: Receipt,
      status: step3Status,
      badgeText: step3Badge,
    },
    {
      id: 'pago',
      label: '4. Cobranza',
      sublabel: 'Validación en caja',
      icon: CreditCard,
      status: step4Status,
      badgeText: step4Badge,
    },
    {
      id: 'entrega',
      label: '5. Entrega Final',
      sublabel: 'Salida de almacén',
      icon: Truck,
      status: step5Status,
      badgeText: step5Badge,
    },
  ];

  const getStatusStyles = (status: StepStatus) => {
    switch (status) {
      case 'completed':
        return {
          circle: 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/30 border-emerald-400',
          line: 'bg-emerald-500',
          text: 'text-emerald-400 font-semibold',
          badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
        };
      case 'current':
        return {
          circle: 'bg-cyan-500 text-white shadow-lg shadow-cyan-500/40 ring-4 ring-cyan-500/20 animate-pulse border-cyan-300',
          line: 'bg-gray-300 dark:bg-white/10',
          text: 'text-cyan-400 font-bold',
          badge: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
        };
      case 'warning':
        return {
          circle: 'bg-amber-500 text-white shadow-lg shadow-amber-500/30 border-amber-400',
          line: 'bg-gray-300 dark:bg-white/10',
          text: 'text-amber-400 font-semibold',
          badge: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
        };
      case 'cancelled':
        return {
          circle: 'bg-rose-500 text-white shadow-lg shadow-rose-500/30 border-rose-400',
          line: 'bg-rose-500/40',
          text: 'text-rose-400 font-semibold',
          badge: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
        };
      case 'pending':
      default:
        return {
          circle: 'bg-gray-100 dark:bg-white/5 text-gray-400 dark:text-gray-500 border-gray-300 dark:border-white/10',
          line: 'bg-gray-200 dark:bg-white/5',
          text: 'text-gray-400 dark:text-gray-500',
          badge: 'bg-gray-500/10 text-gray-400 border-transparent',
        };
    }
  };

  return (
    <div className={`p-4 rounded-xl bg-slate-900/60 border border-cyan-500/20 backdrop-blur-md shadow-inner ${className}`}>
      <div className="flex items-center justify-between mb-3 pb-2 border-b border-white/5">
        <span className="text-xs font-semibold uppercase tracking-wider text-cyan-400 flex items-center gap-1.5">
          <Truck className="w-3.5 h-3.5" />
          Trazabilidad de la Operación (Order Journey)
        </span>
        <span className="text-[11px] text-gray-400">
          {tipo === 'pedido' ? 'Ciclo desde Pedido' : 'Ciclo de Venta Directa'}
        </span>
      </div>

      <div className="relative flex items-start justify-between w-full">
        {steps.map((step, idx) => {
          const style = getStatusStyles(step.status);
          const Icon = step.icon;
          const isLast = idx === steps.length - 1;

          return (
            <div key={step.id} className="flex-1 relative flex flex-col items-center group">
              {/* Línea conectora hacia el siguiente */}
              {!isLast && (
                <div
                  className={`absolute top-4 left-1/2 w-full h-[2px] -z-0 transition-all duration-500 ${
                    step.status === 'completed' ? 'bg-emerald-500' : 'bg-gray-300 dark:bg-white/10'
                  }`}
                  style={{ transform: 'translateY(-50%)' }}
                />
              )}

              {/* Icono circular del paso */}
              <div
                className={`relative z-10 w-8 h-8 rounded-full border flex items-center justify-center transition-transform group-hover:scale-110 ${style.circle}`}
              >
                {step.status === 'completed' ? (
                  <CheckCircle2 className="w-4 h-4 stroke-[2.5]" />
                ) : step.status === 'cancelled' ? (
                  <XCircle className="w-4 h-4 stroke-[2.5]" />
                ) : step.status === 'warning' ? (
                  <AlertCircle className="w-4 h-4 stroke-[2.5]" />
                ) : (
                  <Icon className="w-4 h-4 stroke-[2]" />
                )}
              </div>

              {/* Textos del paso */}
              <div className="text-center mt-2 px-1 max-w-[110px]">
                <p className={`text-xs leading-tight ${style.text}`}>
                  {step.label}
                </p>
                <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-0.5 hidden sm:block">
                  {step.sublabel}
                </p>
                {step.badgeText && (
                  <span
                    className={`inline-block mt-1 text-[9px] px-1.5 py-0.5 rounded font-mono border ${style.badge}`}
                  >
                    {step.badgeText}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
export default OrderJourneyStepper;
