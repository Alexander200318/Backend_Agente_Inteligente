# app/ollama/ollama_client.py
import requests
from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any, Generator
import json

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
        max_tokens: int = 2000,
        options: Optional[Dict] = None  # 🔥 NUEVO: acepta options personalizadas
    ) -> Dict[str, Any]:
        """
        Genera respuesta con Ollama
        
        Returns:
            Dict con 'response' y metadata
        """
        url = f"{self.base}/api/generate"
        
        # 🔥 Merge de options por defecto + personalizadas
        default_options = {
            "num_predict": max_tokens,
            "temperature": temperature,
            "top_p": 0.7,
            "top_k": 25
        }
        
        if options:
            default_options.update(options)
        
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": stream,
            "options": default_options
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

    # 🔥 NUEVO: Método con streaming
    def generate_stream(
        self,
        model_name: str,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        options: Optional[Dict] = None
    ) -> Generator[str, None, None]:
        """
        Genera respuesta con streaming (palabra por palabra)
        
        Args:
            model_name: Nombre del modelo (ej: "llama3")
            prompt: Prompt completo
            temperature: Temperatura (0.0-1.0)
            max_tokens: Máximo de tokens a generar
            options: Opciones adicionales (ej: {"keep_alive": "15m"})
        
        Yields:
            str: Fragmentos de texto a medida que se generan
            
        Example:
            >>> for chunk in client.generate_stream("llama3", "Hola"):
            ...     print(chunk, end='', flush=True)
        """
        url = f"{self.base}/api/generate"
        
        # Merge de options
        default_options = {
            "num_predict": max_tokens,
            "temperature": temperature,
            "top_p": 0.7,
            "top_k": 25
        }
        
        if options:
            default_options.update(options)
        
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": True,  # ← Activar streaming
            "options": default_options
        }
        
        try:
            with requests.post(url, json=payload, stream=True, timeout=120) as response:
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk_data = json.loads(line)
                            
                            # Ollama envía el texto en el campo "response"
                            if "response" in chunk_data:
                                text_chunk = chunk_data["response"]
                                if text_chunk:  # Solo yield si hay contenido
                                    yield text_chunk
                            
                            # Verificar si terminó
                            if chunk_data.get("done", False):
                                break
                                
                        except json.JSONDecodeError as e:
                            print(f"⚠️ Error decodificando JSON: {e}")
                            continue
                            
        except requests.exceptions.ConnectionError:
            raise Exception(
                "No se puede conectar a Ollama. "
                "Asegúrate de que esté corriendo: ollama serve"
            )
        except requests.exceptions.Timeout:
            raise Exception("Timeout esperando respuesta de Ollama")
        except Exception as e:
            raise Exception(f"Error en streaming de Ollama: {str(e)}")

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