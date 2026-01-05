# tasks/vigencia_cron.py
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from database.database import SessionLocal
from services.unidad_contenido_service import UnidadContenidoService
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def actualizar_vigencias_diarias():

    logger.info(f"🔄 [{datetime.now()}] Iniciando actualización de vigencias...")
    
    db = SessionLocal()
    try:
        service = UnidadContenidoService(db)
        resultado = service.actualizar_vigencias_masivo()
        
        logger.info(f"✅ Vigencias actualizadas:")
        logger.info(f"   - Total revisados: {resultado['total_revisados']}")
        logger.info(f"   - Actualizados: {resultado['actualizados']}")
        logger.info(f"   - Sin cambios: {resultado['sin_cambios']}")
        
        return resultado
    except Exception as e:
        logger.error(f"❌ Error actualizando vigencias: {str(e)}")
        raise
    finally:
        db.close()

def iniciar_scheduler():
    """
    Configura y inicia el scheduler
    """
    scheduler = BackgroundScheduler()
    
    # Ejecutar todos los días a las 00:01 AM
    scheduler.add_job(
        actualizar_vigencias_diarias,
        'cron',
        hour=0,
        minute=1,
        id='actualizar_vigencias',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("📅 Scheduler de vigencias iniciado (ejecuta diariamente a las 00:01)")
    
    return scheduler