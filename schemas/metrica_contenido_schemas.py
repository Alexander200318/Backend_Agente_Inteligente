from pydantic import BaseModel, Field, validator, EmailStr
from pydantic import BaseModel

from datetime import date, datetime



class MetricaContenidoBase(BaseModel):
    fecha: date
    veces_usado_dia: int = 0
    veces_util_dia: int = 0
    veces_no_util_dia: int = 0
    total_agentes_usaron: int = 0
    conversaciones_donde_usado: int = 0

class MetricaContenidoCreate(MetricaContenidoBase):
    id_contenido: int

class MetricaContenidoResponse(MetricaContenidoBase):
    id_metrica_contenido: int
    id_contenido: int
    fecha_calculo: datetime
    class Config:
        from_attributes = True