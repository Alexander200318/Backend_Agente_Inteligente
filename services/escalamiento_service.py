# services/escalamiento_service.py
"""
Servicio para escalar conversaciones a atención humana
Sistema SIMPLE con palabras clave y confirmación
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging
import uuid
import random

from models.agente_virtual import AgenteVirtual
from models.notificacion_usuario import NotificacionUsuario, TipoNotificacionEnum
from models.usuario import Usuario
from models.persona import Persona
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

_confirmaciones_pendientes_global = {}

class EscalamientoService:
    """Servicio para gestionar escalamiento de conversaciones a humanos"""
    
    # Palabras clave para detectar escalamiento
    KEYWORDS_ESCALAMIENTO = [
        'humano', 'persona', 'operador', 'agente',
        'hablar con alguien', 'contacto', 'ayuda real',
        'representante', 'asesor', 'atención al cliente'
    ]
    
    # Palabras para confirmar
    KEYWORDS_CONFIRMACION = [
        'si', 'sí', 'yes', 'ok', 'okay', 'vale', 'claro',
        'adelante', 'dale', 'confirmo', 'acepto', 'quiero'
    ]
    
    # Palabras para rechazar
    KEYWORDS_RECHAZO = [
        'no', 'nop', 'cancela', 'mejor no', 'no gracias',
        'olvida', 'dejalo', 'espera', 'ahora no'
    ]

    # 🔥🔥🔥 AGREGAR ESTO AQUÍ 🔥🔥🔥
    KEYWORDS_FINALIZAR_ESCALAMIENTO = [
        'finalizar escalamiento',
        'terminar escalamiento',
        'cancelar escalamiento',
        'volver al bot',
        'volver a la ia',
        'volver al agente virtual',
        'ya no necesito humano',
        'cancelar derivación',
        'cerrar escalamiento',
        'regresar al bot'
    ]
    
    def __init__(self, db: Session):
        self.db = db
        # Cache en memoria para pendientes de confirmación
        self._confirmaciones_pendientes = _confirmaciones_pendientes_global
    

    def detectar_intencion_escalamiento(self, mensaje: str) -> bool:
        """Detecta si el usuario quiere hablar con un humano"""
        mensaje_lower = mensaje.lower()
        
        # Frases más específicas
        frases_escalamiento = [
            # Directas
            'hablar con un humano',
            'hablar con una persona',
            'quiero hablar con alguien',
            'quiero un humano',
            'necesito un humano',
            'hablar con un asesor',
            'hablar con un representante',
            'hablar con soporte',
            'contactar con alguien',
            'pasame con alguien',

            # Instituto / académico
            'hablar con administración',
            'hablar con secretaría',
            'hablar con un asesor académico',
            'hablar con un coordinador',
            'hablar con un profesor',
            'hablar con un encargado',
            'hablar con un tutor',


            # Frustración / bot no ayuda
            'quiero hablar con alguien real',
            'quiero atención humana',


            # Indirectas comunes
            'necesito ayuda personalizada',
            'quiero que me atiendan',
            'necesito hablar con alguien',
            'quiero soporte'
        ]
        
        for frase in frases_escalamiento:
            if frase in mensaje_lower:
                logger.info(f"🔔 Frase de escalamiento detectada: '{frase}'")
                return True
        
        return False
    
    def detectar_confirmacion(self, mensaje: str) -> str:
        """
        Detecta si el usuario confirma o rechaza
        
        Returns:
            'confirmar' | 'rechazar' | 'indefinido'
        """
        mensaje_lower = mensaje.lower().strip()
        
        # Primero buscar rechazo
        for keyword in self.KEYWORDS_RECHAZO:
            if keyword in mensaje_lower:
                logger.info(f"❌ Keyword de rechazo detectado: '{keyword}'")
                return 'rechazar'
        
        # Luego buscar confirmación
        for keyword in self.KEYWORDS_CONFIRMACION:
            if keyword in mensaje_lower:
                logger.info(f"✅ Keyword de confirmación detectado: '{keyword}'")
                return 'confirmar'
        
        logger.warning(f"⚠️ Respuesta indefinida: '{mensaje_lower}'")
        return 'indefinido'
    
    # Método para agregar lógica adicional
    def detectar_finalizacion_escalamiento(self, mensaje: str) -> bool:
        """
        Detecta si el usuario quiere finalizar el escalamiento
        y volver al agente IA
        """
        mensaje_lower = mensaje.lower().strip()
        
        logger.info(f"🔍 Verificando finalización de escalamiento: '{mensaje}'")
        
        for keyword in self.KEYWORDS_FINALIZAR_ESCALAMIENTO:
            if keyword in mensaje_lower:
                logger.info(f"🔔 Keyword de finalización detectado: '{keyword}'")
                return True
        
        logger.info(f"✅ No se detectó intención de finalizar escalamiento")
        return False

    # Método para procesamiento posterior
    async def finalizar_escalamiento(
        self,
        session_id: str,
        motivo: str = "Finalizado por usuario"
    ) -> Dict[str, Any]:
        """
        Finaliza un escalamiento activo y devuelve la conversación al agente IA
        """
        try:
            logger.info(f"=" * 80)
            logger.info(f"🔚 FINALIZANDO ESCALAMIENTO")
            logger.info(f"   - Session ID: {session_id}")
            logger.info(f"   - Motivo: {motivo}")
            logger.info(f"=" * 80)
            
            # 1. Actualizar estado en MongoDB
            update_finalizar = ConversationUpdate(
                estado=ConversationStatus.activa,  # Volver a activa
                requirio_atencion_humana=True  # Mantener que requirió atención
            )
            
            conversacion_actualizada = await ConversationService.update_conversation(
                session_id,
                update_finalizar
            )
            
            # 2. Agregar mensaje de sistema en MongoDB
            mensaje_finalizacion = MessageCreate(
                role=MessageRole.system,
                content=f"✅ Escalamiento finalizado. {motivo}. La conversación continúa con el agente virtual."
            )
            await ConversationService.add_message(session_id, mensaje_finalizacion)
            
            logger.info(f"✅ Estado actualizado en MongoDB: activa")
            
            # 3. Actualizar en MySQL (Conversacion_Sync)
            try:
                conversacion_sync = self.db.query(ConversacionSync).filter(
                    ConversacionSync.mongodb_conversation_id == session_id
                ).first()
                
                if conversacion_sync:
                    conversacion_sync.estado = EstadoConversacionEnum.activa
                    conversacion_sync.ultima_sincronizacion = datetime.utcnow()
                    self.db.commit()
                    
                    logger.info(f"✅ Estado actualizado en MySQL: activa")
                else:
                    logger.warning(f"⚠️ No se encontró ConversacionSync para {session_id}")
                    
            except Exception as e:
                logger.error(f"❌ Error actualizando MySQL: {e}")
                self.db.rollback()
            
            logger.info(f"=" * 80)
            logger.info(f"✅ ESCALAMIENTO FINALIZADO EXITOSAMENTE")
            logger.info(f"=" * 80)
            
            return {
                "ok": True,
                "session_id": session_id,
                "conversacion_id": str(conversacion_actualizada.id),
                "nuevo_estado": "activa",
                "mensaje": "Escalamiento finalizado. Conversación devuelta al agente virtual."
            }
            
        except Exception as e:
            logger.error(f"=" * 80)
            logger.error(f"❌ ERROR FINALIZANDO ESCALAMIENTO")
            logger.error(f"   - Session ID: {session_id}")
            logger.error(f"   - Error: {str(e)}")
            logger.error(f"=" * 80)
            import traceback
            logger.error(traceback.format_exc())
            
            self.db.rollback()
            raise



    def marcar_confirmacion_pendiente(self, session_id: str):
        """Marca que una sesión tiene confirmación pendiente"""
        self._confirmaciones_pendientes[session_id] = datetime.utcnow()
        logger.info(f"⏳ Confirmación pendiente para session: {session_id}")
    
    def tiene_confirmacion_pendiente(self, session_id: str) -> bool:
        """Verifica si hay confirmación pendiente (válida por 5 minutos)"""
        if session_id not in self._confirmaciones_pendientes:
            return False
        
        timestamp = self._confirmaciones_pendientes[session_id]
        tiempo_transcurrido = (datetime.utcnow() - timestamp).total_seconds()
        
        # Expirar después de 5 minutos
        if tiempo_transcurrido > 300:
            del self._confirmaciones_pendientes[session_id]
            logger.info(f"⏰ Confirmación expirada para session: {session_id}")
            return False
        
        return True
    
    def limpiar_confirmacion_pendiente(self, session_id: str):
        """Limpia la confirmación pendiente"""
        if session_id in self._confirmaciones_pendientes:
            del self._confirmaciones_pendientes[session_id]
            logger.info(f"🗑️ Confirmación limpiada para session: {session_id}")
    
    def obtener_mensaje_confirmacion(self, agente_nombre: str) -> str:
        """Mensaje de solicitud de confirmación"""
        return f"""🤝 **¿Deseas hablar con un agente humano?**

Te conectaré con una persona real del equipo de {agente_nombre}.

⚠️ **Ten en cuenta:**
• Esta conversación será registrada
• Tus datos serán almacenados de forma segura
• Un agente te atenderá en breve

**¿Confirmas que deseas continuar?**

Responde:
✅ **"Sí"** para conectar
❌ **"No"** para continuar aquí"""
    
    def obtener_mensaje_confirmado(self) -> str:
        """Mensaje cuando el usuario confirma"""
        return """🔔 **Conectado con atención humana**

Un agente especializado se conectará contigo en breve. **Por favor espera...**

💡 Si deseas volver al agente virtual en cualquier momento, solo **escribe:** finalizar escalamiento o volver al bot"""
    
    def obtener_mensaje_cancelado(self) -> str:
        """Mensaje cuando el usuario cancela"""
        return """✅ **Seguimos aquí para ayudarte**

Entendido, **continuaremos resolviendo tu problema** juntos.

¿En qué más puedo asistirte? 😊"""

    def obtener_mensaje_escalamiento_activo(self, nombre_agente: str) -> str:
        """Mensaje cuando el escalamiento está activo y el agente se conecta"""
        return f"""🔔 **Conectado con atención humana**

**{nombre_agente}** te atenderá en breve.

💡 Si deseas volver al agente virtual en cualquier momento, solo **escribe:** finalizar escalamiento o volver al bot"""

    def obtener_mensaje_finalizacion_escalamiento(self) -> str:
        """Mensaje cuando se finaliza el escalamiento"""
        return """✅ **Escalamiento finalizado**

**Has vuelto al agente virtual.** Ahora puedes continuar tu conversación normalmente. 😊

**Recuerda:** Desde ahora tus mensajes serán procesados por la IA."""

    def obtener_modal_confirmacion(self) -> dict:
        """Estructura del modal de confirmación de escalamiento para el widget"""
        return {
            "type": "confirmacion_escalamiento_modal",
            "titulo": "🤝 Hablar con un agente",
            "descripcion": "¿Deseas conectar con un agente humano para recibir atención personalizada?"
        }

    async def escalar_conversacion(
        self,
        session_id: str,
        id_agente: int,
        motivo: str = "Solicitado por usuario"
    ) -> Dict[str, Any]:
        """Escala conversación a humano"""
        try:
            # Actualizar conversación a escalada
            update_escalado = ConversationUpdate(
                estado=ConversationStatus.escalada_humano,
                requirio_atencion_humana=True
            )
            conversacion_actualizada = await ConversationService.update_conversation(
                session_id, 
                update_escalado
            )
            
            mensaje_escalamiento = MessageCreate(
                role=MessageRole.system,
                content=f"🔔 Conversación escalada a atención humana. Motivo: {motivo}"
            )
            await ConversationService.add_message(session_id, mensaje_escalamiento)
            
            logger.info(f"✅ Conversación escalada en MongoDB: {session_id}")
            
            # Asignar funcionario
            funcionario_asignado = None
            usuarios_notificados = 0
                        
            try:
                agente = self.db.query(AgenteVirtual).filter(
                    AgenteVirtual.id_agente == id_agente
                ).first()
                
                if not agente:
                    raise ValueError(f"Agente {id_agente} no encontrado")
                
                id_departamento = agente.id_departamento
                
                if id_departamento:
                    funcionarios = self._obtener_usuarios_departamento(id_departamento)
                    
                    # 🔥 NUEVO: Verificar si hay funcionarios disponibles
                    if not funcionarios:
                        # ❌ NO HAY FUNCIONARIOS DISPONIBLES
                        #logger.error(f"=" * 80)
                        logger.error(f"❌ SIN FUNCIONARIOS DISPONIBLES")
                        #logger.error(f"   - Departamento: {id_departamento}")
                        #logger.error(f"   - Agente: {agente.nombre_agente}")
                        #logger.error(f"=" * 80)
                        
                        # Agregar mensaje al usuario
                        #mensaje_sin_disponibles = MessageCreate(
                        #    role=MessageRole.system,
                        #    content=(
                        #        "⚠️ **No hay encargados disponibles en este momento**\n\n"
                        #        f"Actualmente no hay personal disponible en el departamento de {agente.nombre_agente}.\n\n"
                        #        "Por favor, intenta nuevamente más tarde o contacta con nosotros por otros medios.\n\n"
                        #        "Disculpa las molestias. 🙏"
                        #    )
                        #)
                        #await ConversationService.add_message(session_id, mensaje_sin_disponibles)
                        
                        # 🔥 REVERTIR ESTADO DE CONVERSACIÓN
                        update_revertir = ConversationUpdate(
                            estado=ConversationStatus.activa,
                            requirio_atencion_humana=False
                        )
                        await ConversationService.update_conversation(session_id, update_revertir)
                        
                        # Retornar error controlado
                        return {
                            "ok": False,
                            "session_id": session_id,
                            "error": "no_disponibles",
                            "mensaje": "No hay funcionarios disponibles en este departamento",
                            "funcionario_asignado": None,
                            "usuarios_notificados": 0
                        }
                    
                    # ✅ SÍ HAY FUNCIONARIOS DISPONIBLES
                    funcionario_asignado = funcionarios[0]
                    
                    nombre_completo = (
                        f"{funcionario_asignado.persona.nombre} "
                        f"{funcionario_asignado.persona.apellido}"
                    )
                    
                    update_asignacion = ConversationUpdate(
                        escalado_a_usuario_id=funcionario_asignado.id_usuario,
                        escalado_a_usuario_nombre=nombre_completo
                    )
                    await ConversationService.update_conversation(
                        session_id,
                        update_asignacion
                    )
                    
                    logger.info(f"✅ Conversación asignada a: {nombre_completo}")
                    
                    mensaje_asignacion = MessageCreate(
                        role=MessageRole.system,
                        content=f"📌 Conversación asignada a {nombre_completo}"
                    )
                    await ConversationService.add_message(session_id, mensaje_asignacion)
                    
                    usuarios_notificados = await self._crear_notificacion_escalamiento(
                        funcionario=funcionario_asignado,
                        session_id=session_id,
                        id_agente=id_agente,
                        agente_nombre=agente.nombre_agente,
                        motivo=motivo
                    )
                            
            except Exception as e:
                logger.error(f"❌ Error en asignación de funcionario: {e}")

            # Crear/actualizar registro en MySQL
            try:
                conversacion_sync = self.db.query(ConversacionSync).filter(
                    ConversacionSync.mongodb_conversation_id == session_id
                ).first()
                
                if conversacion_sync:
                    conversacion_sync.estado = EstadoConversacionEnum.escalada_humano
                    conversacion_sync.requirio_atencion_humana = True
                    conversacion_sync.ultima_sincronizacion = datetime.utcnow()
                else:
                    visitante = await self._obtener_o_crear_visitante(session_id)
                    
                    conversacion_sync = ConversacionSync(
                        mongodb_conversation_id=session_id,
                        id_visitante=visitante.id_visitante,
                        id_agente_inicial=id_agente,
                        id_agente_actual=id_agente,
                        estado=EstadoConversacionEnum.escalada_humano,
                        requirio_atencion_humana=True,
                        fecha_inicio=datetime.utcnow(),
                        ultima_sincronizacion=datetime.utcnow()
                    )
                    
                    self.db.add(conversacion_sync)
                
                self.db.commit()
                
            except Exception as e:
                logger.error(f"❌ Error en ConversacionSync MySQL: {e}")
                self.db.rollback()
            
            return {
                "ok": True,
                "session_id": session_id,
                "conversacion_id": str(conversacion_actualizada.id),
                "funcionario_asignado": {
                    "id": funcionario_asignado.id_usuario if funcionario_asignado else None,
                    "nombre": (
                        f"{funcionario_asignado.persona.nombre} "
                        f"{funcionario_asignado.persona.apellido}"
                    ) if funcionario_asignado else None
                },
                "usuarios_notificados": usuarios_notificados,
                "mensaje": "Conversación escalada correctamente." if funcionario_asignado else "Conversación escalada sin asignación."
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
        """Crea notificación para el funcionario asignado"""
        try:
            nombre_funcionario = f"{funcionario.persona.nombre} {funcionario.persona.apellido}"
    
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
            
            logger.info(f"✅ Notificación creada para {nombre_funcionario}")
            return 1
            
        except Exception as e:
            logger.error(f"❌ Error creando notificación: {e}")
            self.db.rollback()
            return 0

    async def _obtener_o_crear_visitante(self, session_id: str) -> VisitanteAnonimo:
        """Obtiene o crea un visitante anónimo"""
        try:
            visitante = self.db.query(VisitanteAnonimo).filter(
                VisitanteAnonimo.identificador_sesion == session_id
            ).first()
            
            if not visitante:
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
                visitante.ultima_visita = datetime.utcnow()
                self.db.commit()
                
            return visitante
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo/creando visitante: {e}")
            self.db.rollback()
            raise
    
    async def finalizar_conversaciones_inactivas(
        self,
        timeout_minutos: int = 1
    ) -> Dict[str, Any]:
        """Finaliza conversaciones inactivas"""
        try:
            tiempo_limite = datetime.utcnow() - timedelta(minutes=timeout_minutos)
            
            conversaciones = await ConversationService.get_inactive_conversations(
                tiempo_limite=tiempo_limite,
                estados=[ConversationStatus.activa, ConversationStatus.escalada_humano]
            )
            
            finalizadas_mongo = 0
            finalizadas_mysql = 0
            
            for conv in conversaciones:
                try:
                    session_id = conv['session_id']
                    
                    update_data = ConversationUpdate(
                        estado=ConversationStatus.finalizada
                    )
                    await ConversationService.update_conversation(session_id, update_data)
                    
                    cierre_message = MessageCreate(
                        role=MessageRole.system,
                        content=f"Conversación finalizada por inactividad ({timeout_minutos} minutos)"
                    )
                    await ConversationService.add_message(session_id, cierre_message)
                    
                    finalizadas_mongo += 1
                    
                    conversacion_sync = self.db.query(ConversacionSync).filter(
                        ConversacionSync.mongodb_conversation_id == session_id
                    ).first()
                    
                    if conversacion_sync:
                        conversacion_sync.estado = EstadoConversacionEnum.finalizada
                        conversacion_sync.fecha_fin = datetime.utcnow()
                        conversacion_sync.ultima_sincronizacion = datetime.utcnow()
                        finalizadas_mysql += 1
                    
                except Exception as e:
                    logger.error(f"❌ Error finalizando conversación: {e}")
            
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
    

    def _obtener_usuarios_departamento(self, id_departamento: int) -> List[Usuario]:
        """
        Obtiene UN funcionario DISPONIBLE del departamento
        
        🔥 NUEVO COMPORTAMIENTO:
        - Solo funcionarios con disponible=True
        - Del mismo departamento del agente
        - Con rol activo de nivel 3 (funcionario)
        - Estado activo
        
        Returns:
            List[Usuario]: Lista con 1 funcionario disponible, o lista vacía si no hay
        """
        try:
            logger.info(f"🔍 Buscando funcionarios DISPONIBLES en departamento {id_departamento}")
            
            # 🔥 QUERY CON FILTRO DE DISPONIBILIDAD
            funcionarios_disponibles = self.db.query(Usuario).join(
                Persona, Usuario.id_persona == Persona.id_persona
            ).join(
                UsuarioRol, Usuario.id_usuario == UsuarioRol.id_usuario
            ).join(
                Rol, UsuarioRol.id_rol == Rol.id_rol
            ).filter(
                # 🔥 FILTROS CRÍTICOS
                Persona.id_departamento == id_departamento,  # Mismo departamento
                Usuario.disponible == True,                  # ✅ DISPONIBLE
                Usuario.estado == 'activo',                  # Usuario activo
                Persona.estado == 'activo',                  # Persona activa
                UsuarioRol.activo == True,                   # Rol asignado activo
                Rol.activo == True,                          # Rol existe y activo
                Rol.nivel_jerarquia == 3                     # Solo funcionarios
            ).distinct().all()
            
            # 🔥 LOGS DETALLADOS
            logger.info(f"=" * 80)
            logger.info(f"📊 RESULTADO BÚSQUEDA DE FUNCIONARIOS")
            logger.info(f"   - Departamento: {id_departamento}")
            logger.info(f"   - Funcionarios disponibles encontrados: {len(funcionarios_disponibles)}")
            
            if funcionarios_disponibles:
                for i, func in enumerate(funcionarios_disponibles, 1):
                    logger.info(f"   [{i}] {func.username} (ID: {func.id_usuario}) - {func.persona.nombre} {func.persona.apellido}")
            else:
                logger.warning(f"   ⚠️ NO HAY FUNCIONARIOS DISPONIBLES")
            
            logger.info(f"=" * 80)
            
            # 🔥 RETORNAR VACÍO SI NO HAY DISPONIBLES
            if not funcionarios_disponibles:
                logger.warning(f"❌ No hay funcionarios DISPONIBLES en departamento {id_departamento}")
                return []
            
            # 🔥 SELECCIONAR ALEATORIAMENTE ENTRE LOS DISPONIBLES
            funcionario_seleccionado = random.choice(funcionarios_disponibles)
            
            logger.info(f"=" * 80)
            logger.info(f"✅ FUNCIONARIO SELECCIONADO")
            logger.info(f"   - Username: {funcionario_seleccionado.username}")
            logger.info(f"   - ID: {funcionario_seleccionado.id_usuario}")
            logger.info(f"   - Nombre: {funcionario_seleccionado.persona.nombre} {funcionario_seleccionado.persona.apellido}")
            logger.info(f"   - Departamento: {funcionario_seleccionado.persona.id_departamento}")
            logger.info(f"   - Disponible: {funcionario_seleccionado.disponible}")
            logger.info(f"=" * 80)
            
            return [funcionario_seleccionado]
            
        except Exception as e:
            logger.error(f"=" * 80)
            logger.error(f"❌ ERROR OBTENIENDO FUNCIONARIO")
            logger.error(f"   - Departamento: {id_departamento}")
            logger.error(f"   - Error: {str(e)}")
            logger.error(f"=" * 80)
            import traceback
            logger.error(traceback.format_exc())
            return []

    
    async def responder_como_humano(
        self,
        session_id: str,
        mensaje: str,
        id_usuario: int,
        nombre_usuario: str
    ) -> Dict[str, Any]:
        """Agrega respuesta de un humano"""
        try:
            message_data = MessageCreate(
                role=MessageRole.human_agent,
                content=mensaje,
                user_id=id_usuario,
                user_name=nombre_usuario
            )
            
            conversation = await ConversationService.add_message(session_id, message_data)
            
            if not conversation.metadata.fecha_atencion_humana:
                update_data = ConversationUpdate(
                    escalado_a_usuario_id=id_usuario,
                    escalado_a_usuario_nombre=nombre_usuario
                )
                await ConversationService.update_conversation(session_id, update_data)
            
            logger.info(f"💬 Respuesta humana: {nombre_usuario} → {session_id}")
            
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
        """Obtiene conversaciones escaladas"""
        try:
            query = self.db.query(ConversacionSync).filter(
                ConversacionSync.estado == EstadoConversacionEnum.escalada_humano
            )
            
            if solo_pendientes:
                query = query.filter(
                    ConversacionSync.requirio_atencion_humana == True
                )
            
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
            
            logger.info(f"📋 Conversaciones escaladas: {len(conversaciones)}")
            
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
        
    # services/escalamiento_service.py
    class EscalamientoService:
        # ... código existente ...
        
        # 🔥 NUEVO: Keywords para finalizar escalamiento
        KEYWORDS_FINALIZAR_ESCALAMIENTO = [
            'finalizar escalamiento',
            'terminar escalamiento',
            'cancelar escalamiento',
            'volver al bot',
            'volver a la ia',
            'volver al agente virtual',
            'ya no necesito humano',
            'cancelar derivación',
            'cerrar escalamiento',
            'regresar al bot'
        ]
        
        def detectar_finalizacion_escalamiento(self, mensaje: str) -> bool:
            """
            Detecta si el usuario quiere finalizar el escalamiento
            y volver al agente IA
            """
            mensaje_lower = mensaje.lower().strip()
            
            logger.info(f"🔍 Verificando finalización de escalamiento: '{mensaje}'")
            
            for keyword in self.KEYWORDS_FINALIZAR_ESCALAMIENTO:
                if keyword in mensaje_lower:
                    logger.info(f"🔔 Keyword de finalización detectado: '{keyword}'")
                    return True
            
            return False
        
        async def finalizar_escalamiento(
            self,
            session_id: str,
            motivo: str = "Finalizado por usuario"
        ) -> Dict[str, Any]:
            """
            Finaliza un escalamiento activo y devuelve la conversación al agente IA
            """
            try:
                logger.info(f"=" * 80)
                logger.info(f"🔚 FINALIZANDO ESCALAMIENTO")
                logger.info(f"   - Session ID: {session_id}")
                logger.info(f"   - Motivo: {motivo}")
                logger.info(f"=" * 80)
                
                # 1. Actualizar estado en MongoDB
                update_finalizar = ConversationUpdate(
                    estado=ConversationStatus.activa,  # Volver a activa
                    requirio_atencion_humana=True  # Mantener que requirió atención
                )
                
                conversacion_actualizada = await ConversationService.update_conversation(
                    session_id,
                    update_finalizar
                )
                
                # 2. Agregar mensaje de sistema en MongoDB
                mensaje_finalizacion = MessageCreate(
                    role=MessageRole.system,
                    content=f"✅ Escalamiento finalizado. {motivo}. La conversación continúa con el agente virtual."
                )
                await ConversationService.add_message(session_id, mensaje_finalizacion)
                
                logger.info(f"✅ Estado actualizado en MongoDB: activa")
                
                # 3. Actualizar en MySQL (Conversacion_Sync)
                try:
                    conversacion_sync = self.db.query(ConversacionSync).filter(
                        ConversacionSync.mongodb_conversation_id == session_id
                    ).first()
                    
                    if conversacion_sync:
                        conversacion_sync.estado = EstadoConversacionEnum.activa
                        conversacion_sync.ultima_sincronizacion = datetime.utcnow()
                        self.db.commit()
                        
                        logger.info(f"✅ Estado actualizado en MySQL: activa")
                    else:
                        logger.warning(f"⚠️ No se encontró ConversacionSync para {session_id}")
                        
                except Exception as e:
                    logger.error(f"❌ Error actualizando MySQL: {e}")
                    self.db.rollback()
                
                logger.info(f"=" * 80)
                logger.info(f"✅ ESCALAMIENTO FINALIZADO EXITOSAMENTE")
                logger.info(f"=" * 80)
                
                return {
                    "ok": True,
                    "session_id": session_id,
                    "conversacion_id": str(conversacion_actualizada.id),
                    "nuevo_estado": "activa",
                    "mensaje": "Escalamiento finalizado. Conversación devuelta al agente virtual."
                }
                
            except Exception as e:
                logger.error(f"=" * 80)
                logger.error(f"❌ ERROR FINALIZANDO ESCALAMIENTO")
                logger.error(f"   - Session ID: {session_id}")
                logger.error(f"   - Error: {str(e)}")
                logger.error(f"=" * 80)
                import traceback
                logger.error(traceback.format_exc())
                
                self.db.rollback()
                raise