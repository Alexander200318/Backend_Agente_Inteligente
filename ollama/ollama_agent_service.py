# app/ollama/ollama_agent_service.py
from ollama.ollama_client import OllamaClient
from ollama.prompt_builder import build_system_prompt, build_chat_prompt
from rag.rag_service import RAGService
from sqlalchemy.orm import Session
from models.agente_virtual import AgenteVirtual
from typing import Dict, Any, List, Optional, Generator, AsyncGenerator
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
import uuid
import logging

logger = logging.getLogger(__name__)


class OllamaAgentService:
    _session_manager = SessionManager(ttl_minutes=30) 

    def __init__(self, db: Session):
        self.db = db
        self.client = OllamaClient()
        self.rag = RAGService(db, use_cache=True)

    def chat_with_agent(
        self, 
        id_agente: int, 
        pregunta: str,
        session_id: str, 
        origin: str = "web",
        k: Optional[int] = None,
        use_reranking: Optional[bool] = None,
        temperatura: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Chatea con agente SIN streaming"""
        
        agente = self.db.query(AgenteVirtual).filter(
            AgenteVirtual.id_agente == id_agente
        ).first()
        
        if not agente:
            raise Exception(f"Agente {id_agente} no encontrado")

        k_final = k if k is not None else 2
        use_reranking_final = use_reranking if use_reranking is not None else False
        
        temperatura_final = temperatura if temperatura is not None else \
                           (float(agente.temperatura) if agente.temperatura else 0.7)
        
        max_tokens_final = max_tokens if max_tokens is not None else \
                          (int(agente.max_tokens) if agente.max_tokens else 1000)

        system_prompt = build_system_prompt(agente)

        print(f"🔗 Session: {session_id} | Origin: {origin}")
        self._session_manager.touch(session_id)

        try:
            results = self.rag.search(
                id_agente=id_agente, 
                query=pregunta, 
                session_id=session_id, 
                n_results=k_final,
                use_reranking=use_reranking_final,
                use_priority_boost=True,
                priority_boost_factor=0.4
            )
            
            if results:
                contexto_parts = []
                for i, r in enumerate(results, 1):
                    metadata = r.get('metadata', {})
                    titulo = metadata.get('titulo', 'Sin título')
                    doc = r.get('document', '')
                    contexto_parts.append(f"[Fuente {i}: {titulo}]\n{doc}")
                
                contexto = "\n\n".join(contexto_parts)
                sources_count = len(results)
            else:
                contexto = "No se encontró información relevante en la base de conocimientos."
                sources_count = 0
                
        except Exception as e:
            print(f"Error en RAG: {e}")
            contexto = "Error al buscar información."
            sources_count = 0

        prompt = build_chat_prompt(system_prompt, contexto, pregunta)
        model_name = agente.modelo_ia or "llama3"
        
        try:
            print(f"🤖 Modelo: {model_name}")
            print(f"🌡️  Temperatura: {temperatura_final}")
            print(f"📊 Max tokens: {max_tokens_final}")
            print(f"🔍 RAG: k={k_final}, reranking={use_reranking_final}")
            
            res = self.client.generate(
                model_name=model_name,
                prompt=prompt,
                stream=False,
                temperature=temperatura_final,
                max_tokens=max_tokens_final,
                options={"keep_alive": "15m"}
            )
            
            return {
                "ok": True,
                "response": res.get("response", ""),
                "agent_id": id_agente,
                "agent_name": agente.nombre_agente,
                "session_id": session_id,
                "origin": origin,
                "sources_used": sources_count,
                "model_used": model_name,
                "context_size": len(contexto),
                "tokens_generated": max_tokens_final,
                "params_used": {
                    "temperatura": temperatura_final,
                    "max_tokens": max_tokens_final,
                    "k": k_final,
                    "use_reranking": use_reranking_final
                }
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error con Ollama: {error_msg}")
            
            if "not found" in error_msg.lower():
                print(f"⚠️ Modelo {model_name} no encontrado, usando llama3")
                try:
                    res = self.client.generate(
                        model_name="llama3",
                        prompt=prompt,
                        stream=False,
                        temperature=temperatura_final,
                        max_tokens=max_tokens_final,
                        options={"keep_alive": "15m"}
                    )
                    return {
                        "ok": True,
                        "response": res.get("response", ""),
                        "agent_id": id_agente,
                        "agent_name": agente.nombre_agente,
                        "sources_used": sources_count,
                        "model_used": "llama3 (fallback)",
                        "warning": f"Modelo {model_name} no disponible"
                    }
                except Exception as e2:
                    raise Exception(f"Error en fallback: {str(e2)}")
            
            raise Exception(f"Error en Ollama: {error_msg}")

    # 🔥 MÉTODO CON STREAMING, ESCALAMIENTO Y SAVE_TO_MONGO


    async def chat_with_agent_stream(
        self, 
        id_agente: int, 
        pregunta: str, 
        session_id: str, 
        origin: str = "web",
        k: Optional[int] = None,
        use_reranking: Optional[bool] = None,
        temperatura: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Chatea con agente CON streaming
        
        🔥 NUEVO COMPORTAMIENTO:
        - Por defecto NO guarda en MongoDB
        - Solo guarda cuando detecta intención de escalamiento
        - Crea conversación al momento de escalar
        """
        
        try:
            # ============================================
            # PASO 0: INICIALIZAR SERVICIOS
            # ============================================
            escalamiento_service = EscalamientoService(self.db)
            
            # ============================================
            # PASO 1: OBTENER AGENTE
            # ============================================
            agente = self.db.query(AgenteVirtual).filter(
                AgenteVirtual.id_agente == id_agente
            ).first()
            
            if not agente:
                yield {
                    "type": "error",
                    "content": f"Agente {id_agente} no encontrado"
                }
                return
            
            # ============================================
            # PASO 2: 🔥 DETECTAR ESCALAMIENTO PRIMERO
            # ============================================
            necesita_escalamiento = escalamiento_service.detectar_intencion_escalamiento(pregunta)
            
            if necesita_escalamiento:
                logger.info(f"🔔 Escalamiento detectado en session {session_id}")
                
                # ============================================
                # PASO 3: 🔥 CREAR CONVERSACIÓN EN MONGODB (solo al escalar)
                # ============================================
                try:
                    # Verificar si ya existe conversación
                    conversation = await ConversationService.get_conversation_by_session(session_id)
                    
                    if not conversation:
                        # Crear conversación nueva
                        conversation_data = ConversationCreate(
                            session_id=session_id,
                            id_agente=id_agente,
                            agent_name=agente.nombre_agente,
                            agent_type=agente.tipo_agente,
                            origin=origin
                        )
                        conversation = await ConversationService.create_conversation(conversation_data)
                        logger.info(f"✅ Conversación creada en MongoDB por escalamiento: {session_id}")
                    
                    # Guardar mensaje del usuario
                    user_message = MessageCreate(
                        role=MessageRole.user,
                        content=pregunta
                    )
                    await ConversationService.add_message(session_id, user_message)
                    
                except Exception as e:
                    logger.error(f"❌ Error creando conversación en MongoDB: {e}")
                    # Continuar con escalamiento aunque falle MongoDB
                
                # ============================================
                # PASO 4: ESCALAR CONVERSACIÓN
                # ============================================
                try:
                    resultado = await escalamiento_service.escalar_conversacion(
                        session_id=session_id,
                        id_agente=id_agente,
                        motivo="Solicitado por usuario"
                    )
                    
                    # Enviar mensaje de escalamiento
                    yield {
                        "type": "escalamiento",
                        "content": agente.mensaje_derivacion or "Tu solicitud ha sido escalada...",
                        "metadata": {
                            "escalado": True,
                            "usuarios_notificados": resultado.get("usuarios_notificados", 0),
                            "usuario_nombre": resultado.get("funcionario_asignado", {}).get("nombre"),  # ← AGREGAR
                            "usuario_id": resultado.get("funcionario_asignado", {}).get("id")  # ← AGREGAR
                        }
                    }
                    
                    # Finalizar stream
                    yield {
                        "type": "done",
                        "content": agente.mensaje_derivacion or "Escalado a humano",
                        "metadata": {
                            "agent_id": id_agente,
                            "agent_name": agente.nombre_agente,
                            "session_id": session_id,
                            "escalado": True,
                            "saved_to_mongo": True  # 🔥 Se guardó porque escaló
                        }
                    }
                    
                    return  # Detener flujo normal
                    
                except Exception as e:
                    logger.error(f"❌ Error en escalamiento: {e}")
                    yield {
                        "type": "error",
                        "content": f"Error al escalar: {str(e)}"
                    }
                    return

            # ============================================
            # PASO 5: 🔥 FLUJO NORMAL (SIN GUARDAR EN MONGODB)
            # ============================================
            # Aplicar parámetros
            k_final = k if k is not None else 2
            use_reranking_final = use_reranking if use_reranking is not None else False
            
            temperatura_final = temperatura if temperatura is not None else \
                            (float(agente.temperatura) if agente.temperatura else 0.7)
            
            max_tokens_final = max_tokens if max_tokens is not None else \
                            (int(agente.max_tokens) if agente.max_tokens else 1000)

            system_prompt = build_system_prompt(agente)

            print(f"🔗 Session: {session_id} | Origin: {origin} | Sin guardar en MongoDB")
            self._session_manager.touch(session_id)

            # ============================================
            # PASO 6: BUSCAR CONTEXTO CON RAG
            # ============================================
            yield {
                "type": "status",
                "content": "🔍 Buscando información relevante..."
            }
            
            try:
                results = self.rag.search(
                    id_agente=id_agente, 
                    query=pregunta, 
                    session_id=session_id,
                    n_results=k_final,
                    use_reranking=use_reranking_final,
                    use_priority_boost=True,
                    priority_boost_factor=0.4
                )
                
                if results:
                    contexto_parts = []
                    for i, r in enumerate(results, 1):
                        metadata = r.get('metadata', {})
                        titulo = metadata.get('titulo', 'Sin título')
                        doc = r.get('document', '')
                        contexto_parts.append(f"[Fuente {i}: {titulo}]\n{doc}")
                    
                    contexto = "\n\n".join(contexto_parts)
                    sources_count = len(results)
                else:
                    contexto = "No se encontró información relevante."
                    sources_count = 0
                    
            except Exception as e:
                print(f"Error en RAG: {e}")
                contexto = "Error al buscar información."
                sources_count = 0

            yield {
                "type": "context",
                "content": f"📚 Encontradas {sources_count} fuentes relevantes",
                "sources": sources_count
            }

            # ============================================
            # PASO 7: GENERAR RESPUESTA CON OLLAMA
            # ============================================
            prompt = build_chat_prompt(system_prompt, contexto, pregunta)
            model_name = agente.modelo_ia or "llama3"

            print(f"🤖 Streaming - Modelo: {model_name}")
            print(f"🌡️  Temperatura: {temperatura_final}")
            print(f"📊 Fuentes RAG: {sources_count}")

            yield {
                "type": "status",
                "content": "💬 Generando respuesta..."
            }

            full_response = ""
            
            try:
                for token in self.client.generate_stream(
                    model_name=model_name,
                    prompt=prompt,
                    temperature=temperatura_final,
                    max_tokens=max_tokens_final,
                    options={"keep_alive": "15m"}
                ):
                    full_response += token
                    
                    yield {
                        "type": "token",
                        "content": token
                    }
                
                # ============================================
                # PASO 8: 🔥 NO GUARDAR EN MONGODB (modo normal)
                # ============================================
                yield {
                    "type": "done",
                    "content": full_response,
                    "metadata": {
                        "agent_id": id_agente,
                        "agent_name": agente.nombre_agente,
                        "session_id": session_id,
                        "origin": origin,
                        "sources_used": sources_count,
                        "model_used": model_name,
                        "saved_to_mongo": False,  # 🔥 No se guardó
                        "params_used": {
                            "temperatura": temperatura_final,
                            "max_tokens": max_tokens_final,
                            "k": k_final,
                            "use_reranking": use_reranking_final
                        }
                    }
                }

            except Exception as e:
                error_msg = str(e)
                print(f"❌ Error con Ollama: {error_msg}")
                
                if "not found" in error_msg.lower():
                    yield {
                        "type": "status",
                        "content": f"⚠️ Modelo {model_name} no disponible, usando llama3..."
                    }
                    
                    full_response = ""
                    for token in self.client.generate_stream(
                        model_name="llama3",
                        prompt=prompt,
                        temperature=temperatura_final,
                        max_tokens=max_tokens_final,
                        options={"keep_alive": "15m"}
                    ):
                        full_response += token
                        yield {
                            "type": "token",
                            "content": token
                        }
                    
                    yield {
                        "type": "done",
                        "content": full_response,
                        "metadata": {
                            "agent_id": id_agente,
                            "agent_name": agente.nombre_agente,
                            "model_used": "llama3 (fallback)",
                            "saved_to_mongo": False,
                            "warning": f"Modelo {model_name} no disponible"
                        }
                    }
                else:
                    raise Exception(f"Error en Ollama: {error_msg}")

        except Exception as e:
            yield {
                "type": "error",
                "content": str(e)
            }


    def list_available_models(self) -> List[str]:
        """Lista modelos disponibles en Ollama"""
        try:
                models = self.client.list_models()
                return [m.get("name", "unknown") for m in models]
        except Exception as e:
                print(f"Error listando modelos: {e}")
                return []


    def generar_session_id() -> str:
            """
            Genera un session_id único para nuevas conversaciones
            
            Returns:
                str: UUID v4 como string
            """
            return str(uuid.uuid4())