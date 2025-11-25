# app/ollama/ollama_agent_service.py
from ollama.ollama_client import OllamaClient
from ollama.prompt_builder import build_system_prompt, build_chat_prompt
from rag.rag_service import RAGService
from sqlalchemy.orm import Session
from models.agente_virtual import AgenteVirtual
from typing import Dict, Any, List

class OllamaAgentService:
    def __init__(self, db: Session):
        self.db = db
        self.client = OllamaClient()
        self.rag = RAGService(db, use_cache=True)  # 🔥 Habilitar caché

    def chat_with_agent(
        self, 
        id_agente: int, 
        pregunta: str, 
        k: int = 4,
        use_reranking: bool = True
    ) -> Dict[str, Any]:
        """
        Chatea con un agente usando RAG + Ollama
        
        Returns:
            Dict con 'response', 'agent', 'sources_used', etc.
        """
        # 1) Obtener agente
        agente = self.db.query(AgenteVirtual).filter(
            AgenteVirtual.id_agente == id_agente
        ).first()
        
        if not agente:
            raise Exception(f"Agente {id_agente} no encontrado")

        # 2) Construir system prompt
        system_prompt = build_system_prompt(agente)

        # 3) 🔥 Buscar contexto con RAG (MÉTODO CORRECTO)
        try:
            results = self.rag.search(
                id_agente=id_agente, 
                query=pregunta, 
                n_results=k,
                use_reranking=use_reranking,
                use_priority_boost=True,  # 🔥 Habilitar boost
                priority_boost_factor=0.4  # 🔥 Ajustar peso (15% por punto)
            )
            
            # Construir contexto legible
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

        # 4) Construir prompt final
        prompt = build_chat_prompt(system_prompt, contexto, pregunta)

        # 5) 🔥 Llamar a Ollama con modelo correcto
        model_name = agente.modelo_ia or "llama3"
        temperatura = float(agente.temperatura) if agente.temperatura else 0.7
        max_tokens = int(agente.max_tokens) if agente.max_tokens else 1000
        
        try:
            print(f"🤖 Usando modelo: {model_name}")
            print(f"📊 Fuentes RAG: {sources_count}")
            
            res = self.client.generate(
                model_name=model_name,
                prompt=prompt,
                stream=False,
                temperature=temperatura,
                max_tokens=max_tokens
            )
            
            return {
                "ok": True,
                "response": res.get("response", ""),
                "agent_id": id_agente,
                "agent_name": agente.nombre_agente,
                "sources_used": sources_count,
                "model_used": model_name,
                "context_preview": contexto[:200] + "..." if len(contexto) > 200 else contexto
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error con Ollama: {error_msg}")
            
            # Fallback: intentar con modelo base
            if "not found" in error_msg.lower():
                print(f"⚠️ Modelo {model_name} no encontrado, usando llama3")
                try:
                    res = self.client.generate(
                        model_name="llama3",
                        prompt=prompt,
                        stream=False,
                        temperature=temperatura,
                        max_tokens=max_tokens
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

    def list_available_models(self) -> List[str]:
        """Lista modelos disponibles en Ollama"""
        try:
            models = self.client.list_models()
            return [m.get("name", "unknown") for m in models]
        except Exception as e:
            print(f"Error listando modelos: {e}")
            return []