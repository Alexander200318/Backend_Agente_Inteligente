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
from datetime import datetime, timedelta
import logging
import re
import uuid
import random

from models.agente_virtual import AgenteVirtual
from models.notificacion_usuario import NotificacionUsuario, TipoNotificacionEnum
from models.usuario import Usuario, EstadoUsuarioEnum
from models.persona import Persona, EstadoPersonaEnum
from models.usuario_rol import UsuarioRol
from models.rol import Rol
from models.conversacion_sync import ConversacionSync, EstadoConversacionEnum
from models.visitante_anonimo import VisitanteAnonimo
from models.conversation_mongo import (
    ConversationCreate,
    ConversationUpdate,
    ConversationStatus,
    MessageCreate,
    MessageRole
)

from services.conversation_service import ConversationService

logger = logging.getLogger(__name__)


class EscalamientoService:
    """Servicio para gestionar escalamiento de conversaciones a humanos"""
    
    # Palabras clave que indican intención de hablar con humano
    KEYWORDS_ESCALAMIENTO = [
        'humano', 'persona', 'operador', 'agente',
        'hablar con alguien', 'contacto', 'ayuda real',
        'representante', 'asesor', 'atención al cliente',
        'no entiendo', 'necesito ayuda', 'comunicarme con',
        'quiero hablar', 'puedo hablar', 'dame un'
    ]
    
    def __init__(self, db: Session):
        self.db = db
    
    def detectar_intencion_escalamiento(self, mensaje: str) -> bool:
        """
        Detecta si el usuario quiere hablar con un humano
        
        Args:
            mensaje: Texto del mensaje del usuario
            
        Returns:
            True si detecta intención de escalamiento
        """
        mensaje_lower = mensaje.lower()
        
        # Buscar palabras clave
        for keyword in self.KEYWORDS_ESCALAMIENTO:
            if keyword in mensaje_lower:
                logger.info(f"🔔 Keyword de escalamiento detectado: '{keyword}'")
                return True
        
        # Patrones regex más específicos
        patrones = [
            r'hablar\s+con\s+(un|una|el|la)?\s*(humano|persona|operador|agente)',
            r'necesito\s+(hablar|contactar|comunicarme)\s+con',
            r'quiero\s+(hablar|contactar|comunicarme)\s+con',
            r'puedo\s+hablar\s+con',
            r'dame\s+(un|una)\s*(operador|agente|persona)'
        ]
        
        for patron in patrones:
            if re.search(patron, mensaje_lower):
                logger.info(f"🔔 Patrón de escalamiento detectado: '{patron}'")
                return True
        
        return False
    



    async def escalar_conversacion(
        self,
        session_id: str,
        id_agente: int,
        motivo: str = "Solicitado por usuario"
    ) -> Dict[str, Any]:
        """
        Escala conversación a humano
        
        🔥 COMPORTAMIENTO:
        - Actualiza la conversación existente a estado escalada_humano
        - NO crea nueva conversación
        - Usa el mismo session_id
        """
        
        try:
            # ============================================
            # PASO 1: 🔥 ACTUALIZAR CONVERSACIÓN A ESCALADA
            # ============================================
            update_escalado = ConversationUpdate(
                estado=ConversationStatus.escalada_humano,
                requirio_atencion_humana=True
            )
            conversacion_actualizada = await ConversationService.update_conversation(
                session_id, 
                update_escalado
            )
            
            # Agregar mensaje de sistema indicando escalamiento
            mensaje_escalamiento = MessageCreate(
                role=MessageRole.system,
                content=f"🔔 Conversación escalada a atención humana. Motivo: {motivo}"
            )
            await ConversationService.add_message(session_id, mensaje_escalamiento)
            
            logger.info(f"✅ Conversación escalada en MongoDB: {session_id}")
            
            # ============================================
            # PASO 2: 🔥 ASIGNAR FUNCIONARIO Y NOTIFICAR
            # ============================================
            funcionario_asignado = None
            usuarios_notificados = 0
            
            try:
                # Obtener departamento del agente
                agente = self.db.query(AgenteVirtual).filter(
                    AgenteVirtual.id_agente == id_agente
                ).first()
                
                if not agente:
                    raise ValueError(f"Agente {id_agente} no encontrado")
                
                id_departamento = agente.id_departamento
                
                if not id_departamento:
                    logger.warning(f"⚠️ Agente {id_agente} no tiene departamento asignado")
                else:
                    # Obtener funcionarios disponibles del departamento
                    funcionarios = self._obtener_usuarios_departamento(id_departamento)
                    
                    if funcionarios:
                        funcionario_asignado = funcionarios[0]
                        
                        # Obtener nombre completo
                        nombre_completo = (
                            f"{funcionario_asignado.persona.nombre} "
                            f"{funcionario_asignado.persona.apellido}"
                        )
                        logger.info(f"🔍 Nombre: '{funcionario_asignado.persona.nombre}'")
                        logger.info(f"🔍 Apellido: '{funcionario_asignado.persona.apellido}'")
                        logger.info(f"🔍 Nombre completo: '{nombre_completo}'")
                        
                        # 🔥 ACTUALIZAR EN MONGODB con el funcionario asignado
                        update_asignacion = ConversationUpdate(
                            escalado_a_usuario_id=funcionario_asignado.id_usuario,
                            escalado_a_usuario_nombre=nombre_completo
                        )
                        await ConversationService.update_conversation(
                            session_id,  # ✅ CAMBIO: usar session_id en lugar de nuevo_session_id
                            update_asignacion
                        )
                        
                        logger.info(
                            f"✅ Conversación asignada a: {nombre_completo} "
                            f"(ID: {funcionario_asignado.id_usuario})"
                        )
                        
                        # Agregar mensaje de sistema en MongoDB
                        mensaje_asignacion = MessageCreate(
                            role=MessageRole.system,
                            content=f"📌 Conversación asignada a {nombre_completo}"
                        )
                        await ConversationService.add_message(session_id, mensaje_asignacion)  # ✅ CAMBIO
                        
                        # Crear notificación para el funcionario
                        usuarios_notificados = await self._crear_notificacion_escalamiento(
                            funcionario=funcionario_asignado,
                            session_id=session_id,  # ✅ CAMBIO
                            id_agente=id_agente,
                            agente_nombre=agente.nombre_agente,
                            motivo=motivo
                        )
                        
                    else:
                        logger.warning(f"⚠️ No hay funcionarios disponibles en departamento {id_departamento}")
                        
                        # Agregar mensaje de advertencia
                        mensaje_sin_funcionario = MessageCreate(
                            role=MessageRole.system,
                            content="⚠️ No hay funcionarios disponibles en este momento. La conversación quedará en espera."
                        )
                        await ConversationService.add_message(session_id, mensaje_sin_funcionario)  # ✅ CAMBIO
                        
            except Exception as e:
                logger.error(f"❌ Error en asignación de funcionario: {e}")
                import traceback
                traceback.print_exc()
            
            # ============================================
            # PASO 3: CREAR/ACTUALIZAR REGISTRO EN MYSQL (ConversacionSync)
            # ============================================
            try:
                # Buscar si ya existe registro en MySQL
                conversacion_sync = self.db.query(ConversacionSync).filter(
                    ConversacionSync.mongodb_conversation_id == session_id  # ✅ CAMBIO
                ).first()
                
                if conversacion_sync:
                    # Actualizar existente
                    conversacion_sync.estado = EstadoConversacionEnum.escalada_humano
                    conversacion_sync.requirio_atencion_humana = True
                    conversacion_sync.ultima_sincronizacion = datetime.utcnow()
                    logger.info(f"✅ ConversacionSync actualizada en MySQL: {conversacion_sync.id_conversacion_sync}")
                else:
                    # Crear nuevo registro si no existe
                    visitante = await self._obtener_o_crear_visitante(session_id)
                    
                    conversacion_sync = ConversacionSync(
                        mongodb_conversation_id=session_id,  # ✅ CAMBIO
                        id_visitante=visitante.id_visitante,
                        id_agente_inicial=id_agente,
                        id_agente_actual=id_agente,
                        estado=EstadoConversacionEnum.escalada_humano,
                        requirio_atencion_humana=True,
                        fecha_inicio=datetime.utcnow(),
                        ultima_sincronizacion=datetime.utcnow()
                    )
                    
                    self.db.add(conversacion_sync)
                    logger.info(f"✅ ConversacionSync creada en MySQL")
                
                self.db.commit()
                
            except Exception as e:
                logger.error(f"❌ Error en ConversacionSync MySQL: {e}")
                self.db.rollback()
            
            # ============================================
            # PASO 4: RETORNAR RESULTADO
            # ============================================
            return {
                "ok": True,
                "session_id": session_id,  # ✅ CAMBIO: un solo session_id
                "conversacion_id": str(conversacion_actualizada.id),
                "funcionario_asignado": {
                    "id": funcionario_asignado.id_usuario if funcionario_asignado else None,
                    "nombre": (
                        f"{funcionario_asignado.persona.nombre} "
                        f"{funcionario_asignado.persona.apellido}"
                    ) if funcionario_asignado else None
                },
                "usuarios_notificados": usuarios_notificados,
                "mensaje": "Conversación escalada y asignada correctamente." if funcionario_asignado else "Conversación escalada sin asignación (no hay funcionarios disponibles)."
            }
            
        except Exception as e:
            logger.error(f"❌ Error escalando conversación: {e}")
            self.db.rollback()
            raise




    async def _crear_notificacion_escalamiento(
        self,
        funcionario: Usuario,
        session_id: str,
        id_agente: int,
        agente_nombre: str,
        motivo: str
    ) -> int:
        """
        Crea notificación para el funcionario asignado
        
        Args:
            funcionario: Usuario funcionario
            session_id: ID de la sesión
            id_agente: ID del agente
            agente_nombre: Nombre del agente
            motivo: Motivo del escalamiento
            
        Returns:
            1 si se creó la notificación, 0 si hubo error
        """
        try:
            from models.notificacion_usuario import NotificacionUsuario, TipoNotificacionEnum
            
            # Obtener nombre del funcionario
            nombre_funcionario = f"{funcionario.persona.nombre} {funcionario.persona.apellido}"
    
            # Crear notificación
            notificacion = NotificacionUsuario(
                id_usuario=funcionario.id_usuario,
                id_agente=id_agente,
                tipo=TipoNotificacionEnum.urgente,
                titulo=f'Nueva conversación asignada - {agente_nombre}',
                mensaje=f'Se te ha asignado una conversación del agente {agente_nombre}. Motivo: {motivo}',
                icono='arrow-up-circle',
                url_accion=f'/conversaciones-escaladas/{session_id}',
                datos_adicionales=f'{{"session_id": "{session_id}", "id_agente": {id_agente}, "motivo": "{motivo}"}}',
                leida=False,
                fecha_creacion=datetime.utcnow()
            )
            
            self.db.add(notificacion)
            self.db.commit()
            
            logger.info(f"✅ Notificación creada para {nombre_funcionario} (ID: {funcionario.id_usuario})")
            
            # TODO: Aquí podrías agregar:
            # - Enviar email
            # - Enviar notificación push
            # - WebSocket broadcast al funcionario
            
            return 1
            
        except Exception as e:
            logger.error(f"❌ Error creando notificación: {e}")
            self.db.rollback()
            return 0








    
    async def _notificar_escalamiento(
        self,
        session_id: str,
        id_agente: int,
        motivo: str
    ) -> int:
        """
        Notifica a usuarios humanos sobre el escalamiento
        
        Returns:
            Número de usuarios notificados
        """
        try:
            logger.info(f"📢 Notificación de escalamiento: session={session_id}, agente={id_agente}")
            
            # TODO: Implementar sistema de notificaciones real
            # - Enviar email
            # - Enviar notificación push
            # - Enviar mensaje a Slack/Teams
            # - Crear tarea en sistema de tickets
            
            return 1  # Simulamos 1 usuario notificado
            
        except Exception as e:
            logger.error(f"❌ Error notificando escalamiento: {e}")
            return 0
    
    async def _obtener_o_crear_visitante(self, session_id: str) -> VisitanteAnonimo:
        """
        Obtiene o crea un visitante anónimo basado en el session_id
        
        Args:
            session_id: ID de sesión
            
        Returns:
            Instancia de VisitanteAnonimo
        """
        try:
            # Buscar visitante existente
            visitante = self.db.query(VisitanteAnonimo).filter(
                VisitanteAnonimo.identificador_sesion == session_id
            ).first()
            
            if not visitante:
                # Crear nuevo visitante
                visitante = VisitanteAnonimo(
                    identificador_sesion=session_id,
                    ip_origen="unknown",
                    user_agent="unknown",
                    ultima_visita=datetime.utcnow()
                )
                self.db.add(visitante)
                self.db.commit()
                self.db.refresh(visitante)
                
                logger.info(f"✅ Nuevo visitante creado: {visitante.id_visitante}")
            else:
                # Actualizar última visita si ya existe
                visitante.ultima_visita = datetime.utcnow()
                self.db.commit()
                
            return visitante
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo/creando visitante: {e}")
            self.db.rollback()
            raise
    
    # ============================================
    # 🔥 AUTO-FINALIZAR CONVERSACIONES INACTIVAS
    # ============================================
    async def finalizar_conversaciones_inactivas(
        self,
        timeout_minutos: int = 30
    ) -> Dict[str, Any]:
        """
        Finaliza conversaciones inactivas después de X minutos
        
        Args:
            timeout_minutos: Minutos de inactividad para finalizar
            
        Returns:
            Diccionario con estadísticas
        """
        
        try:
            # Calcular timestamp límite
            tiempo_limite = datetime.utcnow() - timedelta(minutes=timeout_minutos)
            
            # Buscar conversaciones activas o escaladas sin actividad
            conversaciones = await ConversationService.get_inactive_conversations(
                tiempo_limite=tiempo_limite,
                estados=[ConversationStatus.activa, ConversationStatus.escalada_humano]
            )
            
            finalizadas_mongo = 0
            finalizadas_mysql = 0
            
            for conv in conversaciones:
                try:
                    # 🔥 conv es un Dict, no un objeto Pydantic
                    session_id = conv['session_id']
                    conv_id = conv['_id']
                    
                    # Finalizar en MongoDB
                    update_data = ConversationUpdate(
                        estado=ConversationStatus.finalizada
                    )
                    await ConversationService.update_conversation(session_id, update_data)
                    
                    # Agregar mensaje de cierre
                    cierre_message = MessageCreate(
                        role=MessageRole.system,
                        content=f"Conversación finalizada automáticamente por inactividad ({timeout_minutos} minutos)"
                    )
                    await ConversationService.add_message(session_id, cierre_message)
                    
                    finalizadas_mongo += 1
                    logger.info(f"✅ Conversación MongoDB finalizada: {session_id}")
                    
                    # 🔥 Finalizar en MySQL (ConversacionSync)
                    # Buscar por session_id ya que ahora pueden ser más largos
                    conversacion_sync = self.db.query(ConversacionSync).filter(
                        ConversacionSync.mongodb_conversation_id == session_id
                    ).first()
                    
                    if conversacion_sync:
                        conversacion_sync.estado = EstadoConversacionEnum.finalizada
                        conversacion_sync.fecha_fin = datetime.utcnow()
                        conversacion_sync.ultima_sincronizacion = datetime.utcnow()
                        finalizadas_mysql += 1
                    
                except Exception as e:
                    session_id_safe = conv.get('session_id', 'unknown')
                    logger.error(f"❌ Error finalizando conversación {session_id_safe}: {e}")
            
            # Commit de cambios en MySQL
            if finalizadas_mysql > 0:
                self.db.commit()
            
            return {
                "ok": True,
                "conversaciones_finalizadas_mongo": finalizadas_mongo,
                "conversaciones_finalizadas_mysql": finalizadas_mysql,
                "tiempo_limite": tiempo_limite.isoformat(),
                "timeout_minutos": timeout_minutos
            }
            
        except Exception as e:
            logger.error(f"❌ Error finalizando conversaciones inactivas: {e}")
            self.db.rollback()
            raise
    
    # ============================================
    # MÉTODOS AUXILIARES
    # ============================================
    
    def _obtener_usuarios_departamento(self, id_departamento: int) -> List[Usuario]:
        """
        Obtiene UN usuario funcionario aleatorio del departamento
        Solo usuarios con nivel_jerarquia = 3 (Funcionario)
        """
        try:
            # Obtener TODOS los funcionarios del departamento
            funcionarios = self.db.query(Usuario).join(
                Persona, Usuario.id_persona == Persona.id_persona
            ).join(
                UsuarioRol, Usuario.id_usuario == UsuarioRol.id_usuario
            ).join(
                Rol, UsuarioRol.id_rol == Rol.id_rol
            ).filter(
                Persona.id_departamento == id_departamento,
                Usuario.estado == 'activo',
                Persona.estado == 'activo',
                UsuarioRol.activo == True,
                Rol.activo == True,
                Rol.nivel_jerarquia == 3  # Solo funcionarios
            ).distinct().all()
            
            if not funcionarios:
                logger.warning(f"No hay funcionarios disponibles en departamento {id_departamento}")
                return []
            
            # Seleccionar UNO aleatorio
            funcionario_seleccionado = random.choice(funcionarios)
            logger.info(f"✅ Funcionario seleccionado: {funcionario_seleccionado.username} (ID: {funcionario_seleccionado.id_usuario})")
            
            return [funcionario_seleccionado]
            
        except Exception as e:
            logger.error(f"Error obteniendo funcionario del departamento: {e}")
            return []
    
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
        """
        notificaciones = []
        
        try:
            for usuario in usuarios:
                notif = NotificacionUsuario(
                    id_usuario=usuario.id_usuario,
                    id_agente=id_agente,
                    tipo=TipoNotificacionEnum.urgente,
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
                await ConversationService.update_conversation(session_id, update_data)
            
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
        """
        try:
            query = self.db.query(ConversacionSync).filter(
                ConversacionSync.estado == EstadoConversacionEnum.escalada_humano
            )
            
            if solo_pendientes:
                query = query.filter(
                    ConversacionSync.requirio_atencion_humana == True
                )
            
            # Si hay filtro de departamento, join con Agente
            if id_departamento:
                query = query.join(
                    AgenteVirtual, 
                    ConversacionSync.id_agente_inicial == AgenteVirtual.id_agente
                ).filter(
                    AgenteVirtual.id_departamento == id_departamento
                )
            
            conversaciones = query.order_by(
                ConversacionSync.fecha_inicio.desc()
            ).limit(50).all()
            
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
