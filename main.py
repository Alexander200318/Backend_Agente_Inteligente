from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from apscheduler.schedulers.asyncio import AsyncIOScheduler

# 🔥 IMPORTAR SLOWAPI PARA RATE LIMITING
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# 🔥 Cargar variables de entorno ANTES de importar settings
load_dotenv()

from core.config import settings
from database.init_db import init_db
from exceptions.base import BaseAPIException

# ==================== LIFESPAN ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manejo del ciclo de vida de la aplicación"""
    # ==================== STARTUP ====================
    print("=" * 60)
    print(f"🚀 Iniciando {settings.APP_NAME}")
    print(f"📦 Versión: {settings.APP_VERSION}")
    print(f"🔧 Modo DEBUG: {settings.DEBUG}")
    print(f"💾 Base de datos: {settings.DB_NAME}")
    print(f"🤖 Modelo Ollama: {settings.OLLAMA_MODEL}")
    print(f"🔒 Rate Limiting: {settings.RATE_LIMIT_PER_MINUTE}/min (Login: {settings.RATE_LIMIT_LOGIN_PER_MINUTE}/min)")
    print("=" * 60)
    
    # Inicializar base de datos MySQL
    init_db()
    
    # 🔥 NUEVO: Inicializar MongoDB
    from database.mongodb import init_mongodb
    await init_mongodb()
    print("✅ MongoDB inicializado")
    
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()

    async def finalizar_conversaciones_inactivas_job():
        """Job para finalizar conversaciones inactivas cada 10 minutos"""
        from database.database import SessionLocal
        from services.escalamiento_service import EscalamientoService
        import logging
        
        logger = logging.getLogger(__name__)
        db = SessionLocal()
        
        try:
            service = EscalamientoService(db)
            resultado = await service.finalizar_conversaciones_inactivas(timeout_minutos=1)
            logger.info(f"✅ Auto-finalización ejecutada: {resultado}")
            print(f"🧹 Conversaciones finalizadas: MongoDB={resultado['conversaciones_finalizadas_mongo']}, MySQL={resultado['conversaciones_finalizadas_mysql']}")
        except Exception as e:
            logger.error(f"❌ Error en auto-finalización: {e}")
            print(f"❌ Error en auto-finalización: {e}")
        finally:
            db.close()

    # Programar tarea cada 10 minutos
    scheduler.add_job(
        finalizar_conversaciones_inactivas_job, 
        'interval', 
        minutes=10,
        id='finalizar_conversaciones',
        replace_existing=True
    )
    scheduler.start()
    print("✅ Scheduler iniciado - Auto-finalización de conversaciones cada 10 minutos")

    # Guardar scheduler en app state
    app.state.scheduler = scheduler
    # ↑↑↑ HASTA AQUÍ

    yield
  

    

    
    # ==================== SHUTDOWN ====================
    print("👋 Cerrando aplicación...")
    
    # 🔥 NUEVO: Detener scheduler
    if hasattr(app.state, 'scheduler'):
        app.state.scheduler.shutdown()
        print("✅ Scheduler detenido")
    
    # 🔥 NUEVO: Cerrar MongoDB
    from database.mongodb import close_mongodb
    await close_mongodb()
    print("✅ MongoDB cerrado")

# ==================== RATE LIMITING ====================

# 🔥 Configurar rate limiter
limiter = Limiter(key_func=get_remote_address)

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

# 🔥 Agregar rate limiter a la app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# 🔥 NUEVO: Iniciar limpieza de sesiones en background
import threading
from utils.background_tasks import cleanup_sessions_periodically

cleanup_thread = threading.Thread(
    target=cleanup_sessions_periodically,
    args=(10,),  # Limpia cada 10 minutos
    daemon=True
)
cleanup_thread.start()
print("🧹 Background task: Limpieza de sesiones iniciada (cada 10 min)")



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
    # allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_origins=["*"],
    
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔥 Middleware de seguridad - Headers HTTP seguros
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Agregar headers de seguridad a todas las respuestas"""
    response = await call_next(request)
    
    # Headers de seguridad
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "ALLOWALL"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(self), camera=(self)"
    
    return response

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
    usuario_rol_router,
    aseguramiento_router,
    escalamiento_router,
    websocket_router
)

# Incluir routers de API con prefix /api/v1
app.include_router(usuario_router.router, prefix="/api/v1")
app.include_router(departamento_router.router, prefix="/api/v1")
app.include_router(rol_router.router, prefix="/api/v1", tags=["Roles"])
app.include_router(usuario_agente_router.router, prefix="/api/v1")
app.include_router(departamento_agente_router.router, prefix="/api/v1")
app.include_router(categoria_router.router, prefix="/api/v1", tags=["Categorías"])
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
app.include_router(usuario_rol_router.router, prefix="/api/v1")
app.include_router(aseguramiento_router.router, prefix="/api/v1")
# Incluir router del widget SIN prefix (acceso directo a /widget y /admin)
app.include_router(widget_router.router, tags=["Widget"])
app.include_router(escalamiento_router.router, prefix="/api/v1")
app.include_router(websocket_router.router)

# ==================== HEALTH CHECK ====================

@app.get("/", tags=["Health"])
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def root(request: Request):
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
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def health_check(request: Request):
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
@limiter.limit("10/minute")  # Límite más restrictivo para endpoint sensible
def get_config(request: Request):
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
    

from core.security import get_password_hash, verify_password
from database.database import get_db
from sqlalchemy.orm import Session
from fastapi import Depends

@app.get("/dev/generate-hash/{password}")
async def generate_hash_dev(password: str):
    """🔧 DESARROLLO: Genera hash de contraseña"""
    hashed = get_password_hash(password)
    return {
        "password": password,
        "hash": hashed,
        "sql": f"UPDATE usuario SET password = '{hashed}' WHERE username = 'superadmin';"
    }

@app.get("/dev/check-user/{username}")
async def check_user_dev(username: str, db: Session = Depends(get_db)):
    """🔧 DESARROLLO: Verifica usuario"""
    from models.usuario import Usuario
    from models.usuario_rol import UsuarioRol
    from models.rol import Rol
    
    usuario = db.query(Usuario).filter(Usuario.username == username).first()
    
    if not usuario:
        return {"error": f"Usuario '{username}' no encontrado"}
    
    roles = db.query(UsuarioRol).filter(
        UsuarioRol.id_usuario == usuario.id_usuario
    ).join(Rol).all()
    
    return {
        "id_usuario": usuario.id_usuario,
        "username": usuario.username,
        "email": usuario.email,
        "estado": usuario.estado,
        "intentos_fallidos": usuario.intentos_fallidos,
        "password_length": len(usuario.password),
        "roles": [
            {
                "id_rol": r.id_rol,
                "nombre_rol": r.rol.nombre_rol,
                "nivel": r.rol.nivel_jerarquia
            }
            for r in roles
        ]
    }



