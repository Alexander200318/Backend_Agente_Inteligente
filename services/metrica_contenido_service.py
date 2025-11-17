
from typing import Optional
from sqlalchemy.orm import Session
from repositories.metrica_contenido_repo import MetricaContenidoRepository,MetricaContenidoCreate
from datetime import date

class MetricaContenidoService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = MetricaContenidoRepository(db)
    
    def registrar_metrica(self, data: MetricaContenidoCreate):
        return self.repo.create_or_update(data)
    
    def obtener_metricas_contenido(self, id_contenido: int, fecha_inicio: Optional[date] = None, fecha_fin: Optional[date] = None):
        return self.repo.get_by_contenido(id_contenido, fecha_inicio, fecha_fin)
    
    def obtener_top_contenidos(self, limit: int = 10):
        return self.repo.get_contenidos_mas_usados(limit)
