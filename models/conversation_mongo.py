# models/conversation_mongo.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Roles de mensajes en la conversación"""
    user = "user"
    assistant = "assistant"
    system = "system"
    human_agent = "human_agent"  # Para cuando un humano responde


class Message(BaseModel):
    """Modelo de un mensaje individual"""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Metadata adicional
    sources_used: Optional[int] = None  # Cuántas fuentes RAG usó
    model_used: Optional[str] = None    # Modelo de IA usado
    token_count: Optional[int] = None   # Tokens generados
    
    # Para mensajes de humano
    user_id: Optional[int] = None       # ID del usuario humano que respondió
    user_name: Optional[str] = None     # Nombre del usuario humano
    
    class Config:
        use_enum_values = True


class ConversationStatus(str, Enum):
    """Estados posibles de una conversación"""
    activa = "activa"
    finalizada = "finalizada"
    abandonada = "abandonada"
    escalada_humano = "escalada_humano"
    
    class Config:
        use_enum_values = True


class ConversationMetadata(BaseModel):
    """Metadata de la conversación"""
    estado: ConversationStatus = ConversationStatus.activa
    
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
    calificacion: Optional[int] = None  # 1-5 estrellas
    comentario_calificacion: Optional[str] = None
    
    class Config:
        use_enum_values = True


class ConversationMongo(BaseModel):
    """
    Modelo principal de conversación en MongoDB
    
    Este modelo representa la estructura completa de una conversación
    almacenada en MongoDB.
    """
    # Identificadores
    session_id: str = Field(..., description="UUID único de la sesión")
    id_agente: int = Field(..., description="ID del agente virtual")
    id_visitante: Optional[int] = None  # ID en MySQL si existe
    
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
    
    # MongoDB ID (se asigna automáticamente)
    # No lo incluimos en el modelo porque Pydantic no puede validar ObjectId directamente
    
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
    id: str  # MongoDB ObjectId como string
    session_id: str
    id_agente: int
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


# Modelos auxiliares para estadísticas
class ConversationStats(BaseModel):
    """Estadísticas de conversaciones"""
    total_conversaciones: int
    conversaciones_activas: int
    conversaciones_finalizadas: int
    conversaciones_escaladas: int
    promedio_mensajes_por_conversacion: float
    calificacion_promedio: Optional[float] = None
