from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr

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
    
    # 🔥 NUEVOS CAMPOS - Canal de acceso
    canal_acceso: Optional[str] = Field(None, max_length=50)
    
    # 🔥 NUEVOS CAMPOS - Datos opcionales del visitante
    nombre: Optional[str] = Field(None, max_length=100)
    apellido: Optional[str] = Field(None, max_length=100)
    edad: Optional[str] = Field(None, max_length=20)
    ocupacion: Optional[str] = Field(None, max_length=100)
    pertenece_instituto: Optional[bool] = False
    
    # 🔥 NUEVOS CAMPOS - Calidad de interacción
    satisfaccion_estimada: Optional[int] = Field(None, ge=1, le=5, description="Satisfacción del 1 al 5")
    email: Optional[str] = Field(None, max_length=150)


class VisitanteAnonimoCreate(VisitanteAnonimoBase):
    pass


# 🔥 NUEVO SCHEMA para registro por email
class EmailRegistration(BaseModel):
    email: EmailStr
    session_id: str
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    edad: Optional[str] = None
    ocupacion: Optional[str] = None
    pertenece_instituto: Optional[bool] = False

class VisitanteAnonimoUpdate(BaseModel):
    identificador_sesion: Optional[str] = None 
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


    # 🔥 NUEVOS CAMPOS
    canal_acceso: Optional[str] = Field(None, max_length=50)
    nombre: Optional[str] = Field(None, max_length=100)
    apellido: Optional[str] = Field(None, max_length=100)
    edad: Optional[str] = Field(None, max_length=20)
    ocupacion: Optional[str] = Field(None, max_length=100)
    pertenece_instituto: Optional[bool] = None
    satisfaccion_estimada: Optional[int] = Field(None, ge=1, le=5)
    email: Optional[str] = Field(None, max_length=150)

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