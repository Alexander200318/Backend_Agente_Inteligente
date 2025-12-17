# services/escalamiento_service.py
"""
Servicio para escalar conversaciones a atención humana

Este servicio maneja:
1. Detección de intención de escalamiento
2. Actualización de estados en MySQL y MongoDB
3. Asignación de usuarios humanos
4. Notificaciones
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from models.agente_virtual import AgenteVirtual
from models.conversacion_sync import ConversacionSync
from models.notificacion_usuario import NotificacionUsuario, TipoNotificacionEnum
from models.usuario import Usuario
from models.persona import Persona
from services.conversation_service import ConversationService
from models.conversation_mongo import ConversationUpdate, ConversationStatus, MessageCreate, MessageRole

logger = logging.getLogger(__name__)


class EscalamientoService:
    """
    Servicio para gestionar escalamiento de conversaciones a humanos
    """
    
    # Palabras clave que indican que el usuario quiere hablar con humano
    PALABRAS_ESCALAMIENTO = [
        "hablar con humano",
        "quiero un humano",
        "hablar con persona",
        "persona real",
        "operador",
        "agente humano",
        "representante",
        "quiero hablar con alguien",
        "necesito ayuda de una persona",
        "no entiendo",
        "esto no me sirve",
        "quiero hablar con alguien más",
        "hablar con un humano"
    ]
    
    def __init__(self, db: Session):
        self.db = db
    
    def detectar_intencion_escalamiento(self, mensaje_usuario: str) -> bool:
        """
        Detecta si el usuario quiere hablar con un humano
        
        Args:
            mensaje_usuario: Mensaje del usuario en minúsculas
            
        Returns:
            True si detecta intención de escalamiento
        """
        mensaje_lower = mensaje_usuario.lower().strip()
        
        # Verificar si contiene alguna palabra clave
        for palabra_clave in self.PALABRAS_ESCALAMIENTO:
            if palabra_clave in mensaje_lower:
                logger.info(f"🔍 Intención de escalamiento detectada: '{palabra_clave}'")
                return True
        
        return False
    
    async def escalar_conversacion(
        self,
        session_id: str,
        id_agente: int,
        motivo: Optional[str] = "Solicitado por usuario"
    ) -> Dict[str, Any]:
        """
        Escala una conversación a atención humana
        
        Args:
            session_id: ID de la sesión en MongoDB
            id_agente: ID del agente virtual
            motivo: Motivo del escalamiento
            
        Returns:
            Dict con resultado del escalamiento
        """
        try:
            # 1. Obtener agente
            agente = self.db.query(AgenteVirtual).filter(
                AgenteVirtual.id_agente == id_agente
            ).first()
            
            if not agente:
                raise ValueError(f"Agente {id_agente} no encontrado")
            
            # 2. Obtener conversación de MongoDB
            conversation = await ConversationService.get_conversation_by_session(session_id)
            
            if not conversation:
                raise ValueError(f"Conversación {session_id} no encontrada en MongoDB")
            
            # 3. Buscar usuarios del departamento del agente (Opción A)
            usuarios_disponibles = self._obtener_usuarios_departamento(agente.id_departamento)
            
            if not usuarios_disponibles:
                logger.warning(f"⚠️ No hay usuarios disponibles en departamento {agente.id_departamento}")
                
                # Fallback: notificar a todos los usuarios activos (puedes ajustar esto)
                usuarios_disponibles = self.db.query(Usuario).filter(
                    Usuario.estado == 'activo'
                ).limit(5).all()
            
            # 4. Actualizar estado en MongoDB
            update_data = ConversationUpdate(
                estado=ConversationStatus.escalada_humano,
                requirio_atencion_humana=True
            )
            
            await ConversationService.update_conversation_status(session_id, update_data)
            
            logger.info(f"✅ Conversación escalada en MongoDB: {session_id}")
            
            # 5. Actualizar o crear registro en MySQL (Conversacion_Sync)
            conversacion_sync = self._actualizar_conversacion_sync(
                session_id=session_id,
                id_agente=id_agente,
                id_visitante=None
            )
            
            # 6. Crear notificaciones para usuarios del departamento
            notificaciones_creadas = self._crear_notificaciones(
                usuarios=usuarios_disponibles,
                id_agente=id_agente,
                agente_nombre=agente.nombre_agente,
                session_id=session_id,
                conversacion_sync_id=conversacion_sync.id_conversacion_sync if conversacion_sync else None
            )
            
            # 7. Agregar mensaje del agente en MongoDB con mensaje_derivacion
            if agente.mensaje_derivacion:
                mensaje_derivacion = MessageCreate(
                    role=MessageRole.system,
                    content=agente.mensaje_derivacion
                )
                await ConversationService.add_message(session_id, mensaje_derivacion)
            
            logger.info(f"🎉 Escalamiento completado: {session_id} → {len(notificaciones_creadas)} usuarios notificados")
            
            return {
                "success": True,
                "session_id": session_id,
                "usuarios_notificados": len(notificaciones_creadas),
                "mensaje_derivacion": agente.mensaje_derivacion,
                "conversacion_sync_id": conversacion_sync.id_conversacion_sync if conversacion_sync else None,
                "usuarios": [
                    {
                        "id": u.id_usuario,
                        "nombre": f"{u.persona.nombre} {u.persona.apellido}" if u.persona else u.username
                    }
                    for u in usuarios_disponibles[:5]  # Mostrar solo primeros 5
                ]
            }
            
        except Exception as e:
            logger.error(f"❌ Error escalando conversación: {e}")
            raise
    
    def _obtener_usuarios_departamento(self, id_departamento: Optional[int]) -> List[Usuario]:
        """
        Obtiene usuarios activos del departamento
        
        Args:
            id_departamento: ID del departamento
            
        Returns:
            Lista de usuarios disponibles
        """
        if not id_departamento:
            return []
        
        try:
            usuarios = self.db.query(Usuario).join(Persona).filter(
                Persona.id_departamento == id_departamento,
                Usuario.estado == 'activo',
                Persona.estado == 'activo'
            ).all()
            
            logger.info(f"📋 Usuarios encontrados en departamento {id_departamento}: {len(usuarios)}")
            return usuarios
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo usuarios del departamento: {e}")
            return []
    
    def _actualizar_conversacion_sync(
        self,
        session_id: str,
        id_agente: int,
        id_visitante: Optional[int]
    ) -> Optional[ConversacionSync]:
        """
        Actualiza o crea registro en Conversacion_Sync
        
        Args:
            session_id: Session ID de MongoDB
            id_agente: ID del agente
            id_visitante: ID del visitante (opcional)
            
        Returns:
            ConversacionSync creada o actualizada
        """
        try:
            # Buscar si ya existe
            conversacion = self.db.query(ConversacionSync).filter(
                ConversacionSync.mongodb_conversation_id == session_id
            ).first()
            
            if conversacion:
                # Actualizar estado
                from models.conversacion_sync import EstadoConversacionEnum
                conversacion.estado = EstadoConversacionEnum.escalada_humano
                conversacion.requirio_atencion_humana = True
                conversacion.ultima_sincronizacion = datetime.utcnow()
            else:
                # Crear nueva
                from models.conversacion_sync import EstadoConversacionEnum
                conversacion = ConversacionSync(
                    mongodb_conversation_id=session_id,
                    id_visitante=id_visitante or 1,  # Requerido en BD
                    id_agente_inicial=id_agente,
                    id_agente_actual=id_agente,
                    estado=EstadoConversacionEnum.escalada_humano,
                    requirio_atencion_humana=True,
                    fecha_inicio=datetime.utcnow(),
                    ultima_sincronizacion=datetime.utcnow()
                )
                self.db.add(conversacion)
            
            self.db.commit()
            self.db.refresh(conversacion)
            
            logger.info(f"✅ Conversacion_Sync actualizada: ID={conversacion.id_conversacion_sync}")
            return conversacion
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error actualizando Conversacion_Sync: {e}")
            return None
    
    def _crear_notificaciones(
        self,
        usuarios: List[Usuario],
        id_agente: int,
        agente_nombre: str,
        session_id: str,
        conversacion_sync_id: Optional[int]
    ) -> List[NotificacionUsuario]:
        """
        Crea notificaciones para los usuarios
        
        Args:
            usuarios: Lista de usuarios a notificar
            id_agente: ID del agente
            agente_nombre: Nombre del agente
            session_id: Session ID de la conversación
            conversacion_sync_id: ID en Conversacion_Sync
            
        Returns:
            Lista de notificaciones creadas
        """
        notificaciones = []
        
        try:
            for usuario in usuarios:
                notif = NotificacionUsuario(
                    id_usuario=usuario.id_usuario,
                    id_agente=id_agente,
                    tipo=TipoNotificacionEnum.urgente,  # Usar el enum
                    titulo=f'Nueva conversación escalada - {agente_nombre}',
                    mensaje=f'Se ha escalado una conversación del agente {agente_nombre} que requiere atención humana.',
                    icono='user-circle',
                    url_accion=f'/conversaciones-escaladas/{session_id}',
                    datos_adicionales=f'{{"session_id": "{session_id}", "conversacion_sync_id": {conversacion_sync_id}, "id_agente": {id_agente}}}',
                    leida=False,
                    fecha_creacion=datetime.utcnow()
                )
                
                self.db.add(notif)
                notificaciones.append(notif)
            
            self.db.commit()
            
            logger.info(f"📬 {len(notificaciones)} notificaciones creadas")
            return notificaciones
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error creando notificaciones: {e}")
            return []
    
    async def responder_como_humano(
        self,
        session_id: str,
        mensaje: str,
        id_usuario: int,
        nombre_usuario: str
    ) -> Dict[str, Any]:
        """
        Agrega respuesta de un humano a la conversación
        
        Args:
            session_id: ID de la sesión
            mensaje: Mensaje del humano
            id_usuario: ID del usuario humano
            nombre_usuario: Nombre del usuario
            
        Returns:
            Dict con resultado
        """
        try:
            # Agregar mensaje en MongoDB con role='human_agent'
            message_data = MessageCreate(
                role=MessageRole.human_agent,
                content=mensaje,
                user_id=id_usuario,
                user_name=nombre_usuario
            )
            
            conversation = await ConversationService.add_message(session_id, message_data)
            
            # Actualizar metadata si es la primera respuesta humana
            if not conversation.metadata.fecha_atencion_humana:
                update_data = ConversationUpdate(
                    escalado_a_usuario_id=id_usuario,
                    escalado_a_usuario_nombre=nombre_usuario
                )
                await ConversationService.update_conversation_status(session_id, update_data)
            
            logger.info(f"💬 Respuesta humana agregada: {nombre_usuario} → {session_id}")
            
            return {
                "success": True,
                "session_id": session_id,
                "mensaje_agregado": True,
                "total_mensajes": conversation.metadata.total_mensajes
            }
            
        except Exception as e:
            logger.error(f"❌ Error agregando respuesta humana: {e}")
            raise
    
    def obtener_conversaciones_escaladas(
        self,
        id_usuario: Optional[int] = None,
        id_departamento: Optional[int] = None,
        solo_pendientes: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Obtiene conversaciones escaladas pendientes de atención
        
        Args:
            id_usuario: Filtrar por usuario (opcional)
            id_departamento: Filtrar por departamento (opcional)
            solo_pendientes: Solo mostrar no resueltas
            
        Returns:
            Lista de conversaciones escaladas
        """
        try:
            from models.conversacion_sync import EstadoConversacionEnum
            
            query = self.db.query(ConversacionSync).filter(
                ConversacionSync.estado == EstadoConversacionEnum.escalada_humano
            )
            
            if solo_pendientes:
                query = query.filter(
                    ConversacionSync.requirio_atencion_humana == True
                )
            
            # Si hay filtro de departamento, join con Agente
            if id_departamento:
                query = query.join(AgenteVirtual, ConversacionSync.id_agente_inicial == AgenteVirtual.id_agente).filter(
                    AgenteVirtual.id_departamento == id_departamento
                )
            
            conversaciones = query.order_by(ConversacionSync.fecha_inicio.desc()).limit(50).all()
            
            logger.info(f"📋 Conversaciones escaladas encontradas: {len(conversaciones)}")
            
            return [
                {
                    "id_conversacion_sync": c.id_conversacion_sync,
                    "session_id": c.mongodb_conversation_id,
                    "id_agente": c.id_agente_inicial,
                    "estado": c.estado,
                    "fecha_inicio": c.fecha_inicio.isoformat() if c.fecha_inicio else None,
                    "requirio_atencion_humana": c.requirio_atencion_humana
                }
                for c in conversaciones
            ]
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo conversaciones escaladas: {e}")
            return []
