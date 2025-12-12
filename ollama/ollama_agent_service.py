# app/ollama/ollama_agent_service.py
from ollama.ollama_client import OllamaClient
from ollama.prompt_builder import build_system_prompt, build_chat_prompt
from rag.rag_service import RAGService
from sqlalchemy.orm import Session
from models.agente_virtual import AgenteVirtual
from typing import Dict, Any, List, Optional, Generator 

class OllamaAgentService:
    def __init__(self, db: Session):
        self.db = db
        self.client = OllamaClient()
        self.rag = RAGService(db, use_cache=True)

    def chat_with_agent(
        self, 
        id_agente: int, 
        pregunta: str, 
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

        try:
            results = self.rag.search(
                id_agente=id_agente, 
                query=pregunta, 
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

    def chat_with_agent_stream(
        self, 
        id_agente: int, 
        pregunta: str, 
        k: Optional[int] = None,
        use_reranking: Optional[bool] = None,
        temperatura: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Chatea con agente CON streaming (palabra por palabra)
        
        Yields:
            Dict con eventos:
                - type: "status" | "context" | "token" | "done" | "error"
                - content: contenido del evento
                - metadata: información adicional
        """
        
        try:
            # 1) Obtener agente
            agente = self.db.query(AgenteVirtual).filter(
                AgenteVirtual.id_agente == id_agente
            ).first()
            
            if not agente:
                yield {
                    "type": "error",
                    "content": f"Agente {id_agente} no encontrado"
                }
                return

            # 2) Aplicar jerarquía de parámetros
            k_final = k if k is not None else 2
            use_reranking_final = use_reranking if use_reranking is not None else False
            
            temperatura_final = temperatura if temperatura is not None else \
                               (float(agente.temperatura) if agente.temperatura else 0.7)
            
            max_tokens_final = max_tokens if max_tokens is not None else \
                              (int(agente.max_tokens) if agente.max_tokens else 1000)

            # 3) System prompt
            system_prompt = build_system_prompt(agente)

            # 4) Buscar contexto con RAG
            yield {
                "type": "status",
                "content": "🔍 Buscando información relevante..."
            }
            
            try:
                results = self.rag.search(
                    id_agente=id_agente, 
                    query=pregunta, 
                    n_results=k_final,
                    use_reranking=use_reranking_final,
                    use_priority_boost=True,
                    priority_boost_factor=0.4
                )
                
                # Construir contexto
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

            # 5) Enviar info de contexto
            yield {
                "type": "context",
                "content": f"📚 Encontradas {sources_count} fuentes relevantes",
                "sources": sources_count
            }

            # 6) Construir prompt
            prompt = build_chat_prompt(system_prompt, contexto, pregunta)
            model_name = agente.modelo_ia or "llama3"

            # 7) Logging
            print(f"🤖 Streaming - Modelo: {model_name}")
            print(f"🌡️  Temperatura: {temperatura_final}")
            print(f"📊 Fuentes RAG: {sources_count}")

            # 8) Enviar inicio de generación
            yield {
                "type": "status",
                "content": "💬 Generando respuesta..."
            }

            # 9) STREAMING de tokens desde Ollama
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
                    
                    # Enviar cada token al frontend
                    yield {
                        "type": "token",
                        "content": token
                    }

                # 10) Mensaje final
                yield {
                    "type": "done",
                    "content": full_response,
                    "metadata": {
                        "agent_id": id_agente,
                        "agent_name": agente.nombre_agente,
                        "sources_used": sources_count,
                        "model_used": model_name,
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
                
                # Fallback con modelo base
                if "not found" in error_msg.lower():
                    yield {
                        "type": "status",
                        "content": f"⚠️ Modelo {model_name} no disponible, usando llama3..."
                    }
                    
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

    # 🔥 NUEVO: Chat automático con selección de agente
    def chat_auto_stream(
        self,
        pregunta: str,
        departamento_codigo: str = "",
        k: Optional[int] = None,
        use_reranking: Optional[bool] = None,
        temperatura: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Chat con selección automática de agente basado en departamento
        
        Args:
            pregunta: Pregunta del usuario
            departamento_codigo: Código del departamento (opcional)
            k, use_reranking, temperatura, max_tokens: Parámetros opcionales
            
        Yields:
            Dict con eventos de streaming
        """
        try:
            yield {
                "type": "status",
                "content": "🔍 Seleccionando agente apropiado..."
            }
            
            # 1) Seleccionar agente basado en departamento
            query = self.db.query(AgenteVirtual)
            
            if departamento_codigo:
                # Buscar agente específico por departamento
                agente = query.filter(
                    AgenteVirtual.departamento_codigo == departamento_codigo,
                    AgenteVirtual.activo == True
                ).first()
                
                if not agente:
                    yield {
                        "type": "error",
                        "content": f"No se encontró agente para el departamento: {departamento_codigo}"
                    }
                    return
            else:
                # Sin departamento: usar agente por defecto o el primero activo
                agente = query.filter(
                    AgenteVirtual.activo == True
                ).order_by(AgenteVirtual.id_agente).first()
                
                if not agente:
                    yield {
                        "type": "error",
                        "content": "No hay agentes activos disponibles"
                    }
                    return

            # 2) Notificar agente seleccionado
            yield {
                "type": "agent_selected",
                "content": f"🤖 Usando agente: {agente.nombre_agente}",
                "agent_id": agente.id_agente,
                "agent_name": agente.nombre_agente
            }

            # 3) Delegar al método de streaming normal
            for event in self.chat_with_agent_stream(
                id_agente=agente.id_agente,
                pregunta=pregunta,
                k=k,
                use_reranking=use_reranking,
                temperatura=temperatura,
                max_tokens=max_tokens
            ):
                yield event

        except Exception as e:
            yield {
                "type": "error",
                "content": f"Error en chat automático: {str(e)}"
            }

    def list_available_models(self) -> List[str]:
        """Lista modelos disponibles en Ollama"""
        try:
            models = self.client.list_models()
            return [m.get("name", "unknown") for m in models]
        except Exception as e:
            print(f"Error listando modelos: {e}")
            return []