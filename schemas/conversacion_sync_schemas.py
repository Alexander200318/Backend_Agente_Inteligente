from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class ConversacionSyncBase(BaseModel):
    mongodb_conversation_id: str = Field(..., min_length=24, max_length=24, description="ID de MongoDB (24 caracteres hex)")
    id_visitante: int
    id_agente_inicial: int
    id_agente_actual: Optional[int] = None
    estado: str = Field("activa", pattern="^(activa|finalizada|abandonada|escalada_humano)$")
    
    @validator('mongodb_conversation_id')
    def validar_mongodb_id(cls, v):
        # Validar que sea hexadecimal
        try:
            int(v, 16)
        except ValueError:
            raise ValueError('El ID debe ser hexadecimal de 24 caracteres')
        return v

class ConversacionSyncCreate(ConversacionSyncBase):
    pass

class ConversacionSyncUpdate(BaseModel):
    id_agente_actual: Optional[int] = None
    estado: Optional[str] = Field(None, pattern="^(activa|finalizada|abandonada|escalada_humano)$")
    fecha_fin: Optional[datetime] = None
    total_mensajes: Optional[int] = None
    requirio_atencion_humana: Optional[bool] = None

class ConversacionSyncResponse(ConversacionSyncBase):
    id_conversacion_sync: int
    fecha_inicio: datetime
    fecha_fin: Optional[datetime]
    total_mensajes: int
    requirio_atencion_humana: bool
    ultima_sincronizacion: datetime
    
    class Config:
        from_attributes = True