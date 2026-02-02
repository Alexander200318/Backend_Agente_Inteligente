# services/escalamiento_service.py
"""
Servicio para escalar conversaciones a atenciÃ³n humana
Sistema SIMPLE con palabras clave y confirmaciÃ³n
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
        # Palabras bÃ¡sicas
        'humano', 'persona', 'operador', 'agente',
        'hablar con alguien', 'contacto', 'ayuda real',
        'representante', 'asesor', 'atenciÃ³n al cliente',
        
        # Variaciones de "hablar con"
        'quiero hablar con una persona',
        'quiero hablar con un humano',
        'hablar con una persona',
        'hablar con un humano',
        'conectar con soporte',
        'comunicarme con soporte',
        'pasar con alguien',
        'transferencia',
        'derivar',
        'derivarme',
        'redirigir',
        
        # Departamentos y personas
        'departamento',
        'supervisor',
        'supervisora',
        'gerente',
        'jefe',
        'encargado',
        'encargada',
        'director',
        'directora',
        'administrador',
        'administradora',
        
        # Tipos de soporte
        'servicio al cliente',
        'atenciÃ³n al cliente',
        'servicio tÃ©cnico',
        'soporte tÃ©cnico',
        'atenciÃ³n prioritaria',
        'soporte vip',
        'urgente',
        'problema serio',
        'asunto importante',
        
        # Complejidad
        'no entiendo',
        'no entiendo nada',
        'esto no funciona',
        'no me sirve',
        'no funciona',
        'estÃ¡ roto',
        'un error',
        'hay un fallo',
        'problema tÃ©cnico',
        'error tÃ©cnico',
        
        # Reclamaciones y quejas
        'reclamaciÃ³n',
        'queja',
        'reclamo',
        'me quejo',
        'no estoy satisfecho',
        'no estoy satisfecha',
        'insatisfecho',
        'insatisfecha',
        'esto es inaceptable',
        
        # Intentos previos
        'intentÃ© antes',
        'ya lo intentÃ©',
        'volver a intentar',
        'no funciona eso',
        'ya no sirve',
        'sigue sin funcionar',
        
        # Necesidades especÃ­ficas
        'ayuda especial',
        'ayuda humana',
        'asistencia real',
        'asistencia humana',
        'necesito ayuda real',
        'necesito ayuda de verdad',
        'necesito hablar con alguien',
        'preciso hablar con alguien',
        
        # Idioma y comunicaciÃ³n
        'habla espaÃ±ol',
        'hablan espaÃ±ol',
        'en espaÃ±ol',
        'espaÃ±ol correctamente',
        
        # Urgencia
        'es urgente',
        'urgencia',
        'rÃ¡pido',
        'lo antes posible',
        'asap',
        'ya',
        
        # Solicitud directa
        'pÃ¡same',
        'pÃ¡samelo',
        'pÃ¡same con',
        'pÃ¡seme',
        'quiero hablar',
        'prefiero hablar',
        'deseo hablar',
        'quisiera hablar',
        'me gustarÃ­a hablar',
        
        # InsatisfacciÃ³n
        'estoy harto',
        'estoy cansado',
        'tengo paciencia',
        'cansada',
        'ya no aguanto',
        'esto me estresa',
        'esto es molesto',
        
        # Escalamiento automÃ¡tico
        'problema',
        'ayuda',
        'explicar',
        'entender',
        'dudas',
        'preguntas',
        'confusiÃ³n',
        
        # Variaciones formales
        'podrÃ­a hablar con',
        'Â¿podrÃ­a hablar con',
        'quisiera hablar con',
        'Â¿me pasa con',
        'comunÃ­came con',
        'contactame con',
        'contacto con',
        'comunÃ­cate conmigo',
        'llama',
        'llamada',
        'llamada telefÃ³nica'
    ]
    
    # Palabras para confirmar
    KEYWORDS_CONFIRMACION = [
        'si', 'sÃ­', 'yes', 'ok', 'okay', 'vale', 'claro',
        'adelante', 'dale', 'confirmo', 'acepto', 'quiero'
    ]
    
    # Palabras para rechazar
    KEYWORDS_RECHAZO = [
        'no', 'nop', 'cancela', 'mejor no', 'no gracias',
        'olvida', 'dejalo', 'espera', 'ahora no'
    ]

    # ðŸ”¥ðŸ”¥ðŸ”¥ AGREGAR ESTO AQUÃ ðŸ”¥ðŸ”¥ðŸ”¥
    KEYWORDS_FINALIZAR_ESCALAMIENTO = [
        'finalizar escalamiento',
        'terminar escalamiento',
        'cancelar escalamiento',
        'volver al bot',
        'volver a la ia',
        'volver al agente virtual',
        'ya no necesito humano',
        'cancelar derivaciÃ³n',
        'cerrar escalamiento',
        'regresar al bot'
    ]
    
    def __init__(self, db: Session):
        self.db = db
        # Cache en memoria para pendientes de confirmaciÃ³n
        self._confirmaciones_pendientes = _confirmaciones_pendientes_global
    

    def detectar_intencion_escalamiento(self, mensaje: str) -> bool:
        """Detecta si el usuario quiere hablar con un humano"""
        mensaje_lower = mensaje.lower()
        
        # Frases mÃ¡s especÃ­ficas
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
            'conectame con alguien',
            'quiero hablar con una persona',
            'necesito persona real',
            'quiero persona real',
            'necesito atenciÃ³n humana',
            'ayuda de un humano',
            'quiero hablar con un agente',
            'necesito hablar con agente',
            'quiero un agente',
            'pasame con un agente',
            'dame un agente',

            # Variantes comunes
            'hablar con un especialista',
            'hablar con un experto',
            'hablar con un funcionario',
            'hablar con un empleado',
            'hablar con la oficina',
            'quiero atenciÃ³n personalizada',
            'necesito atenciÃ³n personalizada',
            'quiero hablar en directo',
            'necesito hablar en directo',
            'conectame con alguien',
            'me conectas',
            'me transfieren',
            'transferencia a agente',
            'quiero transferencia',

            # Instituto / acadÃ©mico
            'hablar con administraciÃ³n',
            'hablar con secretarÃ­a',
            'hablar con un asesor acadÃ©mico',
            'hablar con un coordinador',
            'hablar con un profesor',
            'hablar con un encargado',
            'hablar con un tutor',
            'hablar con direcciÃ³n',
            'hablar con decanato',
            'hablar con rectorado',
            'quiero hablar con direcciÃ³n',

            # FrustraciÃ³n / bot no ayuda
            'quiero hablar con alguien real',
            'quiero atenciÃ³n humana',
            'esto no funciona',
            'no entiendes',
            'no comprendes',
            'no me ayudas',
            'no me sirve',
            'eres un bot',
            'pareces un bot',
            'hablo con un bot',
            'eres un robot',
            'no soy robot',
            'no es suficiente',
            'quiero mÃ¡s ayuda',
            'necesito mÃ¡s ayuda',
            'no puedo seguir con esto',
            'no puedo confiar en eso',

            # Indirectas comunes
            'necesito ayuda personalizada',
            'quiero que me atiendan',
            'necesito hablar con alguien',
            'quiero soporte',
            'necesito soporte',
            'quiero informaciÃ³n de verdad',
            'necesito informaciÃ³n real',
            'quiero una soluciÃ³n real',
            'hablame claro',
            'necesito claridad',
            'quiero hablar directo',
            'no entiendo',
            'explÃ­came bien',
            'explÃ­came mejor',
            'quiero explicaciÃ³n',

            # Urgencia/Problemas
            'es urgente',
            'necesito rÃ¡pido',
            'ayuda urgente',
            'problema grave',
            'tengo un problema grave',
            'esto es importante',
            'necesito ayuda ya',
            'no puede esperar',
            'es importante',

            # TÃ©cnicas
            'falla',
            'bug',
            'error',
            'no funciona',
            'rotura',
            'se cayÃ³',
            'se rompiÃ³',
            'fallo',
        ]
        
        for frase in frases_escalamiento:
            if frase in mensaje_lower:
                logger.info(f"ðŸ”” Frase de escalamiento detectada: '{frase}'")
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
                logger.info(f"âŒ Keyword de rechazo detectado: '{keyword}'")
                return 'rechazar'
        
        # Luego buscar confirmaciÃ³n
        for keyword in self.KEYWORDS_CONFIRMACION:
            if keyword in mensaje_lower:
                logger.info(f"âœ… Keyword de confirmaciÃ³n detectado: '{keyword}'")
                return 'confirmar'
        
        logger.warning(f"âš ï¸ Respuesta indefinida: '{mensaje_lower}'")
        return 'indefinido'
    
    # MÃ©todo para agregar lÃ³gica adicional
    def detectar_finalizacion_escalamiento(self, mensaje: str) -> bool:
        """
        Detecta si el usuario quiere finalizar el escalamiento
        y volver al agente IA
        """
        mensaje_lower = mensaje.lower().strip()
        
        logger.info(f"ðŸ” Verificando finalizaciÃ³n de escalamiento: '{mensaje}'")
        
        for keyword in self.KEYWORDS_FINALIZAR_ESCALAMIENTO:
            if keyword in mensaje_lower:
                logger.info(f"ðŸ”” Keyword de finalizaciÃ³n detectado: '{keyword}'")
                return True
        
        logger.info(f"âœ… No se detectÃ³ intenciÃ³n de finalizar escalamiento")
        return False

    # MÃ©todo para procesamiento posterior
    async def finalizar_escalamiento(
        self,
        session_id: str,
        motivo: str = "Finalizado por usuario"
    ) -> Dict[str, Any]:
        """
        Finaliza un escalamiento activo y devuelve la conversaciÃ³n al agente IA
        """
        try:
            logger.info(f"=" * 80)
            logger.info(f"ðŸ”š FINALIZANDO ESCALAMIENTO")
            logger.info(f"   - Session ID: {session_id}")
            logger.info(f"   - Motivo: {motivo}")
            logger.info(f"=" * 80)
            
            # 1. Actualizar estado en MongoDB
            update_finalizar = ConversationUpdate(
                estado=ConversationStatus.activa,  # Volver a activa
                requirio_atencion_humana=True  # Mantener que requiriÃ³ atenciÃ³n
            )
            
            conversacion_actualizada = await ConversationService.update_conversation(
                session_id,
                update_finalizar
            )
            
            # 2. Agregar mensaje de sistema en MongoDB
            mensaje_finalizacion = MessageCreate(
                role=MessageRole.system,
                content=f"âœ… Escalamiento finalizado. {motivo}. La conversaciÃ³n continÃºa con el agente virtual."
            )
            await ConversationService.add_message(session_id, mensaje_finalizacion)
            
            logger.info(f"âœ… Estado actualizado en MongoDB: activa")
            
            # 3. Actualizar en MySQL (Conversacion_Sync)
            try:
                conversacion_sync = self.db.query(ConversacionSync).filter(
                    ConversacionSync.mongodb_conversation_id == session_id
                ).first()
                
                if conversacion_sync:
                    conversacion_sync.estado = EstadoConversacionEnum.activa
                    conversacion_sync.ultima_sincronizacion = datetime.utcnow()
                    self.db.commit()
                    
                    logger.info(f"âœ… Estado actualizado en MySQL: activa")
                else:
                    logger.warning(f"âš ï¸ No se encontrÃ³ ConversacionSync para {session_id}")
                    
            except Exception as e:
                logger.error(f"âŒ Error actualizando MySQL: {e}")
                self.db.rollback()
            
            logger.info(f"=" * 80)
            logger.info(f"âœ… ESCALAMIENTO FINALIZADO EXITOSAMENTE")
            logger.info(f"=" * 80)
            
            return {
                "ok": True,
                "session_id": session_id,
                "conversacion_id": str(conversacion_actualizada.id),
                "nuevo_estado": "activa",
                "mensaje": "Escalamiento finalizado. ConversaciÃ³n devuelta al agente virtual."
            }
            
        except Exception as e:
            logger.error(f"=" * 80)
            logger.error(f"âŒ ERROR FINALIZANDO ESCALAMIENTO")
            logger.error(f"   - Session ID: {session_id}")
            logger.error(f"   - Error: {str(e)}")
            logger.error(f"=" * 80)
            import traceback
            logger.error(traceback.format_exc())
            
            self.db.rollback()
            raise



    def marcar_confirmacion_pendiente(self, session_id: str):
        """Marca que una sesiÃ³n tiene confirmaciÃ³n pendiente"""
        self._confirmaciones_pendientes[session_id] = datetime.utcnow()
        logger.info(f"â³ ConfirmaciÃ³n pendiente para session: {session_id}")
    
    def tiene_confirmacion_pendiente(self, session_id: str) -> bool:
        """Verifica si hay confirmaciÃ³n pendiente (vÃ¡lida por 5 minutos)"""
        if session_id not in self._confirmaciones_pendientes:
            return False
        
        timestamp = self._confirmaciones_pendientes[session_id]
        tiempo_transcurrido = (datetime.utcnow() - timestamp).total_seconds()
        
        # Expirar despuÃ©s de 5 minutos
        if tiempo_transcurrido > 300:
            del self._confirmaciones_pendientes[session_id]
            logger.info(f"â° ConfirmaciÃ³n expirada para session: {session_id}")
            return False
        
        return True
    
    def limpiar_confirmacion_pendiente(self, session_id: str):
        """Limpia la confirmaciÃ³n pendiente"""
        if session_id in self._confirmaciones_pendientes:
            del self._confirmaciones_pendientes[session_id]
            logger.info(f"ðŸ—‘ï¸ ConfirmaciÃ³n limpiada para session: {session_id}")
    
    def obtener_mensaje_confirmacion(self, agente_nombre: str) -> str:
        """Mensaje de solicitud de confirmaciÃ³n"""
        return f"""ðŸ¤ **Â¿Deseas hablar con un agente humano?**

Te conectarÃ© con una persona real del equipo de {agente_nombre}.

âš ï¸ **Ten en cuenta:**
â€¢ Esta conversaciÃ³n serÃ¡ registrada
â€¢ Tus datos serÃ¡n almacenados de forma segura
â€¢ Un agente te atenderÃ¡ en breve

**Â¿Confirmas que deseas continuar?**

Responde:
âœ… **"SÃ­"** para conectar
âŒ **"No"** para continuar aquÃ­"""
    
    def obtener_mensaje_confirmado(self) -> str:
        """Mensaje cuando el usuario confirma"""
        return """ðŸ”” **Conectado con atenciÃ³n humana**

Un agente especializado se conectarÃ¡ contigo en breve. **Por favor espera...**

ðŸ’¡ Si deseas volver al agente virtual en cualquier momento, solo **escribe:** finalizar escalamiento o volver al bot"""
    
    def obtener_mensaje_cancelado(self) -> str:
        """Mensaje cuando el usuario cancela"""
        return """âœ… **Seguimos aquÃ­ para ayudarte**

Entendido, **continuaremos resolviendo tu problema** juntos.

Â¿En quÃ© mÃ¡s puedo asistirte? ðŸ˜Š"""

    def obtener_mensaje_escalamiento_activo(self, nombre_agente: str) -> str:
        """Mensaje cuando el escalamiento estÃ¡ activo y el agente se conecta"""
        return f"""ðŸ”” **Conectado con atenciÃ³n humana**

**{nombre_agente}** te atenderÃ¡ en breve.

ðŸ’¡ Si deseas volver al agente virtual en cualquier momento, solo **escribe:** finalizar escalamiento o volver al bot"""

    def obtener_mensaje_finalizacion_escalamiento(self) -> str:
        """Mensaje cuando se finaliza el escalamiento"""
        return """âœ… **Escalamiento finalizado**

**Has vuelto al agente virtual.** Ahora puedes continuar tu conversaciÃ³n normalmente. ðŸ˜Š

**Recuerda:** Desde ahora tus mensajes serÃ¡n procesados por la IA."""

    def obtener_modal_confirmacion(self) -> dict:
        """Estructura del modal de confirmaciÃ³n de escalamiento para el widget"""
        return {
            "type": "confirmacion_escalamiento_modal",
            "titulo": "ðŸ¤ Hablar con un agente",
            "descripcion": "Â¿Deseas conectar con un agente humano para recibir atenciÃ³n personalizada?"
        }

    async def escalar_conversacion(
        self,
        session_id: str,
        id_agente: int,
        motivo: str = "Solicitado por usuario"
    ) -> Dict[str, Any]:
        """Escala conversaciÃ³n a humano"""
        try:
            # Actualizar conversaciÃ³n a escalada
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
                content=f"ðŸ”” ConversaciÃ³n escalada a atenciÃ³n humana. Motivo: {motivo}"
            )
            await ConversationService.add_message(session_id, mensaje_escalamiento)
            
            logger.info(f"âœ… ConversaciÃ³n escalada en MongoDB: {session_id}")
            
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
                    
                    # ðŸ”¥ NUEVO: Verificar si hay funcionarios disponibles
                    if not funcionarios:
                        # âŒ NO HAY FUNCIONARIOS DISPONIBLES
                        #logger.error(f"=" * 80)
                        logger.error(f"âŒ SIN FUNCIONARIOS DISPONIBLES")
                        #logger.error(f"   - Departamento: {id_departamento}")
                        #logger.error(f"   - Agente: {agente.nombre_agente}")
                        #logger.error(f"=" * 80)
                        
                        # Agregar mensaje al usuario
                        #mensaje_sin_disponibles = MessageCreate(
                        #    role=MessageRole.system,
                        #    content=(
                        #        "âš ï¸ **No hay encargados disponibles en este momento**\n\n"
                        #        f"Actualmente no hay personal disponible en el departamento de {agente.nombre_agente}.\n\n"
                        #        "Por favor, intenta nuevamente mÃ¡s tarde o contacta con nosotros por otros medios.\n\n"
                        #        "Disculpa las molestias. ðŸ™"
                        #    )
                        #)
                        #await ConversationService.add_message(session_id, mensaje_sin_disponibles)
                        
                        # ðŸ”¥ REVERTIR ESTADO DE CONVERSACIÃ“N
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
                    
                    # âœ… SÃ HAY FUNCIONARIOS DISPONIBLES
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
                    
                    logger.info(f"âœ… ConversaciÃ³n asignada a: {nombre_completo}")
                    
                    mensaje_asignacion = MessageCreate(
                        role=MessageRole.system,
                        content=f"ðŸ“Œ ConversaciÃ³n asignada a {nombre_completo}"
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
                logger.error(f"âŒ Error en asignaciÃ³n de funcionario: {e}")

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
                logger.error(f"âŒ Error en ConversacionSync MySQL: {e}")
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
                "mensaje": "ConversaciÃ³n escalada correctamente." if funcionario_asignado else "ConversaciÃ³n escalada sin asignaciÃ³n."
            }
            
        except Exception as e:
            logger.error(f"âŒ Error escalando conversaciÃ³n: {e}")
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
        """Crea notificaciÃ³n para el funcionario asignado"""
        try:
            nombre_funcionario = f"{funcionario.persona.nombre} {funcionario.persona.apellido}"
    
            notificacion = NotificacionUsuario(
                id_usuario=funcionario.id_usuario,
                id_agente=id_agente,
                tipo=TipoNotificacionEnum.urgente,
                titulo=f'Nueva conversaciÃ³n asignada - {agente_nombre}',
                mensaje=f'Se te ha asignado una conversaciÃ³n del agente {agente_nombre}. Motivo: {motivo}',
                icono='arrow-up-circle',
                url_accion=f'/conversaciones-escaladas/{session_id}',
                datos_adicionales=f'{{"session_id": "{session_id}", "id_agente": {id_agente}, "motivo": "{motivo}"}}',
                leida=False,
                fecha_creacion=datetime.utcnow()
            )
            
            self.db.add(notificacion)
            self.db.commit()
            
            logger.info(f"âœ… NotificaciÃ³n creada para {nombre_funcionario}")
            return 1
            
        except Exception as e:
            logger.error(f"âŒ Error creando notificaciÃ³n: {e}")
            self.db.rollback()
            return 0

    async def _obtener_o_crear_visitante(self, session_id: str) -> VisitanteAnonimo:
        """Obtiene o crea un visitante anÃ³nimo"""
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
                
                logger.info(f"âœ… Nuevo visitante creado: {visitante.id_visitante}")
            else:
                visitante.ultima_visita = datetime.utcnow()
                self.db.commit()
                
            return visitante
            
        except Exception as e:
            logger.error(f"âŒ Error obteniendo/creando visitante: {e}")
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
                        content=f"ConversaciÃ³n finalizada por inactividad ({timeout_minutos} minutos)"
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
                    logger.error(f"âŒ Error finalizando conversaciÃ³n: {e}")
            
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
            logger.error(f"âŒ Error finalizando conversaciones inactivas: {e}")
            self.db.rollback()
            raise
    

    def _obtener_usuarios_departamento(self, id_departamento: int) -> List[Usuario]:
        """
        Obtiene UN funcionario DISPONIBLE del departamento
        
        ðŸ”¥ NUEVO COMPORTAMIENTO:
        - Solo funcionarios con disponible=True
        - Del mismo departamento del agente
        - Con rol activo de nivel 3 (funcionario)
        - Estado activo
        
        Returns:
            List[Usuario]: Lista con 1 funcionario disponible, o lista vacÃ­a si no hay
        """
        try:
            logger.info(f"ðŸ” Buscando funcionarios DISPONIBLES en departamento {id_departamento}")
            
            # ðŸ”¥ QUERY CON FILTRO DE DISPONIBILIDAD
            funcionarios_disponibles = self.db.query(Usuario).join(
                Persona, Usuario.id_persona == Persona.id_persona
            ).join(
                UsuarioRol, Usuario.id_usuario == UsuarioRol.id_usuario
            ).join(
                Rol, UsuarioRol.id_rol == Rol.id_rol
            ).filter(
                # ðŸ”¥ FILTROS CRÃTICOS
                Persona.id_departamento == id_departamento,  # Mismo departamento
                Usuario.disponible == True,                  # âœ… DISPONIBLE
                Usuario.estado == 'activo',                  # Usuario activo
                Persona.estado == 'activo',                  # Persona activa
                UsuarioRol.activo == True,                   # Rol asignado activo
                Rol.activo == True,                          # Rol existe y activo
                Rol.nivel_jerarquia == 3                     # Solo funcionarios
            ).distinct().all()
            
            # ðŸ”¥ LOGS DETALLADOS
            logger.info(f"=" * 80)
            logger.info(f"ðŸ“Š RESULTADO BÃšSQUEDA DE FUNCIONARIOS")
            logger.info(f"   - Departamento: {id_departamento}")
            logger.info(f"   - Funcionarios disponibles encontrados: {len(funcionarios_disponibles)}")
            
            if funcionarios_disponibles:
                for i, func in enumerate(funcionarios_disponibles, 1):
                    logger.info(f"   [{i}] {func.username} (ID: {func.id_usuario}) - {func.persona.nombre} {func.persona.apellido}")
            else:
                logger.warning(f"   âš ï¸ NO HAY FUNCIONARIOS DISPONIBLES")
            
            logger.info(f"=" * 80)
            
            # ðŸ”¥ RETORNAR VACÃO SI NO HAY DISPONIBLES
            if not funcionarios_disponibles:
                logger.warning(f"âŒ No hay funcionarios DISPONIBLES en departamento {id_departamento}")
                return []
            
            # ðŸ”¥ SELECCIONAR ALEATORIAMENTE ENTRE LOS DISPONIBLES
            funcionario_seleccionado = random.choice(funcionarios_disponibles)
            
            logger.info(f"=" * 80)
            logger.info(f"âœ… FUNCIONARIO SELECCIONADO")
            logger.info(f"   - Username: {funcionario_seleccionado.username}")
            logger.info(f"   - ID: {funcionario_seleccionado.id_usuario}")
            logger.info(f"   - Nombre: {funcionario_seleccionado.persona.nombre} {funcionario_seleccionado.persona.apellido}")
            logger.info(f"   - Departamento: {funcionario_seleccionado.persona.id_departamento}")
            logger.info(f"   - Disponible: {funcionario_seleccionado.disponible}")
            logger.info(f"=" * 80)
            
            return [funcionario_seleccionado]
            
        except Exception as e:
            logger.error(f"=" * 80)
            logger.error(f"âŒ ERROR OBTENIENDO FUNCIONARIO")
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
            
            logger.info(f"ðŸ’¬ Respuesta humana: {nombre_usuario} â†’ {session_id}")
            
            return {
                "success": True,
                "session_id": session_id,
                "mensaje_agregado": True,
                "total_mensajes": conversation.metadata.total_mensajes
            }
            
        except Exception as e:
            logger.error(f"âŒ Error agregando respuesta humana: {e}")
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
            
            logger.info(f"ðŸ“‹ Conversaciones escaladas: {len(conversaciones)}")
            
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
            logger.error(f"âŒ Error obteniendo conversaciones escaladas: {e}")
            return []
        
    # services/escalamiento_service.py
    class EscalamientoService:
        # ... cÃ³digo existente ...
        
        # ðŸ”¥ NUEVO: Keywords para finalizar escalamiento
        KEYWORDS_FINALIZAR_ESCALAMIENTO = [
            'finalizar escalamiento',
            'terminar escalamiento',
            'cancelar escalamiento',
            'volver al bot',
            'volver a la ia',
            'volver al agente virtual',
            'ya no necesito humano',
            'cancelar derivaciÃ³n',
            'cerrar escalamiento',
            'regresar al bot'
        ]
        
        def detectar_finalizacion_escalamiento(self, mensaje: str) -> bool:
            """
            Detecta si el usuario quiere finalizar el escalamiento
            y volver al agente IA
            """
            mensaje_lower = mensaje.lower().strip()
            
            logger.info(f"ðŸ” Verificando finalizaciÃ³n de escalamiento: '{mensaje}'")
            
            for keyword in self.KEYWORDS_FINALIZAR_ESCALAMIENTO:
                if keyword in mensaje_lower:
                    logger.info(f"ðŸ”” Keyword de finalizaciÃ³n detectado: '{keyword}'")
                    return True
            
            return False
        
        async def finalizar_escalamiento(
            self,
            session_id: str,
            motivo: str = "Finalizado por usuario"
        ) -> Dict[str, Any]:
            """
            Finaliza un escalamiento activo y devuelve la conversaciÃ³n al agente IA
            """
            try:
                logger.info(f"=" * 80)
                logger.info(f"ðŸ”š FINALIZANDO ESCALAMIENTO")
                logger.info(f"   - Session ID: {session_id}")
                logger.info(f"   - Motivo: {motivo}")
                logger.info(f"=" * 80)
                
                # 1. Actualizar estado en MongoDB
                update_finalizar = ConversationUpdate(
                    estado=ConversationStatus.activa,  # Volver a activa
                    requirio_atencion_humana=True  # Mantener que requiriÃ³ atenciÃ³n
                )
                
                conversacion_actualizada = await ConversationService.update_conversation(
                    session_id,
                    update_finalizar
                )
                
                # 2. Agregar mensaje de sistema en MongoDB
                mensaje_finalizacion = MessageCreate(
                    role=MessageRole.system,
                    content=f"âœ… Escalamiento finalizado. {motivo}. La conversaciÃ³n continÃºa con el agente virtual."
                )
                await ConversationService.add_message(session_id, mensaje_finalizacion)
                
                logger.info(f"âœ… Estado actualizado en MongoDB: activa")
                
                # 3. Actualizar en MySQL (Conversacion_Sync)
                try:
                    conversacion_sync = self.db.query(ConversacionSync).filter(
                        ConversacionSync.mongodb_conversation_id == session_id
                    ).first()
                    
                    if conversacion_sync:
                        conversacion_sync.estado = EstadoConversacionEnum.activa
                        conversacion_sync.ultima_sincronizacion = datetime.utcnow()
                        self.db.commit()
                        
                        logger.info(f"âœ… Estado actualizado en MySQL: activa")
                    else:
                        logger.warning(f"âš ï¸ No se encontrÃ³ ConversacionSync para {session_id}")
                        
                except Exception as e:
                    logger.error(f"âŒ Error actualizando MySQL: {e}")
                    self.db.rollback()
                
                logger.info(f"=" * 80)
                logger.info(f"âœ… ESCALAMIENTO FINALIZADO EXITOSAMENTE")
                logger.info(f"=" * 80)
                
                return {
                    "ok": True,
                    "session_id": session_id,
                    "conversacion_id": str(conversacion_actualizada.id),
                    "nuevo_estado": "activa",
                    "mensaje": "Escalamiento finalizado. ConversaciÃ³n devuelta al agente virtual."
                }
                
            except Exception as e:
                logger.error(f"=" * 80)
                logger.error(f"âŒ ERROR FINALIZANDO ESCALAMIENTO")
                logger.error(f"   - Session ID: {session_id}")
                logger.error(f"   - Error: {str(e)}")
                logger.error(f"=" * 80)
                import traceback
                logger.error(traceback.format_exc())
                
                self.db.rollback()
                raise