
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes.auth import router as auth_router
from app.api.routes.usuarios import router as usuarios_router
from app.api.routes.roles import router as roles_router
from app.api.routes.clientes import router as clientes_router
from app.api.routes.categorias import router as categorias_router
from app.api.routes.productos import router as productos_router

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
