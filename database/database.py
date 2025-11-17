from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from core.config import settings

# Crear engine con configuración de pool
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Verificar conexión antes de usar
    pool_size=10,  # Número de conexiones permanentes
    max_overflow=20,  # Conexiones adicionales bajo demanda
    pool_recycle=3600,  # Reciclar conexiones cada hora
    echo=settings.DEBUG,  # Log de queries SQL en modo debug
    poolclass=QueuePool
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base para modelos
Base = declarative_base()

def get_db():
    """
    Dependency para obtener sesión de base de datos.
    Se usa con FastAPI Depends.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()