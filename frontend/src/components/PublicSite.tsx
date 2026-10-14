import React, { useState } from 'react';

type Page = 'inicio' | 'login' | 'empresa' | 'invitacion';
interface Props { page: Page; navigate: (page: Page) => void; theme: 'light' | 'dark'; toggleTheme: () => void; children?: React.ReactNode }
const features = [
 {icon:'▥',title:'Visibilidad comercial',desc:'Indicadores de ventas, evolución temporal y desempeño en una sola vista.'},
 {icon:'▣',title:'Operación conectada',desc:'Clientes, productos, pedidos, pagos, inventario y proveedores.'},
 {icon:'✦',title:'Análisis inteligente',desc:'Estadística, segmentación comercial e insights basados en datos.'},
 {icon:'▧',title:'Reportes ejecutivos',desc:'Informes y exportaciones para interpretar resultados de negocio.'},
 {icon:'♢',title:'Empresas independientes',desc:'Separación de información empresarial mediante permisos y controles de acceso.'},
 {icon:'◈',title:'Trazabilidad',desc:'Historial de actividades, roles y registro de operaciones críticas.'},
];
export const PublicSite: React.FC<Props> = ({page,navigate,theme,toggleTheme,children}) => <div className="public-shell">
  <header className="public-nav"><button className="public-logo" onClick={()=>navigate('inicio')}><span className="public-logo-mark">S</span><span><b>SalesIA</b><small>ENTERPRISE</small></span></button>
    <nav aria-label="Navegación pública"><button onClick={()=>navigate('inicio')}>Inicio</button><button onClick={()=>navigate('empresa')}>Registrar empresa</button><button className="public-theme" onClick={toggleTheme} aria-label="Cambiar tema">{theme==='light'?'☾':'☀'}</button><button className="public-login" onClick={()=>navigate('login')}>Iniciar sesión <span>↗</span></button></nav>
  </header>
  {page==='inicio' ? <>
    <section className="public-hero"><div className="public-hero-copy"><span className="public-eyebrow"><span className="public-green-dot"/> SOFTWARE DE GESTIÓN EMPRESARIAL</span><h1>Controla tus operaciones.<br/><em>Decide con datos.</em></h1><p>Conecta ventas, inventario, clientes y análisis comercial en una plataforma diseñada para dar claridad a tu negocio.</p><div className="public-actions"><button className="public-cta" onClick={()=>navigate('empresa')}>Registrar mi empresa <span>→</span></button><button className="public-alt" onClick={()=>navigate('login')}>Ya tengo una cuenta</button></div><div className="public-trust"><span>✓ Gestión multiempresa</span><span>✓ Accesos por rol</span><span>✓ Analítica integrada</span></div></div>
      <div className="public-visual" aria-label="Vista ilustrativa de análisis"><div className="preview-top"><span>◉ &nbsp; SALESIA / ANALÍTICA</span><span className="preview-tag">Resumen general</span></div><div className="preview-metric"><div><small>Visión comercial</small><strong>Decisiones informadas</strong><span>Visualiza el movimiento de tu negocio</span></div><div className="preview-arrow">↗</div></div><div className="preview-bars" aria-hidden="true">{[40,53,47,72,62,80,76,94,85,99].map((n,i)=><div key={i} style={{height:`${n}%`}} />)}</div><div className="preview-bottom"><span>VENTAS</span><span>INVENTARIO</span><span>CLIENTES</span></div></div>
    </section>
    <section className="public-feature-section" id="funciones"><div className="public-section-intro"><span className="public-eyebrow">UNA PLATAFORMA, MÁS CONTROL</span><h2>Lo que necesitas para gestionar mejor</h2><p>Herramientas conectadas para organizar el trabajo diario y convertir la información en oportunidades.</p></div><div className="public-feature-grid">{features.map(f=><article key={f.title} className="public-feature"><div className="public-feature-icon">{f.icon}</div><h3>{f.title}</h3><p>{f.desc}</p></article>)}</div></section>
    <section className="public-bottom-cta"><div><h2>Tu empresa, tu información, tus decisiones.</h2><p>Solicita el registro de tu organización y comienza el proceso de incorporación.</p></div><button onClick={()=>navigate('empresa')}>Solicitar incorporación →</button></section>
  </> : <section className="public-auth-layout"><div className="public-auth-aside"><span className="public-eyebrow">SALESIA ENTERPRISE</span><h2>{page==='login'?'Bienvenido de nuevo.':page==='empresa'?'Da el primer paso hacia una gestión más clara.':'Tu invitación empresarial.'}</h2><p>Una plataforma con operaciones conectadas, información organizada y análisis para decisiones comerciales.</p><div className="public-auth-mini">▦ <span>Ventas · Inventario · Analítica · Reportes</span></div></div><div className="public-auth-panel">{children}</div></section>}
  <footer className="public-footer"><span>© {new Date().getFullYear()} SalesIA Enterprise</span><span>Plataforma de gestión empresarial · Versión de demostración</span></footer>
</div>;

export const CompanyRegistration: React.FC<{goLogin:()=>void}> = ({goLogin}) => {
 const [form,setForm]=useState({razon_social:'',ruc:'',nombre_contacto:'',email_contacto:'',telefono:'',sitio_web:''});
 const [loading,setLoading]=useState(false); const [error,setError]=useState(''); const [done,setDone]=useState(false);
 const update=(key:keyof typeof form,value:string)=>setForm(s=>({...s,[key]:value}));
 const submit=async(e:React.FormEvent)=>{e.preventDefault();setError('');setLoading(true);try{
   const base=import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
   const response=await fetch(`${base}/api/publico/solicitudes-empresa`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(form)});
   if(!response.ok){const json=await response.json().catch(()=>({}));throw new Error(typeof json.detail==='string'?json.detail:'No fue posible enviar la solicitud. Verifica los datos.');}
   setDone(true);
 }catch(err){setError(err instanceof Error?err.message:'Error de conexión');}finally{setLoading(false);}};
 if(done)return <div className="public-form-card public-success" role="status"><div className="public-success-icon">✓</div><h2>Solicitud recibida</h2><p>El registro de tu empresa está <b>pendiente de revisión</b>. No se crea una sesión ni una cuenta administradora automáticamente.</p><p>El responsable de SalesIA deberá confirmar el alta y comunicarte los siguientes pasos.</p><button className="public-cta" onClick={goLogin}>Ir a iniciar sesión →</button></div>;
 return <div className="public-form-card"><span className="public-form-kicker">ALTA DE ORGANIZACIÓN</span><h2>Registra tu empresa</h2><p>Envíanos los datos de tu organización para revisar su incorporación a SalesIA.</p><form onSubmit={submit} className="public-registration-form">
 <label>Razón social<input required maxLength={200} minLength={3} value={form.razon_social} onChange={e=>update('razon_social',e.target.value)} placeholder="Nombre legal de la empresa"/></label>
 <div className="public-form-grid"><label>RUC (11 dígitos)<input required inputMode="numeric" pattern="[0-9]{11}" maxLength={11} value={form.ruc} onChange={e=>update('ruc',e.target.value.replace(/\D/g,''))} placeholder="20XXXXXXXXX"/></label><label>Teléfono (opcional)<input maxLength={25} value={form.telefono} onChange={e=>update('telefono',e.target.value)} placeholder="Teléfono de contacto"/></label></div>
 <label>Responsable de la solicitud<input required minLength={2} maxLength={120} value={form.nombre_contacto} onChange={e=>update('nombre_contacto',e.target.value)} placeholder="Nombre y apellido"/></label>
 <label>Correo corporativo<input required type="email" value={form.email_contacto} onChange={e=>update('email_contacto',e.target.value)} placeholder="contacto@empresa.com"/></label>
 <div className="public-honeypot" aria-hidden="true"><label>Sitio web<input tabIndex={-1} autoComplete="off" value={form.sitio_web} onChange={e=>update('sitio_web',e.target.value)}/></label></div>
 {error&&<div className="alert alert-error" role="alert">{error}</div>}
 <p className="public-privacy">El envío constituye una solicitud de evaluación. No habilita acceso automático. No ingreses contraseñas en este formulario.</p>
 <button className="public-cta public-wide" disabled={loading}>{loading?'Enviando solicitud…':'Solicitar registro empresarial →'}</button>
 </form><div className="public-form-bottom">¿Ya tienes una cuenta? <button onClick={goLogin}>Inicia sesión</button></div></div>;
};
