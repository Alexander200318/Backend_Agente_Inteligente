# models/conversation_mongo.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Roles de mensajes en la conversación"""
    user = "user"
    assistant = "assistant"
    system = "system"
    human_agent = "human_agent"


class Message(BaseModel):
    """Modelo de un mensaje individual"""
    role: Union[MessageRole, str]  # 🔥 Acepta tanto Enum como string
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Metadata adicional
    sources_used: Optional[int] = None
    model_used: Optional[str] = None
    token_count: Optional[int] = None
    
    # Para mensajes de humano
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    
    @validator('role', pre=True)
    def validate_role(cls, v):
        """Convierte string a MessageRole si es necesario"""
        if isinstance(v, str):
            try:
                return MessageRole(v)
            except ValueError:
                return v  # Si no es válido, dejar como string
        return v
    
    class Config:
        use_enum_values = True


class ConversationStatus(str, Enum):
    """Estados posibles de una conversación"""
    activa = "activa"
    finalizada = "finalizada"
    abandonada = "abandonada"
    escalada_humano = "escalada_humano"


class ConversationMetadata(BaseModel):
    """Metadata de la conversación"""
    estado: Union[ConversationStatus, str] = "activa"  # 🔥 Acepta tanto Enum como string
    
    # Info del visitante
    ip_origen: Optional[str] = None
    user_agent: Optional[str] = None
    dispositivo: Optional[str] = None
    navegador: Optional[str] = None
    
    # Métricas
    total_mensajes: int = 0
    total_mensajes_usuario: int = 0
    total_mensajes_agente: int = 0
    requirio_atencion_humana: bool = False
    
    # Escalamiento
    escalado_a_usuario_id: Optional[int] = None
    escalado_a_usuario_nombre: Optional[str] = None
    fecha_escalamiento: Optional[datetime] = None
    fecha_atencion_humana: Optional[datetime] = None
    fecha_resolucion: Optional[datetime] = None
    
    # Satisfacción
    calificacion: Optional[int] = None
    comentario_calificacion: Optional[str] = None
    
    @validator('estado', pre=True)
    def validate_estado(cls, v):
        """Convierte string a ConversationStatus si es necesario"""
        if isinstance(v, str):
            try:
                return ConversationStatus(v)
            except ValueError:
                return v  # Si no es válido, dejar como string
        return v
    
    class Config:
        use_enum_values = True


class ConversationMongo(BaseModel):
    """
    Modelo principal de conversación en MongoDB
    """
    # Identificadores
    session_id: str = Field(..., description="UUID único de la sesión")
    id_agente: int = Field(..., description="ID del agente virtual")
    id_visitante: Optional[int] = None
    
    # Información del agente
    agent_name: str
    agent_type: Optional[str] = None
    
    # Mensajes de la conversación
    messages: List[Message] = Field(default_factory=list)
    
    # Metadata
    metadata: ConversationMetadata = Field(default_factory=ConversationMetadata)
    
    # Origen de la conversación
    origin: str = Field(default="web", description="web, mobile, widget, api")
    
    # Auditoría
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConversationCreate(BaseModel):
    """Schema para crear una nueva conversación"""
    session_id: str
    id_agente: int
    agent_name: str
    agent_type: Optional[str] = None
    id_visitante: Optional[int] = None
    origin: str = "web"
    
    # Metadata inicial
    ip_origen: Optional[str] = None
    user_agent: Optional[str] = None
    dispositivo: Optional[str] = None
    navegador: Optional[str] = None


class MessageCreate(BaseModel):
    """Schema para agregar un mensaje a una conversación"""
    role: MessageRole
    content: str
    
    # Opcional para metadata
    sources_used: Optional[int] = None
    model_used: Optional[str] = None
    token_count: Optional[int] = None
    
    # Para mensajes de humano
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    
    class Config:
        use_enum_values = True


class ConversationResponse(BaseModel):
    """Schema para respuesta de conversación"""
    id: str
    session_id: str
    id_agente: int
    id_visitante: Optional[int] = None 
    agent_name: str
    messages: List[Message]
    metadata: ConversationMetadata
    origin: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConversationUpdate(BaseModel):
    """Schema para actualizar una conversación"""
    estado: Optional[ConversationStatus] = None
    requirio_atencion_humana: Optional[bool] = None
    escalado_a_usuario_id: Optional[int] = None
    escalado_a_usuario_nombre: Optional[str] = None
    calificacion: Optional[int] = None
    comentario_calificacion: Optional[str] = None
    
    class Config:
        use_enum_values = True


class ConversationListResponse(BaseModel):
    """Schema para listar conversaciones"""
    total: int
    page: int
    page_size: int
    conversations: List[ConversationResponse]


class ConversationStats(BaseModel):
    """Estadísticas de conversaciones"""
    total_conversaciones: int
    conversaciones_activas: int
    conversaciones_finalizadas: int
    conversaciones_escaladas: int
    promedio_mensajes_por_conversacion: float
    calificacion_promedio: Optional[float] = None