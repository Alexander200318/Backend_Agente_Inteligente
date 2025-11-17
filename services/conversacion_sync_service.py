from exceptions.base import ValidationException,NotFoundException
from typing import List, Optional
from typing import Optional
from sqlalchemy.orm import Session
from repositories.conversacion_sync_repo import ConversacionSyncRepository,ConversacionSyncCreate,ConversacionSync,ConversacionSyncUpdate

from datetime import date

class ConversacionSyncService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ConversacionSyncRepository(db)
    
    def crear_conversacion(self, conversacion_data: ConversacionSyncCreate) -> ConversacionSync:
        # Validación: MongoDB ID debe ser 24 caracteres hex
        if len(conversacion_data.mongodb_conversation_id) != 24:
            raise ValidationException("El ID de MongoDB debe tener exactamente 24 caracteres")
        
        return self.repo.create(conversacion_data)
    
    def obtener_conversacion(self, id_conversacion_sync: int) -> ConversacionSync:
        return self.repo.get_by_id(id_conversacion_sync)
    
    def obtener_por_mongodb_id(self, mongodb_id: str) -> ConversacionSync:
        conversacion = self.repo.get_by_mongodb_id(mongodb_id)
        if not conversacion:
            raise NotFoundException("Conversación con mongodb_id", mongodb_id)
        return conversacion
    
    def listar_por_visitante(
        self,
        id_visitante: int,
        estado: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ConversacionSync]:
        if limit > 500:
            raise ValidationException("Límite máximo: 500 registros")
        
        return self.repo.get_by_visitante(id_visitante, estado, skip, limit)
    
    def listar_por_agente(
        self,
        id_agente: int,
        estado: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ConversacionSync]:
        if limit > 500:
            raise ValidationException("Límite máximo: 500 registros")
        
        return self.repo.get_by_agente(id_agente, estado, skip, limit)
    
    def listar_activas(self, limit: int = 100) -> List[ConversacionSync]:
        return self.repo.get_activas(limit)
    
    def actualizar_conversacion(
        self,
        id_conversacion_sync: int,
        conversacion_data: ConversacionSyncUpdate
    ) -> ConversacionSync:
        return self.repo.update(id_conversacion_sync, conversacion_data)
    
    def finalizar_conversacion(self, id_conversacion_sync: int) -> ConversacionSync:
        """Marcar conversación como finalizada"""
        return self.repo.finalizar_conversacion(id_conversacion_sync)
    
    def derivar_a_agente(self, id_conversacion_sync: int, id_nuevo_agente: int) -> ConversacionSync:
        """Derivar conversación a otro agente"""
        return self.repo.derivar_agente(id_conversacion_sync, id_nuevo_agente)
    
    def registrar_mensaje(self, id_conversacion_sync: int, cantidad: int = 1) -> ConversacionSync:
        """Incrementar contador de mensajes"""
        if cantidad < 1:
            raise ValidationException("La cantidad debe ser mayor a 0")
        
        return self.repo.incrementar_mensajes(id_conversacion_sync, cantidad)
    
    def obtener_estadisticas_generales(self) -> dict:
        return {
            "total_conversaciones": self.repo.count(),
            "conversaciones_activas": self.repo.count(estado="activa"),
            "conversaciones_finalizadas": self.repo.count(estado="finalizada"),
            "conversaciones_abandonadas": self.repo.count(estado="abandonada"),
            "escaladas_humano": self.repo.count(estado="escalada_humano")
        }
    
    def obtener_estadisticas_fecha(self, fecha: date) -> dict:
        """Obtener estadísticas de un día específico"""
        return self.repo.get_estadisticas_por_fecha(fecha)
