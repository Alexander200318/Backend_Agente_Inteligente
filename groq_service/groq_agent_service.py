"""Servicio de Groq para chat con agentes virtuales"""

from groq_service.groq_client import GroqClient
from rag.rag_service import RAGService
from sqlalchemy.orm import Session
from models.agente_virtual import AgenteVirtual
from typing import Dict, Any, List, Optional
from utils.session_manager import SessionManager
from services.escalamiento_service import EscalamientoService
from services.conversation_service import ConversationService
from models.conversation_mongo import (
    ConversationCreate, 
    MessageCreate, 
    MessageRole,
    ConversationUpdate,
    ConversationStatus
)
from services.visitante_anonimo_service import VisitanteAnonimoService
import uuid
import logging

logger = logging.getLogger(__name__)


class GroqAgentService:
    """Servicio para chatear con agentes virtuales usando Groq API"""
    
    _session_manager = SessionManager(ttl_minutes=30)

    def __init__(self, db: Session):
        """
        Inicializa el servicio de Groq
        
        Args:
            db: Sesión de base de datos
        """
        self.db = db
        self.client = GroqClient()
        self.rag = RAGService(db, use_cache=True)
        self.visitante_service = VisitanteAnonimoService(db)

    async def chat_with_agent(
        self, 
        id_agente: int, 
        pregunta: str,
        session_id: str, 
        origin: str = "web",
        ip_origen: Optional[str] = None,
        user_agent: Optional[str] = None,
        dispositivo: Optional[str] = None,
        navegador: Optional[str] = None,
        sistema_operativo: Optional[str] = None,
        guardar_en_bd: bool = True,
        k: Optional[int] = None,
        use_reranking: Optional[bool] = None,
        temperatura: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Chatea con agente usando Groq (sin streaming)
        
        Args:
            id_agente: ID del agente virtual
            pregunta: Pregunta del usuario
            session_id: ID de sesión del usuario
            origin: Origen de la solicitud (web, widget, api, etc)
            ip_origen: IP del cliente
            user_agent: User agent del navegador
            dispositivo: Tipo de dispositivo
            navegador: Nombre del navegador
            sistema_operativo: Sistema operativo del cliente
            guardar_en_bd: Si guardar la conversación en BD
            k: Número de documentos RAG a recuperar
            use_reranking: Si usar reranking en RAG
            temperatura: Temperatura para generación
            max_tokens: Máximo de tokens en respuesta
        
        Returns:
            Dict con la respuesta
        """
        
        # Obtener agente
        agente = self.db.query(AgenteVirtual).filter(
            AgenteVirtual.id_agente == id_agente
        ).first()
        
        if not agente:
            raise Exception(f"Agente {id_agente} no encontrado")
        
        # Obtener o crear visitante
        visitante = None
        if guardar_en_bd:
            try:
                visitante = self.visitante_service.obtener_por_sesion(session_id)
                logger.info(f"✅ Visitante registrado: {visitante.id_visitante}")
            except:
                logger.info("⚠️ No hay visitante registrado")
        
        k_final = k if k is not None else 2
        use_reranking_final = use_reranking if use_reranking is not None else False
        
        # Recuperar documentos RAG
        logger.info(f"🔍 Buscando documentos RAG (k={k_final}, reranking={use_reranking_final})")
        documentos = self.rag.search(
            id_agente=id_agente,
            query=pregunta,
            session_id=session_id,
            n_results=k_final,
            use_reranking=use_reranking_final,
            incluir_inactivos=False
        )
        
        contexto_rag = "\n".join([
            f"- {doc['document']} (Relevancia: {doc.get('score', 0):.2f})"
            for doc in documentos[:k_final]
        ]) if documentos else "No hay documentos relevantes"
        
        logger.info(f"📚 {len(documentos)} documentos recuperados")
        
        # 🔥 IMPORTANTE: Si no hay contexto, rechazar respuesta SIN llamar a Groq
        if contexto_rag == "No hay documentos relevantes":
            logger.warning(f"⛔ No hay contexto para la pregunta: '{pregunta}'")
            respuesta = "Lo siento, no tengo información disponible sobre eso en mi base de datos. Te recomiendo contactar con un agente humano."
            
            # Aún así guardar en BD si es necesario
            if guardar_en_bd and visitante:
                try:
                    conv_service = ConversationService(self.db)
                    conversacion = conv_service.obtener_por_sesion(session_id)
                    
                    if not conversacion:
                        conv_create = ConversationCreate(
                            id_visitante=visitante.id_visitante,
                            id_agente=id_agente,
                            session_id=session_id,
                            origin=origin
                        )
                        conversacion = conv_service.crear(conv_create)
                    
                    # Guardar mensaje del usuario
                    msg_user = MessageCreate(
                        id_conversacion=conversacion.id_conversacion,
                        role="user",
                        content=pregunta
                    )
                    conv_service.crear_mensaje(msg_user)
                    
                    # Guardar respuesta del sistema
                    msg_bot = MessageCreate(
                        id_conversacion=conversacion.id_conversacion,
                        role="assistant",
                        content=respuesta
                    )
                    conv_service.crear_mensaje(msg_bot)
                    
                    logger.info(f"✅ Conversación guardada sin contexto")
                except Exception as e:
                    logger.error(f"❌ Error guardando conversación sin contexto: {e}")
            
            return {"respuesta": respuesta, "documentos_usados": 0, "tuvo_contexto": False}
        
        # Construir prompt
        system_prompt = self._build_system_prompt(agente, contexto_rag)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": pregunta}
        ]
        
        # Llamar a Groq
        logger.info("📤 Enviando solicitud a Groq...")
        # 🔥 Usar temperatura y tokens del agente si no se pasan parámetros
        temp = temperatura if temperatura is not None else (float(agente.temperatura) if agente.temperatura else 0.7)
        tokens = max_tokens if max_tokens is not None else (agente.max_tokens if agente.max_tokens else 2000)
        
        logger.info(f"⚙️ Configuración: temperatura={temp}, max_tokens={tokens}")
        
        response_data = self.client.chat_completion(
            messages=messages,
            temperature=temp,
            max_tokens=tokens
        )
        
        respuesta = response_data["content"]
        logger.info(f"✅ Respuesta recibida: {len(respuesta)} caracteres")
        
        # Crear/actualizar conversación si es necesario
        conversation_id = None
        if guardar_en_bd and visitante:
            try:
                # Buscar conversación existente
                conv_service = ConversationService(self.db)
                conversacion = conv_service.obtener_por_sesion(session_id)
                
                if not conversacion:
                    # Crear nueva conversación
                    conv_create = ConversationCreate(
                        id_visitante=visitante.id_visitante,
                        id_agente=id_agente,
                        session_id=session_id,
                        origin=origin
                    )
                    conversacion = conv_service.crear(conv_create)
                
                conversation_id = conversacion.id_conversacion
                
                # Agregar mensajes
                user_msg = MessageCreate(
                    id_conversacion=conversation_id,
                    role=MessageRole.USER,
                    content=pregunta,
                    origen=origin
                )
                conv_service.agregar_mensaje(user_msg)
                
                assistant_msg = MessageCreate(
                    id_conversacion=conversation_id,
                    role=MessageRole.ASSISTANT,
                    content=respuesta,
                    origen="groq"
                )
                conv_service.agregar_mensaje(assistant_msg)
                
                logger.info(f"✅ Conversación guardada: {conversation_id}")
            
            except Exception as e:
                logger.error(f"⚠️ Error al guardar conversación: {str(e)}")
        
        return {
            "id_conversacion": conversation_id,
            "respuesta": respuesta,
            "modelo_usado": response_data["model"],
            "tokens_usados": response_data["usage"]["total_tokens"],
            "documentos_recuperados": len(documentos),
            "fuente": "groq"
        }

    async def chat_with_agent_streaming(
        self,
        id_agente: int,
        pregunta: str,
        session_id: str,
        origin: str = "web",
        ip_origen: Optional[str] = None,
        user_agent: Optional[str] = None,
        dispositivo: Optional[str] = None,
        navegador: Optional[str] = None,
        sistema_operativo: Optional[str] = None,
        guardar_en_bd: bool = True,
        k: Optional[int] = None,
        use_reranking: Optional[bool] = None,
        temperatura: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        """
        Chatea con agente usando Groq CON streaming
        
        Yields:
            Fragmentos de la respuesta
        """
        
        agente = self.db.query(AgenteVirtual).filter(
            AgenteVirtual.id_agente == id_agente
        ).first()
        
        if not agente:
            raise Exception(f"Agente {id_agente} no encontrado")
        
        # Obtener visitante
        visitante = None
        if guardar_en_bd:
            try:
                visitante = self.visitante_service.obtener_por_sesion(session_id)
            except:
                pass
        
        k_final = k if k is not None else 2
        use_reranking_final = use_reranking if use_reranking is not None else False
        
        # Recuperar documentos RAG
        documentos = self.rag.search(
            id_agente=id_agente,
            query=pregunta,
            session_id=session_id,
            n_results=k_final,
            use_reranking=use_reranking_final,
            incluir_inactivos=False
        )
        
        contexto_rag = "\n".join([
            f"- {doc['document']} (Relevancia: {doc.get('score', 0):.2f})"
            for doc in documentos[:k_final]
        ]) if documentos else "No hay documentos relevantes"
        
        # 🔥 IMPORTANTE: Si no hay contexto, rechazar respuesta SIN llamar a Groq
        if contexto_rag == "No hay documentos relevantes":
            logger.warning(f"⛔ No hay contexto para streaming: '{pregunta}'")
            respuesta_completa = "Lo siento, no tengo información disponible sobre eso en mi base de datos. Te recomiendo contactar con un agente humano."
            
            # Devolver respuesta en chunks
            yield respuesta_completa
            
            # Guardar en BD si es necesario
            if guardar_en_bd and visitante:
                try:
                    conv_service = ConversationService(self.db)
                    conversacion = conv_service.obtener_por_sesion(session_id)
                    
                    if not conversacion:
                        conv_create = ConversationCreate(
                            id_visitante=visitante.id_visitante,
                            id_agente=id_agente,
                            session_id=session_id,
                            origin=origin
                        )
                        conversacion = conv_service.crear(conv_create)
                    
                    msg_user = MessageCreate(id_conversacion=conversacion.id_conversacion, role="user", content=pregunta)
                    conv_service.crear_mensaje(msg_user)
                    
                    msg_bot = MessageCreate(id_conversacion=conversacion.id_conversacion, role="assistant", content=respuesta_completa)
                    conv_service.crear_mensaje(msg_bot)
                except Exception as e:
                    logger.error(f"❌ Error guardando conversación sin contexto: {e}")
            
            return
        
        # Construir prompt
        system_prompt = self._build_system_prompt(agente, contexto_rag)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": pregunta}
        ]
        
        # Streaming
        logger.info("📤 Iniciando streaming con Groq...")
        respuesta_completa = ""
        
        # 🔥 Usar configuración del agente si no se pasan parámetros
        temp = temperatura if temperatura is not None else (float(agente.temperatura) if agente.temperatura else 0.7)
        tokens = max_tokens if max_tokens is not None else (agente.max_tokens if agente.max_tokens else 2000)
        logger.info(f"⚙️ Configuración streaming: temperatura={temp}, max_tokens={tokens}")
        
        try:
            for chunk in self.client.streaming_chat(
                messages=messages,
                temperature=temp,
                max_tokens=tokens
            ):
                respuesta_completa += chunk
                yield chunk
        
        except Exception as e:
            logger.error(f"❌ Error en streaming: {str(e)}")
            raise
        
        # Guardar conversación completa si es necesario
        if guardar_en_bd and visitante:
            try:
                conv_service = ConversationService(self.db)
                conversacion = conv_service.obtener_por_sesion(session_id)
                
                if not conversacion:
                    conv_create = ConversationCreate(
                        id_visitante=visitante.id_visitante,
                        id_agente=id_agente,
                        session_id=session_id,
                        origin=origin
                    )
                    conversacion = conv_service.crear(conv_create)
                
                # Guardar mensajes
                user_msg = MessageCreate(
                    id_conversacion=conversacion.id_conversacion,
                    role=MessageRole.USER,
                    content=pregunta,
                    origen=origin
                )
                conv_service.agregar_mensaje(user_msg)
                
                assistant_msg = MessageCreate(
                    id_conversacion=conversacion.id_conversacion,
                    role=MessageRole.ASSISTANT,
                    content=respuesta_completa,
                    origen="groq"
                )
                conv_service.agregar_mensaje(assistant_msg)
                
                logger.info(f"✅ Conversación streaming guardada")
            
            except Exception as e:
                logger.error(f"⚠️ Error al guardar conversación streaming: {str(e)}")

    def _build_system_prompt(self, agente: AgenteVirtual, contexto_rag: str) -> str:
        """
        Construye el prompt del sistema para el agente
        
        Args:
            agente: Objeto del agente virtual
            contexto_rag: Contexto de documentos recuperados
        
        Returns:
            String con el prompt del sistema
        """
        # Detectar si hay contexto relevante
        tiene_contexto = contexto_rag and contexto_rag != "No hay documentos relevantes"
        
        # 🔥 Usar configuración del agente virtual
        nombre_agente = agente.nombre_agente if agente.nombre_agente else "CallCenter AI"
        prompt_especializado = agente.prompt_especializado if agente.prompt_especializado else ""
        prompt_sistema = agente.prompt_sistema if agente.prompt_sistema else ""
        mensaje_bienvenida = agente.mensaje_bienvenida if agente.mensaje_bienvenida else ""
        
        if not tiene_contexto:
            # Si no hay contexto, ser muy estricto
            base_prompt = f"""Eres un asistente virtual para {nombre_agente}.

⛔ INSTRUCCIÓN CRÍTICA - LEE ESTO PRIMERO:
- NO tienes información disponible sobre esta pregunta
- NO debes inventar o sugerir respuestas
- DEBES responder que no tienes esa información en tu base de datos
- Sé honesto y directo

Responde EXACTAMENTE así cuando no tengas contexto:
"Lo siento, no tengo información disponible sobre eso en mi base de datos. Te recomiendo contactar con un agente humano."

{f'TONO Y PERSONALIDAD: {mensaje_bienvenida}' if mensaje_bienvenida else ''}
{f'INSTRUCCIONES DEL SISTEMA: {prompt_sistema}' if prompt_sistema else ''}

INFORMACIÓN DE CONTEXTO:
{contexto_rag}
"""
        else:
            # Si hay contexto, responder normalmente
            base_prompt = f"""Eres un asistente virtual para {nombre_agente}.

⚠️ INSTRUCCIÓN IMPORTANTE:
- SOLO responde basándote en la información del contexto proporcionado
- Si el contexto no contiene información relevante para la pregunta, DEBES rechazar
- NO inventes, NO sugieras, NO alucinates información
- Si la pregunta no está cubierta por el contexto, responde: "Lo siento, no tengo información disponible sobre eso en mi base de datos. Te recomiendo contactar con un agente humano."

Tu responsabilidad es:
1. Usar SIEMPRE y SOLO la información del contexto proporcionado
2. Responder de forma clara y profesional
3. Si no está en el contexto, rechazar la pregunta
4. Mantener un tono amable y profesional

{f'PERSONALIDAD Y BIENVENIDA: {mensaje_bienvenida}' if mensaje_bienvenida else ''}
{f'INSTRUCCIONES DEL SISTEMA: {prompt_sistema}' if prompt_sistema else ''}
{f'ESPECIALIZACIÓN: {prompt_especializado}' if prompt_especializado else ''}

INFORMACIÓN DE CONTEXTO:
{contexto_rag}

Importante: Responde BASÁNDOTE ÚNICAMENTE en el contexto anterior. Si la pregunta no está cubierta, rechaza."""
        
        return base_prompt

    def test_connection(self) -> Dict[str, Any]:
        """
        Prueba la conexión con Groq
        
        Returns:
            Dict con el resultado de la prueba
        """
        try:
            logger.info("🧪 Probando conexión con Groq...")
            
            response = self.client.chat_completion(
                messages=[
                    {"role": "user", "content": "Di 'Conexión exitosa' si me escuchas"}
                ],
                max_tokens=100
            )
            
            logger.info("✅ Prueba de conexión exitosa")
            return {
                "estado": "conexión exitosa",
                "modelo": response["model"],
                "respuesta": response["content"]
            }
        
        except Exception as e:
            logger.error(f"❌ Error en prueba de conexión: {str(e)}")
            return {
                "estado": "error",
                "error": str(e)
            }

    async def chat_with_agent_stream(
        self,
        id_agente: int,
        pregunta: str,
        session_id: str,
        origin: str = "web",
        ip_origen: Optional[str] = None,
        user_agent: Optional[str] = None,
        dispositivo: Optional[str] = None,
        navegador: Optional[str] = None,
        sistema_operativo: Optional[str] = None,
        guardar_en_bd: bool = True,
        k: Optional[int] = None,
        use_reranking: Optional[bool] = None,
        temperatura: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        """
        Método compatible con SSE (Server-Sent Events) que retorna eventos estructurados
        
        Yields:
            Diccionarios con estructura de eventos para streaming
        """
        
        agente = self.db.query(AgenteVirtual).filter(
            AgenteVirtual.id_agente == id_agente
        ).first()
        
        if not agente:
            raise Exception(f"Agente {id_agente} no encontrado")
        
        # Obtener visitante
        visitante = None
        if guardar_en_bd:
            try:
                visitante = self.visitante_service.obtener_por_sesion(session_id)
            except:
                pass
        
        k_final = k if k is not None else 2
        use_reranking_final = use_reranking if use_reranking is not None else False
        
        # Recuperar documentos RAG
        documentos = self.rag.search(
            id_agente=id_agente,
            query=pregunta,
            session_id=session_id,
            n_results=k_final,
            use_reranking=use_reranking_final,
            incluir_inactivos=False
        )
        
        contexto_rag = "\n".join([
            f"- {doc['document']} (Relevancia: {doc.get('score', 0):.2f})"
            for doc in documentos[:k_final]
        ]) if documentos else "No hay documentos relevantes"
        
        # 🔥 IMPORTANTE: Si no hay contexto, rechazar respuesta SIN llamar a Groq
        if contexto_rag == "No hay documentos relevantes":
            logger.warning(f"⛔ No hay contexto para SSE: '{pregunta}'")
            respuesta_completa = "Lo siento, no tengo información disponible sobre eso en mi base de datos. Te recomiendo contactar con un agente humano."
            
            # Enviar evento de inicio
            yield {
                "type": "start",
                "agent_id": id_agente,
                "timestamp": str(__import__('datetime').datetime.now().isoformat())
            }
            
            # Enviar respuesta completa
            yield {
                "type": "chunk",
                "content": respuesta_completa
            }
            
            # Enviar evento de finalización
            yield {
                "type": "done",
                "content": respuesta_completa,
                "documents_used": 0,
                "timestamp": str(__import__('datetime').datetime.now().isoformat())
            }
            
            # Guardar en BD si es necesario
            if guardar_en_bd and visitante:
                try:
                    conv_service = ConversationService(self.db)
                    conversacion = conv_service.obtener_por_sesion(session_id)
                    
                    if not conversacion:
                        conv_create = ConversationCreate(
                            id_visitante=visitante.id_visitante,
                            id_agente=id_agente,
                            session_id=session_id,
                            origin=origin
                        )
                        conversacion = conv_service.crear(conv_create)
                    
                    msg_user = MessageCreate(id_conversacion=conversacion.id_conversacion, role="user", content=pregunta)
                    conv_service.crear_mensaje(msg_user)
                    
                    msg_bot = MessageCreate(id_conversacion=conversacion.id_conversacion, role="assistant", content=respuesta_completa)
                    conv_service.crear_mensaje(msg_bot)
                except Exception as e:
                    logger.error(f"❌ Error guardando conversación sin contexto: {e}")
            
            return
        
        # Construir prompt
        system_prompt = self._build_system_prompt(agente, contexto_rag)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": pregunta}
        ]
        
        logger.info("📤 Iniciando streaming con Groq...")
        respuesta_completa = ""
        
        try:
            # Enviar evento de inicio
            yield {
                "type": "start",
                "agent_id": id_agente,
                "timestamp": str(__import__('datetime').datetime.now().isoformat())
            }
            
            # 🔥 NUEVO: Enviar contenidos consultados ANTES de empezar el stream
            if documentos:
                contenidos_para_enviar = []
                for doc in documentos:
                    meta = doc.get('metadata', {})
                    contenidos_para_enviar.append({
                        'id': meta.get('id'),
                        'titulo': meta.get('titulo', doc.get('document', '')[:100]),
                        'tipo': meta.get('tipo', 'documento'),
                        'categoria': meta.get('categoria'),
                        'contenido': doc.get('document', ''),
                        'score': doc.get('score', 0.0)
                    })
                
                yield {
                    "type": "sources",
                    "sources": contenidos_para_enviar,
                    "total_sources": len(contenidos_para_enviar)
                }
                logger.info(f"📚 Enviando {len(contenidos_para_enviar)} fuentes consultadas")
            
            # Streaming de respuesta
            for chunk in self.client.streaming_chat(
                messages=messages,
                temperature=temperatura or 0.7,
                max_tokens=max_tokens or 2000
            ):
                respuesta_completa += chunk
                
                # Enviar cada fragmento como evento
                yield {
                    "type": "chunk",
                    "content": chunk
                }
            
            # Enviar evento de finalización
            yield {
                "type": "done",
                "content": respuesta_completa,
                "tokens": len(respuesta_completa.split()),
                "documents_used": len(documentos),
                "timestamp": str(__import__('datetime').datetime.now().isoformat())
            }
        
        except Exception as e:
            logger.error(f"❌ Error en streaming: {str(e)}")
            yield {
                "type": "error",
                "content": str(e),
                "timestamp": str(__import__('datetime').datetime.now().isoformat())
            }
