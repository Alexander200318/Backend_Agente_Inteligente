"""Router para endpoints de Groq AI"""

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from pydantic import BaseModel
import logging

from database.database import get_db
from groq_service.groq_agent_service import GroqAgentService
from auth.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/groq", tags=["Groq AI"])


# =============================================
# MODELOS PYDANTIC
# =============================================

class ChatRequest(BaseModel):
    """Solicitud de chat con Groq"""
    id_agente: int
    mensaje: str
    session_id: str
    origin: str = "web"
    temperatura: Optional[float] = None
    max_tokens: Optional[int] = None
    k: Optional[int] = None
    use_reranking: Optional[bool] = None


class ChatResponse(BaseModel):
    """Respuesta de chat con Groq"""
    id_conversacion: Optional[int]
    respuesta: str
    modelo_usado: str
    tokens_usados: int
    documentos_recuperados: int
    fuente: str


class TestConnectionResponse(BaseModel):
    """Respuesta de prueba de conexión"""
    estado: str
    modelo: Optional[str] = None
    respuesta: Optional[str] = None
    error: Optional[str] = None


# =============================================
# ENDPOINTS
# =============================================

@router.post("/chat", response_model=ChatResponse)
async def chat_with_groq(
    request: ChatRequest,
    db: Session = Depends(get_db)
) -> ChatResponse:
    """
    Chat con agente virtual usando Groq
    
    - **id_agente**: ID del agente virtual
    - **mensaje**: Mensaje del usuario
    - **session_id**: ID de sesión
    - **origin**: Origen de la solicitud (web, widget, etc)
    - **temperatura**: Temperatura para generación (0.0-1.0)
    - **max_tokens**: Máximo tokens en respuesta
    - **k**: Número de documentos RAG
    - **use_reranking**: Usar reranking en RAG
    
    Returns:
        Respuesta del agente con metadata
    """
    try:
        logger.info(f"📨 Chat request recibida - Agente: {request.id_agente}, Sesión: {request.session_id}")
        
        service = GroqAgentService(db)
        
        result = await service.chat_with_agent(
            id_agente=request.id_agente,
            pregunta=request.mensaje,
            session_id=request.session_id,
            origin=request.origin,
            temperatura=request.temperatura,
            max_tokens=request.max_tokens,
            k=request.k,
            use_reranking=request.use_reranking
        )
        
        logger.info(f"✅ Chat completado - Tokens: {result['tokens_usados']}")
        
        return ChatResponse(
            id_conversacion=result.get("id_conversacion"),
            respuesta=result["respuesta"],
            modelo_usado=result["modelo_usado"],
            tokens_usados=result["tokens_usados"],
            documentos_recuperados=result["documentos_recuperados"],
            fuente=result["fuente"]
        )
    
    except Exception as e:
        logger.error(f"❌ Error en chat_with_groq: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar solicitud: {str(e)}"
        )


@router.websocket("/chat/stream/{session_id}/{id_agente}")
async def websocket_chat_groq(
    websocket: WebSocket,
    session_id: str,
    id_agente: int,
    db: Session = Depends(get_db)
):
    """
    WebSocket para chat con streaming usando Groq
    
    - **session_id**: ID de sesión del usuario
    - **id_agente**: ID del agente virtual
    
    Espera mensajes JSON con estructura:
    {
        "mensaje": "pregunta del usuario",
        "origen": "web",
        "temperatura": 0.7,
        "max_tokens": 2000
    }
    """
    await websocket.accept()
    
    try:
        logger.info(f"🔌 WebSocket conectado - Sesión: {session_id}, Agente: {id_agente}")
        
        service = GroqAgentService(db)
        
        async for data in websocket.iter_json():
            try:
                mensaje = data.get("mensaje", "")
                origen = data.get("origen", "web")
                temperatura = data.get("temperatura")
                max_tokens = data.get("max_tokens")
                k = data.get("k")
                use_reranking = data.get("use_reranking")
                
                if not mensaje:
                    await websocket.send_json({
                        "error": "El mensaje no puede estar vacío"
                    })
                    continue
                
                logger.info(f"💬 Mensaje recibido: {mensaje[:50]}...")
                
                # Enviar respuesta en streaming
                await websocket.send_json({
                    "tipo": "inicio",
                    "mensaje": "Procesando...",
                    "agente_id": id_agente
                })
                
                async for chunk in service.chat_with_agent_streaming(
                    id_agente=id_agente,
                    pregunta=mensaje,
                    session_id=session_id,
                    origin=origen,
                    temperatura=temperatura,
                    max_tokens=max_tokens,
                    k=k,
                    use_reranking=use_reranking
                ):
                    await websocket.send_json({
                        "tipo": "chunk",
                        "contenido": chunk
                    })
                
                await websocket.send_json({
                    "tipo": "fin",
                    "mensaje": "Respuesta completada"
                })
                
                logger.info("✅ Streaming completado")
            
            except Exception as e:
                logger.error(f"❌ Error procesando mensaje: {str(e)}")
                await websocket.send_json({
                    "tipo": "error",
                    "error": str(e)
                })
    
    except Exception as e:
        logger.error(f"❌ Error en WebSocket: {str(e)}")
        try:
            await websocket.send_json({
                "tipo": "error",
                "error": f"Error de conexión: {str(e)}"
            })
        except:
            pass
    
    finally:
        await websocket.close()
        logger.info(f"🔌 WebSocket cerrado - Sesión: {session_id}")


@router.get("/test", response_model=TestConnectionResponse)
async def test_groq_connection(db: Session = Depends(get_db)) -> TestConnectionResponse:
    """
    Prueba la conexión con Groq API
    
    Returns:
        Estado de la conexión y respuesta de prueba
    """
    try:
        logger.info("🧪 Iniciando prueba de conexión a Groq...")
        
        service = GroqAgentService(db)
        result = service.test_connection()
        
        logger.info(f"✅ Prueba completada: {result['estado']}")
        
        return TestConnectionResponse(**result)
    
    except Exception as e:
        logger.error(f"❌ Error en test de conexión: {str(e)}")
        return TestConnectionResponse(
            estado="error",
            error=str(e)
        )


@router.get("/models")
async def list_groq_models(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Lista modelos disponibles en Groq
    
    Returns:
        Lista de modelos y estado
    """
    try:
        logger.info("📋 Obteniendo lista de modelos de Groq...")
        
        service = GroqAgentService(db)
        models = service.client.list_available_models()
        
        logger.info(f"✅ {len(models)} modelos disponibles")
        
        return {
            "total": len(models),
            "modelos": models,
            "estado": "éxito"
        }
    
    except Exception as e:
        logger.error(f"❌ Error al obtener modelos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener modelos: {str(e)}"
        )


@router.post("/verify-api-key")
async def verify_groq_api_key() -> Dict[str, Any]:
    """
    Verifica que la API key de Groq sea válida
    
    Returns:
        Estado de verificación
    """
    try:
        logger.info("🔑 Verificando API key de Groq...")
        
        # Intentar hacer una solicitud mínima
        db = None  # No necesitamos DB para esta verificación
        service = GroqAgentService(db) if db else GroqAgentService.__new__(GroqAgentService)
        
        # Inicializar solo el cliente
        from groq_service.groq_client import GroqClient
        client = GroqClient()
        
        result = client.chat_completion(
            messages=[{"role": "user", "content": "test"}],
            max_tokens=10
        )
        
        logger.info("✅ API key válida")
        
        return {
            "valida": True,
            "modelo": result["model"],
            "mensaje": "API key de Groq verificada correctamente"
        }
    
    except ValueError as e:
        logger.error(f"❌ API key no configurada: {str(e)}")
        return {
            "valida": False,
            "error": "GROQ_API_KEY no está configurado",
            "mensaje": "Por favor, configura la variable GROQ_API_KEY en .env"
        }
    
    except Exception as e:
        logger.error(f"❌ Error verificando API key: {str(e)}")
        return {
            "valida": False,
            "error": str(e),
            "mensaje": "Error al verificar la API key"
        }
