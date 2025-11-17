from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class VisitanteAnonimoBase(BaseModel):
    identificador_sesion: str = Field(..., min_length=10, max_length=255)
    
    # Información técnica
    ip_origen: Optional[str] = Field(None, max_length=45)
    user_agent: Optional[str] = None
    dispositivo: Optional[str] = Field(None, pattern="^(desktop|mobile|tablet)$")
    navegador: Optional[str] = Field(None, max_length=50)
    sistema_operativo: Optional[str] = Field(None, max_length=50)
    
    # Geolocalización
    pais: Optional[str] = Field(None, max_length=50)
    ciudad: Optional[str] = Field(None, max_length=100)

class VisitanteAnonimoCreate(VisitanteAnonimoBase):
    pass

class VisitanteAnonimoUpdate(BaseModel):
    ip_origen: Optional[str] = None
    user_agent: Optional[str] = None
    dispositivo: Optional[str] = None
    navegador: Optional[str] = None
    sistema_operativo: Optional[str] = None
    pais: Optional[str] = None
    ciudad: Optional[str] = None
    ultima_visita: Optional[datetime] = None
    total_conversaciones: Optional[int] = None
    total_mensajes: Optional[int] = None

class VisitanteAnonimoResponse(VisitanteAnonimoBase):
    id_visitante: int
    primera_visita: datetime
    ultima_visita: Optional[datetime]
    total_conversaciones: int
    total_mensajes: int
    
    class Config:
        from_attributes = True

class VisitanteConEstadisticas(VisitanteAnonimoResponse):
    conversaciones_activas: int = 0
    conversaciones_finalizadas: int = 0