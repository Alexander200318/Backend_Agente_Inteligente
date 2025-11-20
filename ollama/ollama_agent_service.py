# app/ollama/ollama_agent_service.py
from ollama.ollama_client import OllamaClient
from ollama.prompt_builder import build_system_prompt, build_chat_prompt
from rag.rag_service import RAGService
from sqlalchemy.orm import Session
from models.agente_virtual import AgenteVirtual

class OllamaAgentService:
    def __init__(self, db: Session):
        self.db = db
        self.client = OllamaClient()
        self.rag = RAGService(db)

    def _agent_model_name(self, agente: AgenteVirtual) -> str:
        return f"agente_{agente.id_agente}"

    def chat_with_agent(self, id_agente: int, pregunta: str, k: int = 4):
        agente = self.db.query(AgenteVirtual).filter(AgenteVirtual.id_agente == id_agente).first()
        if not agente:
            raise Exception("Agente no encontrado")

        # 1) construir prompt del sistema desde agente
        system_prompt = build_system_prompt(agente)

        # 2) obtener contexto con RAG (solo para ese agente)
        contexto = self.rag.generar_contexto_unificado(id_agente, pregunta)

        # 3) construir prompt final
        prompt = build_chat_prompt(system_prompt, contexto, pregunta)

        # 4) llamar a Ollama con nombre de modelo (suponemos nombre 'agente_{id_agente}' creado o usar base)
        model_name = self._agent_model_name(agente)
        try:
            res = self.client.generate(model_name, prompt, stream=False, max_tokens=int(getattr(agente, "max_tokens", 1000)))
            # Respuesta de Ollama según su API: ajustar si devuelve lista/objeto
            return res
        except Exception as e:
            # fallback: usar modelo base directamente con el prompt (no ideal pero funcional)
            fallback = self.client.generate("llama3:8b", prompt, stream=False)
            return fallback
