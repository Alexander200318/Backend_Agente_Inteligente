# app/ollama/ollama_client.py
import requests
from pydantic_settings import BaseSettings

class OllamaSettings(BaseSettings):
    OLLAMA_HOST: str = "http://localhost:11434"

settings = OllamaSettings()

class OllamaClient:
    def __init__(self, base_url: str = None):
        self.base = (base_url or settings.OLLAMA_HOST).rstrip("/")

    def generate(self, model_name: str, prompt: str, stream: bool = False, max_tokens: int = 2000):
        url = f"{self.base}/api/generate"
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": stream,
            "max_tokens": max_tokens
        }
        r = requests.post(url, json=payload, timeout=120)
        r.raise_for_status()
        return r.json()

    def create(self, name: str, modelfile_text: str):
        url = f"{self.base}/api/create"
        r = requests.post(url, json={"name": name, "modelfile": modelfile_text}, timeout=300)
        r.raise_for_status()
        return r.json()

    def delete(self, name: str):
        url = f"{self.base}/api/delete"
        r = requests.delete(url, json={"name": name}, timeout=120)
        r.raise_for_status()
        return r.json()
