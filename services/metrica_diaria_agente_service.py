from typing import Optional
from sqlalchemy.orm import Session
from repositories.metrica_diaria_agente_repo import MetricaDiariaAgenteRepository,MetricaDiariaAgenteCreate
from datetime import date

class MetricaDiariaAgenteService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = MetricaDiariaAgenteRepository(db)
    
    def registrar_metrica(self, data: MetricaDiariaAgenteCreate):
        return self.repo.create_or_update(data)
    
    def obtener_metricas_agente(self, id_agente: int, fecha_inicio: Optional[date] = None, fecha_fin: Optional[date] = None):
        return self.repo.get_by_agente(id_agente, fecha_inicio, fecha_fin)
    
    def obtener_resumen_agente(self, id_agente: int, fecha_inicio: date, fecha_fin: date):
        return self.repo.get_resumen_agente(id_agente, fecha_inicio, fecha_fin)