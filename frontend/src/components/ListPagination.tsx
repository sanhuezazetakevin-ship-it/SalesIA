import React, { useEffect, useMemo, useState } from 'react';

type Props<T> = {
  items: T[];
  renderItem: (item: T, index: number) => React.ReactNode;
  getKey: (item: T, index: number) => React.Key;
  title?: string;
  pageSize?: number;
  sourceLimit?: number;
  emptyText?: string;
};

/** Paginación reutilizable de los registros recibidos. No finge paginación del servidor. */
export function ListPagination<T>({items,renderItem,getKey,title,pageSize=10,sourceLimit,emptyText='No hay registros para mostrar.'}:Props<T>) {
  const [page,setPage] = useState(1);
  const [limit,setLimit] = useState(pageSize);
  const pages = Math.max(1,Math.ceil(items.length/limit));
  useEffect(()=>setPage(1),[items,limit]);
  const safePage = Math.min(page,pages);
  const visible = useMemo(()=>items.slice((safePage-1)*limit,safePage*limit),[items,safePage,limit]);
  return <div className="list-pagination">
    {items.length===0 ? <div className="empty-state">{emptyText}</div> : visible.map((item,i)=><React.Fragment key={getKey(item,(safePage-1)*limit+i)}>{renderItem(item,(safePage-1)*limit+i)}</React.Fragment>)}
    <div className="list-pagination-footer">
      <span>{title ? `${title}: `:''}{items.length ? `${(safePage-1)*limit+1}–${Math.min(safePage*limit,items.length)} de ${items.length}`:'0 registros'}{sourceLimit && items.length>=sourceLimit?' (muestra recibida del servidor)':''}</span>
      <label>Por página <select aria-label="Registros por página" value={limit} onChange={e=>setLimit(Number(e.target.value))}><option value={5}>5</option><option value={10}>10</option><option value={25}>25</option><option value={50}>50</option></select></label>
      <button type="button" onClick={()=>setPage(1)} disabled={safePage===1}>Primera</button>
      <button type="button" onClick={()=>setPage(v=>Math.max(1,v-1))} disabled={safePage===1}>Anterior</button>
      <span>Página {safePage} de {pages}</span>
      <button type="button" onClick={()=>setPage(v=>Math.min(pages,v+1))} disabled={safePage>=pages}>Siguiente</button>
      <button type="button" onClick={()=>setPage(pages)} disabled={safePage>=pages}>Última</button>
    </div>
  </div>;
}
