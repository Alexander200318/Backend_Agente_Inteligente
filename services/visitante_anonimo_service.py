from exceptions.base import ValidationException, NotFoundException
from typing import List, Optional
from sqlalchemy.orm import Session
from repositories.visitante_anonimo_repo import VisitanteAnonimoRepository, VisitanteAnonimoCreate, VisitanteAnonimo, VisitanteAnonimoUpdate
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

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
        fecha_desde: Optional[datetime] = None,
        canal_acceso: Optional[str] = None,  # 🔥 NUEVO
        pertenece_instituto: Optional[bool] = None  # 🔥 NUEVO
    ) -> List[VisitanteAnonimo]:
        if limit > 500:
            raise ValidationException("Límite máximo: 500 registros")
        
        return self.repo.get_all(skip, limit, dispositivo, pais, fecha_desde, canal_acceso, pertenece_instituto)
    
    # 🔥 NUEVO - Listar por canal
    def listar_por_canal(self, canal_acceso: str, skip: int = 0, limit: int = 100) -> List[VisitanteAnonimo]:
        """Listar visitantes por canal de acceso"""
        if limit > 500:
            raise ValidationException("Límite máximo: 500 registros")
        
        return self.repo.get_by_canal(canal_acceso, skip, limit)
    
    # 🔥 NUEVO - Listar miembros del instituto
    def listar_miembros_instituto(self, skip: int = 0, limit: int = 100) -> List[VisitanteAnonimo]:
        """Listar visitantes que pertenecen al instituto"""
        if limit > 500:
            raise ValidationException("Límite máximo: 500 registros")
        
        return self.repo.get_miembros_instituto(skip, limit)
    
    def actualizar_visitante(self, id_visitante: int, visitante_data: VisitanteAnonimoUpdate) -> VisitanteAnonimo:
        return self.repo.update(id_visitante, visitante_data)
    
    # 🔥 NUEVO - Actualizar satisfacción
    def actualizar_satisfaccion(self, id_visitante: int, satisfaccion: int) -> VisitanteAnonimo:
        """Actualizar satisfacción estimada del visitante (1-5)"""
        if satisfaccion < 1 or satisfaccion > 5:
            raise ValidationException("La satisfacción debe estar entre 1 y 5")
        
        return self.repo.actualizar_satisfaccion(id_visitante, satisfaccion)
    
    # 🔥 NUEVO - Actualizar perfil
    def actualizar_perfil(
        self,
        id_visitante: int,
        nombre: Optional[str] = None,
        apellido: Optional[str] = None,
        edad: Optional[str] = None,
        ocupacion: Optional[str] = None,
        pertenece_instituto: Optional[bool] = None,
        email: Optional[str] = None
    ) -> VisitanteAnonimo:
        """Actualizar datos de perfil del visitante"""
        return self.repo.actualizar_perfil(
            id_visitante,
            nombre,
            apellido,
            edad,
            ocupacion,
            pertenece_instituto,
            email
        )
    
    def registrar_actividad(self, id_visitante: int) -> VisitanteAnonimo:
        """Registrar que el visitante está activo"""
        return self.repo.registrar_actividad(id_visitante)
    
    def incrementar_conversacion(self, id_visitante: int) -> VisitanteAnonimo:
        """Incrementar contador al iniciar conversación"""
        return self.repo.incrementar_conversaciones(id_visitante)
    
    def incrementar_mensajes(self, id_visitante: int, cantidad: int = 1) -> VisitanteAnonimo:
        """Incrementar contador de mensajes"""
        return self.repo.incrementar_mensajes(id_visitante, cantidad)
    
    def obtener_o_crear_visitante(
        self,
        session_id: str,
        ip_origen: Optional[str] = None,
        user_agent: Optional[str] = None,
        dispositivo: Optional[str] = None,
        navegador: Optional[str] = None,
        sistema_operativo: Optional[str] = None,
        canal_acceso: Optional[str] = "widget"  # 🔥 NUEVO
    ) -> VisitanteAnonimo:
        """
        Obtiene un visitante existente o crea uno nuevo
        
        Args:
            session_id: Identificador único de sesión
            ip_origen: IP del visitante
            user_agent: User agent completo
            dispositivo: Tipo de dispositivo (desktop/mobile/tablet)
            navegador: Nombre del navegador
            sistema_operativo: Sistema operativo
            canal_acceso: Canal de acceso (widget, whatsapp, telegram, etc.)
            
        Returns:
            Instancia de VisitanteAnonimo
        """
        try:
            # Intentar obtener visitante existente
            visitante = self.repo.get_by_sesion(session_id)
            
            if visitante:
                # Actualizar última visita
                self.registrar_actividad(visitante.id_visitante)
                logger.info(f"✅ Visitante existente: ID={visitante.id_visitante}")
                return visitante
            
        except NotFoundException:
            # No existe, crear nuevo
            pass
        
        # Crear nuevo visitante
        visitante_data = VisitanteAnonimoCreate(
            identificador_sesion=session_id,
            ip_origen=ip_origen or "unknown",
            user_agent=user_agent or "unknown",
            dispositivo=dispositivo,
            navegador=navegador,
            sistema_operativo=sistema_operativo,
            canal_acceso=canal_acceso  # 🔥 NUEVO
        )
        
        nuevo_visitante = self.crear_visitante(visitante_data)
        logger.info(f"✅ Nuevo visitante creado: ID={nuevo_visitante.id_visitante}, canal={canal_acceso}")
        return nuevo_visitante
    
    def obtener_estadisticas_visitante(self, id_visitante: int) -> dict:
        visitante = self.repo.get_by_id(id_visitante)
        stats = self.repo.get_estadisticas_visitante(id_visitante)
        
        return {
            "visitante": {
                "id": visitante.id_visitante,
                "sesion": visitante.identificador_sesion[:20] + "...",
                "dispositivo": visitante.dispositivo,
                "pais": visitante.pais,
                "canal_acceso": visitante.canal_acceso,  # 🔥 NUEVO
                "satisfaccion": visitante.satisfaccion_estimada  # 🔥 NUEVO
            },
            **stats,
            "total_conversaciones": visitante.total_conversaciones,
            "total_mensajes": visitante.total_mensajes
        }
    
    def obtener_visitantes_activos(self, minutos: int = 30) -> List[VisitanteAnonimo]:
        """Obtener visitantes activos recientemente"""
        return self.repo.get_visitantes_activos(minutos)
    
    # 🔥 NUEVO - Estadísticas de satisfacción
    def obtener_estadisticas_satisfaccion(self) -> dict:
        """Obtener estadísticas de satisfacción general"""
        return self.repo.get_estadisticas_satisfaccion()
    
    def obtener_estadisticas_generales(self) -> dict:
        # Estadísticas de satisfacción
        stats_satisfaccion = self.repo.get_estadisticas_satisfaccion()
        
        return {
            "total_visitantes": self.repo.count(),
            "visitantes_desktop": self.repo.count(dispositivo="desktop"),
            "visitantes_mobile": self.repo.count(dispositivo="mobile"),
            "visitantes_tablet": self.repo.count(dispositivo="tablet"),
            "visitantes_activos_30min": len(self.repo.get_visitantes_activos(30)),
            # 🔥 NUEVO - Estadísticas de satisfacción
            "satisfaccion": stats_satisfaccion
        }