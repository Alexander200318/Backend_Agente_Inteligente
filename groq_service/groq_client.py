"""Cliente para interactuar con la API de Groq"""

from groq import Groq
from typing import Optional, List, Dict, Any
import logging
from core.config import settings

logger = logging.getLogger(__name__)


class GroqClient:
    """Cliente para comunicarse con Groq API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa el cliente de Groq
        
        Args:
            api_key: API key de Groq (si no se proporciona, usa la del settings)
        """
        self.api_key = api_key or settings.GROQ_API_KEY
        if not self.api_key:
            raise ValueError("GROQ_API_KEY no está configurado en variables de entorno")
        
        self.client = Groq(api_key=self.api_key)
        self.model = settings.GROQ_MODEL
        self.timeout = settings.GROQ_TIMEOUT
        self.max_tokens = settings.GROQ_MAX_TOKENS
        self.temperature = settings.GROQ_TEMPERATURE
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Realiza una solicitud de chat completion a Groq
        
        Args:
            messages: Lista de mensajes con estructura [{"role": "user/assistant", "content": "..."}]
            model: Modelo a usar (si no se proporciona, usa el del settings)
            max_tokens: Máximo de tokens en la respuesta
            temperature: Temperatura para generación
            **kwargs: Argumentos adicionales para la API
        
        Returns:
            Dict con la respuesta de Groq
        """
        try:
            model = model or self.model
            max_tokens = max_tokens or self.max_tokens
            temperature = temperature if temperature is not None else self.temperature
            
            logger.info(f"📤 Enviando solicitud a Groq - Modelo: {model}, Tokens: {max_tokens}")
            
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=self.timeout,
                **kwargs
            )
            
            logger.info(f"✅ Respuesta recibida de Groq - {response.usage.completion_tokens} tokens usados")
            
            return {
                "content": response.choices[0].message.content,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "stop_reason": response.choices[0].finish_reason
            }
        
        except Exception as e:
            logger.error(f"❌ Error en chat_completion con Groq: {str(e)}")
            raise
    
    async def chat_completion_async(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Versión asincrónica de chat_completion
        Por ahora, envuelve la versión síncrona
        """
        return self.chat_completion(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )
    
    def streaming_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ):
        """
        Chat con streaming - genera respuestas incrementalmente
        
        Yields:
            Strings con fragmentos de la respuesta
        """
        try:
            model = model or self.model
            max_tokens = max_tokens or self.max_tokens
            temperature = temperature if temperature is not None else self.temperature
            
            logger.info(f"📤 Iniciando streaming con Groq - Modelo: {model}")
            
            with self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                timeout=self.timeout,
                **kwargs
            ) as response:
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            
            logger.info("✅ Streaming completado")
        
        except Exception as e:
            logger.error(f"❌ Error en streaming_chat con Groq: {str(e)}")
            raise
    
    def list_available_models(self) -> List[str]:
        """
        Lista modelos disponibles en Groq
        
        Returns:
            Lista de nombres de modelos
        """
        try:
            logger.info("📋 Obteniendo lista de modelos disponibles de Groq")
            
            models = self.client.models.list()
            model_list = [model.id for model in models.data]
            
            logger.info(f"✅ Modelos encontrados: {len(model_list)}")
            return model_list
        
        except Exception as e:
            logger.error(f"❌ Error al obtener modelos: {str(e)}")
            raise
