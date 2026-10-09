
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes.auth import router as auth_router
from app.api.routes.usuarios import router as usuarios_router
from app.api.routes.roles import router as roles_router
from app.api.routes.clientes import router as clientes_router
from app.api.routes.categorias import router as categorias_router
from app.api.routes.productos import router as productos_router
from app.api.routes.pedidos import router as pedidos_router
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

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Backend empresarial SalesIA",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(usuarios_router)
app.include_router(roles_router)
app.include_router(clientes_router)
app.include_router(categorias_router)
app.include_router(productos_router)
app.include_router(pedidos_router)
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



