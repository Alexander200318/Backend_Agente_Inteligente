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
        self.api_version = None  # 🔥 Detectar versión automáticamente

    def _detect_api_version(self):
        """
        Detecta qué versión de la API usar
        - Versiones viejas: /api/generate
        - Versiones nuevas (0.5.0+): /api/chat
        """
        if self.api_version is not None:
            return self.api_version
        
        # Probar /api/chat primero (versión nueva)
        try:
            test_url = f"{self.base}/api/chat"
            response = requests.post(
                test_url,
                json={
                    "model": "llama3",
                    "messages": [{"role": "user", "content": "test"}],
                    "stream": False
                },
                timeout=5
            )
            
            if response.status_code != 404:
                self.api_version = "chat"
                print("✅ Ollama API: Usando /api/chat (versión nueva)")
                return "chat"
        except:
            pass
        
        # Fallback a /api/generate (versión vieja)
        self.api_version = "generate"
        print("✅ Ollama API: Usando /api/generate (versión vieja)")
        return "generate"

    def generate(
        self, 
        model_name: str, 
        prompt: str, 
        stream: bool = False, 
        temperature: float = 0.7,
        max_tokens: int = 2000,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Genera respuesta con Ollama (compatible con ambas versiones)
        """
        api_version = self._detect_api_version()
        
        # Opciones por defecto
        default_options = {
            "num_predict": max_tokens,
            "temperature": temperature,
            "top_p": 0.7,
            "top_k": 25
        }
        
        if options:
            default_options.update(options)
        
        try:
            if api_version == "chat":
                # 🔥 API nueva: /api/chat
                url = f"{self.base}/api/chat"
                payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "stream": stream,
                    "options": default_options
                }
                
                r = requests.post(url, json=payload, timeout=120)
                r.raise_for_status()
                
                if stream:
                    return {"response": "Streaming no implementado"}
                
                data = r.json()
                
                # Extraer contenido de la respuesta
                message_content = ""
                if "message" in data:
                    message_content = data["message"].get("content", "")
                
                return {
                    "response": message_content,
                    "model": data.get("model", model_name),
                    "done": data.get("done", False)
                }
            
            else:
                # 🔥 API vieja: /api/generate
                url = f"{self.base}/api/generate"
                payload = {
                    "model": model_name,
                    "prompt": prompt,
                    "stream": stream,
                    "options": default_options
                }
                
                r = requests.post(url, json=payload, timeout=120)
                r.raise_for_status()
                
                if stream:
                    return {"response": "Streaming no implementado"}
                
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
        Compatible con ambas versiones de la API
        """
        api_version = self._detect_api_version()
        
        # Opciones
        default_options = {
            "num_predict": max_tokens,
            "temperature": temperature,
            "top_p": 0.7,
            "top_k": 25
        }
        
        if options:
            default_options.update(options)
        
        try:
            if api_version == "chat":
                # 🔥 API nueva: /api/chat
                url = f"{self.base}/api/chat"
                payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "stream": True,
                    "options": default_options
                }
                
                with requests.post(url, json=payload, stream=True, timeout=120) as response:
                    response.raise_for_status()
                    
                    for line in response.iter_lines():
                        if line:
                            try:
                                chunk_data = json.loads(line)
                                
                                # En /api/chat, el texto está en message.content
                                if "message" in chunk_data:
                                    text_chunk = chunk_data["message"].get("content", "")
                                    if text_chunk:
                                        yield text_chunk
                                
                                if chunk_data.get("done", False):
                                    break
                                    
                            except json.JSONDecodeError:
                                continue
            
            else:
                # 🔥 API vieja: /api/generate
                url = f"{self.base}/api/generate"
                payload = {
                    "model": model_name,
                    "prompt": prompt,
                    "stream": True,
                    "options": default_options
                }
                
                with requests.post(url, json=payload, stream=True, timeout=120) as response:
                    response.raise_for_status()
                    
                    for line in response.iter_lines():
                        if line:
                            try:
                                chunk_data = json.loads(line)
                                
                                if "response" in chunk_data:
                                    text_chunk = chunk_data["response"]
                                    if text_chunk:
                                        yield text_chunk
                                
                                if chunk_data.get("done", False):
                                    break
                                    
                            except json.JSONDecodeError:
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