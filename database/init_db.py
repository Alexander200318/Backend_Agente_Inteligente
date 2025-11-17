from database.database import Base, engine
from sqlalchemy import text
from core.config import settings

def init_db():
    """
    Inicializar base de datos:
    - Crea todas las tablas si no existen
    - Verifica conexión
    """
    try:
        # Verificar conexión
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(f"✅ Conexión a MySQL exitosa: {settings.DB_NAME}")
        
        # Importar todos los modelos para que SQLAlchemy los registre
        import models
        # Esto importa todos los modelos del __init__.py
        
        # Crear tablas
        print("⏳ Creando tablas...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tablas creadas correctamente!")
        
    except Exception as e:
        print(f"❌ Error al inicializar base de datos: {e}")
        raise e

def drop_all_tables():
    """
    CUIDADO: Elimina todas las tablas.
    Solo usar en desarrollo.
    """
    if not settings.DEBUG:
        raise Exception("drop_all_tables solo puede ejecutarse en modo DEBUG")
    
    print("⚠️  ELIMINANDO TODAS LAS TABLAS...")
    Base.metadata.drop_all(bind=engine)
    print("✅ Tablas eliminadas")

if __name__ == "__main__":
    init_db()