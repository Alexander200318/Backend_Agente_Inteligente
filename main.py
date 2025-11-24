from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from contextlib import asynccontextmanager
from dotenv import load_dotenv  # 🔥 AGREGAR

# 🔥 Cargar variables de entorno ANTES de importar settings
load_dotenv()
from core.config import settings
from database.init_db import init_db
from exceptions.base import BaseAPIException

# Lifespan para inicializar DB al arrancar
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"🚀 Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    init_db()
    yield
    # Shutdown
    print("👋 Cerrando aplicación...")

# Crear aplicación
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API REST para sistema multi-agente de chatbot institucional",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# ==================== MIDDLEWARE ====================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== EXCEPTION HANDLERS ====================

@app.exception_handler(BaseAPIException)
async def base_exception_handler(request: Request, exc: BaseAPIException):
    """Manejo de excepciones personalizadas"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "path": str(request.url)
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Manejo de errores de validación de Pydantic"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "message": "Error de validación",
            "details": errors
        }
    )

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Manejo de errores de base de datos"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": "Error en la base de datos",
            "details": str(exc) if settings.DEBUG else "Contacte al administrador"
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Manejo de errores generales"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": "Error interno del servidor",
            "details": str(exc) if settings.DEBUG else "Contacte al administrador"
        }
    )

# ==================== ROUTERS ====================

# Importar routers
from routers import (
    usuario_router,
    departamento_router,
    rol_router,
    usuario_agente_router,
    departamento_agente_router,
    categoria_router,
    unidad_contenido_router,
    metrica_diaria_agente_router,
    metrica_contenido_router,
    agente_virtual_router,
    visitante_anonimo_router,
    conversacion_sync_router,
    chat_router,
    chat_auto_router,
    agentes_router,
    embeddings_router,
    persona_router
)

# Incluir routers
app.include_router(usuario_router.router, prefix="/api/v1")
app.include_router(departamento_router.router, prefix="/api/v1")
app.include_router(rol_router.router, prefix="/api/v1")
app.include_router(usuario_agente_router.router, prefix="/api/v1")
app.include_router(departamento_agente_router.router, prefix="/api/v1")
app.include_router(categoria_router.router, prefix="/api/v1")
app.include_router(unidad_contenido_router.router, prefix="/api/v1")
app.include_router(metrica_diaria_agente_router.router, prefix="/api/v1")
app.include_router(metrica_contenido_router.router, prefix="/api/v1")
app.include_router(agente_virtual_router.router, prefix="/api/v1")
app.include_router(visitante_anonimo_router.router, prefix="/api/v1")
app.include_router(conversacion_sync_router.router, prefix="/api/v1")
app.include_router(chat_router.router, prefix="/api/v1")
app.include_router(chat_auto_router.router, prefix="/api/v1")
app.include_router(agentes_router.router, prefix="/api/v1")
app.include_router(embeddings_router.router, prefix="/api/v1")
app.include_router(persona_router.router, prefix="/api/v1")

# ==================== HEALTH CHECK ====================

@app.get("/", tags=["Health"])
def root():
    """Endpoint raíz"""
    return {
        "message": f"Bienvenido a {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health", tags=["Health"])
def health_check():
    """Verificar estado de la aplicación"""
    return {
        "status": "healthy",
        "database": "connected"
    }

# ==================== EJECUCIÓN ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )