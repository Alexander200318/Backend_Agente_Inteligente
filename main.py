from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles  # 🔥 AGREGAR ESTA IMPORTACIÓN
from sqlalchemy.exc import SQLAlchemyError
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# 🔥 Cargar variables de entorno ANTES de importar settings
load_dotenv()

from core.config import settings
from database.init_db import init_db
from exceptions.base import BaseAPIException

# ==================== LIFESPAN ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manejo del ciclo de vida de la aplicación"""
    # Startup
    print("=" * 60)
    print(f"🚀 Iniciando {settings.APP_NAME}")
    print(f"📦 Versión: {settings.APP_VERSION}")
    print(f"🔧 Modo DEBUG: {settings.DEBUG}")
    print(f"💾 Base de datos: {settings.DB_NAME}")
    print(f"🤖 Modelo Ollama: {settings.OLLAMA_MODEL}")
    print("=" * 60)
    
    # Inicializar base de datos
    init_db()
    
    yield
    
    # Shutdown
    print("👋 Cerrando aplicación...")

# ==================== CREAR APLICACIÓN ====================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API REST para sistema multi-agente de chatbot institucional con IA",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    debug=settings.DEBUG
)

# ==================== ARCHIVOS ESTÁTICOS ====================

# Montar archivos estáticos (CSS, JS, imágenes)
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    print("✅ Archivos estáticos montados en /static")
except Exception as e:
    print(f"⚠️  Advertencia: No se pudieron montar archivos estáticos: {e}")
    print("   Asegúrate de que la carpeta 'static' existe")

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
    persona_router,
    widget_router,
    usuario_rol_router  # 🔥 Router del widget
)

# Incluir routers de API con prefix /api/v1
app.include_router(usuario_router.router, prefix="/api/v1", tags=["Usuarios"])
app.include_router(departamento_router.router, prefix="/api/v1", tags=["Departamentos"])
app.include_router(rol_router.router, prefix="/api/v1", tags=["Roles"])
app.include_router(usuario_agente_router.router, prefix="/api/v1", tags=["Usuario-Agente"])
app.include_router(departamento_agente_router.router, prefix="/api/v1", tags=["Departamento-Agente"])
app.include_router(categoria_router.router, prefix="/api/v1", tags=["Categorías"])
app.include_router(unidad_contenido_router.router, prefix="/api/v1", tags=["Contenido"])
app.include_router(metrica_diaria_agente_router.router, prefix="/api/v1", tags=["Métricas Agente"])
app.include_router(metrica_contenido_router.router, prefix="/api/v1", tags=["Métricas Contenido"])
app.include_router(agente_virtual_router.router, prefix="/api/v1", tags=["Agentes Virtuales"])
app.include_router(visitante_anonimo_router.router, prefix="/api/v1", tags=["Visitantes"])
app.include_router(conversacion_sync_router.router, prefix="/api/v1", tags=["Conversaciones"])
app.include_router(chat_router.router, prefix="/api/v1", tags=["Chat"])
app.include_router(chat_auto_router.router, prefix="/api/v1", tags=["Chat Auto"])
app.include_router(agentes_router.router, prefix="/api/v1", tags=["Gestión Agentes"])
app.include_router(embeddings_router.router, prefix="/api/v1", tags=["Embeddings"])
app.include_router(persona_router.router, prefix="/api/v1", tags=["Personas"])
app.include_router(usuario_rol_router.router, prefix="/api/v1", tags=["Rol-Usuario"])

# Incluir router del widget SIN prefix (acceso directo a /widget y /admin)
app.include_router(widget_router.router, tags=["Widget"])

# ==================== HEALTH CHECK ====================

@app.get("/", tags=["Health"])
def root():
    """Endpoint raíz con información del sistema"""
    return {
        "message": f"Bienvenido a {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "widget": "/widget",
            "admin": "/admin",
            "health": "/health"
        }
    }

@app.get("/health", tags=["Health"])
def health_check():
    """Verificar estado de la aplicación"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": "connected",
        "ollama": {
            "url": settings.OLLAMA_BASE_URL,
            "model": settings.OLLAMA_MODEL
        }
    }

@app.get("/config", tags=["Health"])
def get_config():
    """Obtener configuración actual (solo disponible en modo DEBUG)"""
    if not settings.DEBUG:
        return JSONResponse(
            status_code=403,
            content={
                "error": "Forbidden",
                "message": "Este endpoint solo está disponible en modo DEBUG"
            }
        )
    
    return {
        "app": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "debug": settings.DEBUG
        },
        "database": {
            "host": settings.DB_HOST,
            "port": settings.DB_PORT,
            "name": settings.DB_NAME
        },
        "ollama": {
            "url": settings.OLLAMA_BASE_URL,
            "model": settings.OLLAMA_MODEL
        },
        "redis": {
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT
        },
        "chatbot": {
            "name": settings.BOT_NAME,
            "default_agent_id": settings.DEFAULT_AGENT_ID
        }
    }

# ==================== EJECUCIÓN ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )