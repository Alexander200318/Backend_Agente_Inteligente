from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import func, and_
from typing import Optional, List
from datetime import datetime, timedelta
import logging
from models.visitante_anonimo import VisitanteAnonimo
from models.conversacion_sync import ConversacionSync
from schemas.visitante_anonimo_schemas import VisitanteAnonimoCreate, VisitanteAnonimoUpdate
from exceptions.base import *

logger = logging.getLogger(__name__)

class VisitanteAnonimoRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, visitante_data: VisitanteAnonimoCreate) -> VisitanteAnonimo:
        try:
            # Verificar si ya existe el identificador de sesión
            existing = self.get_by_sesion(visitante_data.identificador_sesion)
            if existing:
                raise AlreadyExistsException(
                    "Visitante",
                    "sesión",
                    visitante_data.identificador_sesion[:20] + "..."
                )
            
            visitante = VisitanteAnonimo(**visitante_data.dict())
            self.db.add(visitante)
            self.db.commit()
            self.db.refresh(visitante)
            return visitante
        except IntegrityError:
            self.db.rollback()
            raise AlreadyExistsException("Visitante", "sesión", "duplicada")
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al crear visitante: {str(e)}")
    
    def get_by_id(self, id_visitante: int) -> VisitanteAnonimo:
        visitante = self.db.query(VisitanteAnonimo).filter(
            VisitanteAnonimo.id_visitante == id_visitante
        ).first()
        
        if not visitante:
            raise NotFoundException("Visitante", id_visitante)
        return visitante
    
    def get_by_sesion(self, identificador_sesion: str) -> Optional[VisitanteAnonimo]:
        return self.db.query(VisitanteAnonimo).filter(
            VisitanteAnonimo.identificador_sesion == identificador_sesion
        ).first()
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        dispositivo: Optional[str] = None,
        pais: Optional[str] = None,
        fecha_desde: Optional[datetime] = None,
        canal_acceso: Optional[str] = None,  # 🔥 NUEVO
        pertenece_instituto: Optional[bool] = None  # 🔥 NUEVO
    ) -> List[VisitanteAnonimo]:
        query = self.db.query(VisitanteAnonimo)
        
        if dispositivo:
            query = query.filter(VisitanteAnonimo.dispositivo == dispositivo)
        if pais:
            query = query.filter(VisitanteAnonimo.pais == pais)
        if fecha_desde:
            query = query.filter(VisitanteAnonimo.primera_visita >= fecha_desde)
        if canal_acceso:  # 🔥 NUEVO
            query = query.filter(VisitanteAnonimo.canal_acceso == canal_acceso)
        if pertenece_instituto is not None:  # 🔥 NUEVO
            query = query.filter(VisitanteAnonimo.pertenece_instituto == pertenece_instituto)
        
        return query.order_by(VisitanteAnonimo.primera_visita.desc()).offset(skip).limit(limit).all()
    
    # 🔥 NUEVO - Listar por canal
    def get_by_canal(self, canal_acceso: str, skip: int = 0, limit: int = 100) -> List[VisitanteAnonimo]:
        """Obtener visitantes por canal de acceso"""
        return self.db.query(VisitanteAnonimo).filter(
            VisitanteAnonimo.canal_acceso == canal_acceso
        ).order_by(VisitanteAnonimo.primera_visita.desc()).offset(skip).limit(limit).all()
    
    # 🔥 NUEVO - Listar miembros del instituto
    def get_miembros_instituto(self, skip: int = 0, limit: int = 100) -> List[VisitanteAnonimo]:
        """Obtener visitantes que pertenecen al instituto"""
        return self.db.query(VisitanteAnonimo).filter(
            VisitanteAnonimo.pertenece_instituto == True
        ).order_by(VisitanteAnonimo.primera_visita.desc()).offset(skip).limit(limit).all()
    
    def update(self, id_visitante: int, visitante_data: VisitanteAnonimoUpdate) -> VisitanteAnonimo:
        try:
            visitante = self.get_by_id(id_visitante)
            
            # Lista de campos válidos en el modelo
            valid_fields = {
                'identificador_sesion', 'ip_origen', 'user_agent', 'dispositivo',
                'navegador', 'sistema_operativo', 'pais', 'ciudad', 'ultima_visita',
                'total_conversaciones', 'total_mensajes', 'canal_acceso', 'nombre',
                'apellido', 'edad', 'ocupacion', 'pertenece_instituto',
                'satisfaccion_estimada', 'email'
            }
            
            for field, value in visitante_data.dict(exclude_unset=True).items():
                # Solo actualizar si el valor no es None y el campo existe en el modelo
                if value is not None and field in valid_fields:
                    setattr(visitante, field, value)

            visitante.ultima_visita = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(visitante)
            return visitante
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"❌ Error al actualizar visitante: {str(e)}")
            raise DatabaseException(f"Error al actualizar visitante: {str(e)}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error inesperado al actualizar visitante: {str(e)}")
            raise DatabaseException(f"Error inesperado: {str(e)}")
    
    # 🔥 NUEVO - Actualizar solo satisfacción
    def actualizar_satisfaccion(self, id_visitante: int, satisfaccion: int) -> VisitanteAnonimo:
        """Actualizar satisfacción estimada (1-5)"""
        try:
            if satisfaccion < 1 or satisfaccion > 5:
                raise ValueError("La satisfacción debe estar entre 1 y 5")
            
            visitante = self.get_by_id(id_visitante)
            visitante.satisfaccion_estimada = satisfaccion
            self.db.commit()
            self.db.refresh(visitante)
            return visitante
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al actualizar satisfacción: {str(e)}")
    
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
        try:
            visitante = self.get_by_id(id_visitante)
            
            if nombre is not None:
                visitante.nombre = nombre
            if apellido is not None:
                visitante.apellido = apellido
            if edad is not None:
                visitante.edad = edad
            if ocupacion is not None:
                visitante.ocupacion = ocupacion
            if pertenece_instituto is not None:
                visitante.pertenece_instituto = pertenece_instituto
            if email is not None:  # 🔥 AGREGAR AQUÍ
                visitante.email = email
            
            self.db.commit()
            self.db.refresh(visitante)
            return visitante
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al actualizar perfil: {str(e)}")
    
    def registrar_actividad(self, id_visitante: int) -> VisitanteAnonimo:
        """Actualizar última visita"""
        visitante = self.get_by_id(id_visitante)
        visitante.ultima_visita = datetime.now()
        self.db.commit()
        self.db.refresh(visitante)
        return visitante
    
    def incrementar_conversaciones(self, id_visitante: int) -> VisitanteAnonimo:
        """Incrementar contador de conversaciones"""
        visitante = self.get_by_id(id_visitante)
        visitante.total_conversaciones += 1
        self.db.commit()
        self.db.refresh(visitante)
        return visitante
    
    def incrementar_mensajes(self, id_visitante: int, cantidad: int = 1) -> VisitanteAnonimo:
        """Incrementar contador de mensajes"""
        visitante = self.get_by_id(id_visitante)
        visitante.total_mensajes += cantidad
        self.db.commit()
        self.db.refresh(visitante)
        return visitante
    
    def get_estadisticas_visitante(self, id_visitante: int) -> dict:
        """Estadísticas del visitante"""
        visitante = self.get_by_id(id_visitante)
        
        conversaciones_activas = self.db.query(func.count(ConversacionSync.id_conversacion_sync)).filter(
            ConversacionSync.id_visitante == id_visitante,
            ConversacionSync.estado == "activa"
        ).scalar()
        
        conversaciones_finalizadas = self.db.query(func.count(ConversacionSync.id_conversacion_sync)).filter(
            ConversacionSync.id_visitante == id_visitante,
            ConversacionSync.estado == "finalizada"
        ).scalar()
        
        return {
            "conversaciones_activas": conversaciones_activas or 0,
            "conversaciones_finalizadas": conversaciones_finalizadas or 0
        }
    
    # 🔥 NUEVO - Estadísticas de satisfacción
    def get_estadisticas_satisfaccion(self) -> dict:
        """Obtener estadísticas de satisfacción general"""
        # Total con satisfacción registrada
        total_con_satisfaccion = self.db.query(func.count(VisitanteAnonimo.id_visitante)).filter(
            VisitanteAnonimo.satisfaccion_estimada.isnot(None)
        ).scalar() or 0
        
        if total_con_satisfaccion == 0:
            return {
                "total_evaluaciones": 0,
                "promedio_satisfaccion": None,
                "distribucion": {
                    "1_estrella": 0,
                    "2_estrellas": 0,
                    "3_estrellas": 0,
                    "4_estrellas": 0,
                    "5_estrellas": 0
                }
            }
        
        # Promedio
        promedio = self.db.query(func.avg(VisitanteAnonimo.satisfaccion_estimada)).filter(
            VisitanteAnonimo.satisfaccion_estimada.isnot(None)
        ).scalar() or 0.0
        
        # Distribución
        distribucion = {}
        for i in range(1, 6):
            count = self.db.query(func.count(VisitanteAnonimo.id_visitante)).filter(
                VisitanteAnonimo.satisfaccion_estimada == i
            ).scalar() or 0
            key = f"{i}_estrella{'s' if i > 1 else ''}"
            distribucion[key] = count
        
        return {
            "total_evaluaciones": total_con_satisfaccion,
            "promedio_satisfaccion": round(float(promedio), 2),
            "distribucion": distribucion
        }
    
    def count(self, dispositivo: Optional[str] = None) -> int:
        query = self.db.query(VisitanteAnonimo)
        if dispositivo:
            query = query.filter(VisitanteAnonimo.dispositivo == dispositivo)
        return query.count()
    
    def get_visitantes_activos(self, minutos: int = 30) -> List[VisitanteAnonimo]:
        """Obtener visitantes activos en los últimos X minutos"""
        tiempo_limite = datetime.now() - timedelta(minutes=minutos)
        return self.db.query(VisitanteAnonimo).filter(
            VisitanteAnonimo.ultima_visita >= tiempo_limite
        ).all()