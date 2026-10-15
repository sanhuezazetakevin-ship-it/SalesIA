
from fastapi import FastAPI
from app.api.routes.alta_empresas import router as alta_empresas_router
from app.api.routes.plataforma_empresas import router as plataforma_empresas_router
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import settings
from app.api.routes.auth import router as auth_router
from app.api.routes.usuarios import router as usuarios_router
from app.api.routes.roles import router as roles_router
from app.api.routes.clientes import router as clientes_router
from app.api.routes.categorias import router as categorias_router
from app.api.routes.productos import router as productos_router
from app.api.routes.pedidos import router as pedidos_router
from app.api.routes.configuracion_tributaria import router as configuracion_tributaria_router
from app.core.openapi_contracts import instalar_openapi_contratos
from app.api.routes.ventas import router as ventas_router
from app.api.routes.pagos import router as pagos_router
from app.api.routes.entregas import router as entregas_router
from app.api.routes.proveedores import router as proveedores_router
from app.api.routes.ordenes_compra import router as ordenes_compra_router
from app.api.routes.recepciones_compra import router as recepciones_compra_router
from app.api.routes.pagos_proveedores import router as pagos_proveedores_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.analytics_distribuciones import router as analytics_distribuciones_router
from app.api.routes.analytics_probabilidades import router as analytics_probabilidades_router
from app.api.routes.analytics_historial import router as analytics_historial_router

from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.insights import router as insights_router
from app.api.routes.reportes import router as reportes_router
from app.api.routes.auditoria import router as auditoria_router
from app.api.routes.mejoras145 import router as mejoras145_router
from app.api.routes.semana08 import router as semana08_router
from app.api.routes.notificaciones145 import router as notificaciones145_router

from app.api.routes.inventario_operativo import router as inventario_operativo_router
from app.api.routes.vendedores_operativos import router as vendedores_operativos_router

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Backend empresarial SalesIA",
)

app.add_middleware(GZipMiddleware, minimum_size=1200)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(inventario_operativo_router)
app.include_router(vendedores_operativos_router)
app.include_router(auth_router)
app.include_router(alta_empresas_router)
app.include_router(plataforma_empresas_router)
app.include_router(usuarios_router)
app.include_router(roles_router)
app.include_router(clientes_router)
app.include_router(categorias_router)
app.include_router(productos_router)
app.include_router(pedidos_router)
app.include_router(configuracion_tributaria_router)
app.include_router(ventas_router)
app.include_router(pagos_router)
app.include_router(entregas_router)
instalar_openapi_contratos(app) 
app.include_router(proveedores_router)
app.include_router(ordenes_compra_router)
app.include_router(recepciones_compra_router)
app.include_router(pagos_proveedores_router)
app.include_router(analytics_router)
app.include_router(analytics_distribuciones_router)
app.include_router(analytics_probabilidades_router)
app.include_router(analytics_historial_router)
app.include_router(dashboard_router)
app.include_router(insights_router)
app.include_router(reportes_router)
app.include_router(auditoria_router)
app.include_router(mejoras145_router)
app.include_router(semana08_router)
app.include_router(notificaciones145_router)


@app.get("/")
def root():
    return {
        "sistema": settings.APP_NAME,
        "estado": "Backend funcionando",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Sistema"])
def health():
    return {
        "status": "ok",
        "service": "salesia-backend",
    }





@app.get("/ready", tags=["Sistema"])
def ready():
    """Comprueba acceso SQL; no publica detalles internos del servidor."""
    from fastapi import HTTPException
    from sqlalchemy import text
    from sqlalchemy.exc import SQLAlchemyError
    from app.database.connection import engine

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="database_unavailable") from exc
    return {"status": "ready", "database": "ok"}


@app.middleware("http")
async def cabeceras_seguridad(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cache-Control", "no-store")
    if settings.ENVIRONMENT == "production" and request.url.scheme == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    return response
