from exceptions.base import ValidationException,NotFoundException
from typing import List, Optional
from typing import Optional
from sqlalchemy.orm import Session
from repositories.visitante_anonimo_repo import VisitanteAnonimoRepository,VisitanteAnonimoCreate,VisitanteAnonimo,VisitanteAnonimoUpdate
from datetime import datetime

class VisitanteAnonimoService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = VisitanteAnonimoRepository(db)
    
    def crear_visitante(self, visitante_data: VisitanteAnonimoCreate) -> VisitanteAnonimo:
        # Validación: sesión no vacía
        if not visitante_data.identificador_sesion.strip():
            raise ValidationException("El identificador de sesión no puede estar vacío")
        
        return self.repo.create(visitante_data)
    
    def obtener_visitante(self, id_visitante: int) -> VisitanteAnonimo:
        return self.repo.get_by_id(id_visitante)
    
    def obtener_por_sesion(self, identificador_sesion: str) -> Optional[VisitanteAnonimo]:
        visitante = self.repo.get_by_sesion(identificador_sesion)
        if not visitante:
            raise NotFoundException("Visitante con sesión", identificador_sesion)
        return visitante
    
    def listar_visitantes(
        self,
        skip: int = 0,
        limit: int = 100,
        dispositivo: Optional[str] = None,
        pais: Optional[str] = None,
        fecha_desde: Optional[datetime] = None
    ) -> List[VisitanteAnonimo]:
        if limit > 500:
            raise ValidationException("Límite máximo: 500 registros")
        
        return self.repo.get_all(skip, limit, dispositivo, pais, fecha_desde)
    
    def actualizar_visitante(self, id_visitante: int, visitante_data: VisitanteAnonimoUpdate) -> VisitanteAnonimo:
        return self.repo.update(id_visitante, visitante_data)
    
    def registrar_actividad(self, id_visitante: int) -> VisitanteAnonimo:
        """Registrar que el visitante está activo"""
        return self.repo.registrar_actividad(id_visitante)
    
    def incrementar_conversacion(self, id_visitante: int) -> VisitanteAnonimo:
        """Incrementar contador al iniciar conversación"""
        return self.repo.incrementar_conversaciones(id_visitante)
    
    def incrementar_mensajes(self, id_visitante: int, cantidad: int = 1) -> VisitanteAnonimo:
        """Incrementar contador de mensajes"""
        return self.repo.incrementar_mensajes(id_visitante, cantidad)
    
    def obtener_estadisticas_visitante(self, id_visitante: int) -> dict:
        visitante = self.repo.get_by_id(id_visitante)
        stats = self.repo.get_estadisticas_visitante(id_visitante)
        
        return {
            "visitante": {
                "id": visitante.id_visitante,
                "sesion": visitante.identificador_sesion[:20] + "...",
                "dispositivo": visitante.dispositivo,
                "pais": visitante.pais
            },
            **stats,
            "total_conversaciones": visitante.total_conversaciones,
            "total_mensajes": visitante.total_mensajes
        }
    
    def obtener_visitantes_activos(self, minutos: int = 30) -> List[VisitanteAnonimo]:
        """Obtener visitantes activos recientemente"""
        return self.repo.get_visitantes_activos(minutos)
    
    def obtener_estadisticas_generales(self) -> dict:
        return {
            "total_visitantes": self.repo.count(),
            "visitantes_desktop": self.repo.count(dispositivo="desktop"),
            "visitantes_mobile": self.repo.count(dispositivo="mobile"),
            "visitantes_tablet": self.repo.count(dispositivo="tablet"),
            "visitantes_activos_30min": len(self.repo.get_visitantes_activos(30))
        }

