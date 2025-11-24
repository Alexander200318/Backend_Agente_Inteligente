# app/ollama/ollama_client.py
import requests
from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any

class OllamaSettings(BaseSettings):
    OLLAMA_HOST: str = "http://localhost:11434"

settings = OllamaSettings()

class OllamaClient:
    def __init__(self, base_url: str = None):
        self.base = (base_url or settings.OLLAMA_HOST).rstrip("/")

    def generate(
        self, 
        model_name: str, 
        prompt: str, 
        stream: bool = False, 
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Genera respuesta con Ollama
        
        Returns:
            Dict con 'response' y metadata
        """
        url = f"{self.base}/api/generate"
        
        # 🔥 Usar formato correcto de Ollama
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "num_predict": max_tokens,  # ✅ Correcto para Ollama
                "temperature": temperature,
                "top_p": 0.9,
                "top_k": 40
            }
        }
        
        try:
            r = requests.post(url, json=payload, timeout=120)
            r.raise_for_status()
            
            if stream:
                # Manejar streaming (para futuro)
                return {"response": "Streaming no implementado aún"}
            
            data = r.json()
            return {
                "response": data.get("response", ""),
                "model": data.get("model", model_name),
                "done": data.get("done", False),
                "context": data.get("context", [])
            }
            
        except requests.exceptions.ConnectionError:
            raise Exception(
                "No se puede conectar a Ollama. "
                "Asegúrate de que esté corriendo: ollama serve"
            )
        except requests.exceptions.Timeout:
            raise Exception("Timeout esperando respuesta de Ollama")
        except Exception as e:
            raise Exception(f"Error en Ollama: {str(e)}")

    def list_models(self) -> list:
        """Lista modelos disponibles en Ollama"""
        url = f"{self.base}/api/tags"
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            return r.json().get("models", [])
        except Exception as e:
            print(f"Error listando modelos: {e}")
            return []

    def create(self, name: str, modelfile_text: str):
        """Crea modelo personalizado (Modelfile)"""
        url = f"{self.base}/api/create"
        r = requests.post(
            url, 
            json={"name": name, "modelfile": modelfile_text}, 
            timeout=300
        )
        r.raise_for_status()
        return r.json()

    def delete(self, name: str):
        """Elimina modelo"""
        url = f"{self.base}/api/delete"
        r = requests.delete(url, json={"name": name}, timeout=120)
        r.raise_for_status()
        return r.json()