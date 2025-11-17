from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from decimal import Decimal

class MetricaDiariaAgenteBase(BaseModel):
    fecha: date
    visitantes_unicos: int = 0
    conversaciones_iniciadas: int = 0
    conversaciones_finalizadas: int = 0
    conversaciones_abandonadas: int = 0
    mensajes_enviados: int = 0
    mensajes_recibidos: int = 0
    derivaciones_salientes: int = 0
    derivaciones_entrantes: int = 0
    tiempo_respuesta_promedio_ms: Optional[Decimal] = None
    satisfaccion_promedio: Optional[Decimal] = None
    tasa_resolucion: Optional[Decimal] = None

class MetricaDiariaAgenteCreate(MetricaDiariaAgenteBase):
    id_agente: int

class MetricaDiariaAgenteResponse(MetricaDiariaAgenteBase):
    id_metrica: int
    id_agente: int
    fecha_calculo: datetime
    class Config:
        from_attributes = True