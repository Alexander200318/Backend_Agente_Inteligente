# routers/websocket_router.py (ARCHIVO NUEVO)
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from database.database import get_db
from services.websocket_manager import manager
from services.conversation_service import ConversationService
from services.escalamiento_service import EscalamientoService
from models.conversation_mongo import MessageCreate, MessageRole
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/chat/{session_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    WebSocket para chat en tiempo real
    
    Clientes:
    - Widget (usuario final)
    - Interface de humano (funcionario)
    
    Mensajes:
    {
        "type": "message",
        "content": "texto del mensaje",
        "user_id": 123,  // Solo para humanos
        "user_name": "Juan Pérez"  // Solo para humanos
    }
    
    {
        "type": "typing",
        "user_name": "Juan Pérez"
    }
    
    {
        "type": "join",
        "user_id": 123,
        "user_name": "Juan Pérez",
        "role": "human" | "user"
    }
    """
    
    await manager.connect(websocket, session_id)
    escalamiento_service = EscalamientoService(db)
    
    try:
        # Verificar si conversación existe y está escalada
        conversation = await ConversationService.get_conversation_by_session(session_id)
        
        if conversation and conversation.metadata.estado == "escalada_humano":
            # ✅ CORREGIDO: Usar el nombre correcto del atributo
            await manager.send_personal_message({
                "type": "escalamiento_info",
                "escalado": True,
                "usuario_asignado": conversation.metadata.escalado_a_usuario_id,
                "usuario_nombre": conversation.metadata.escalado_a_usuario_nombre  # ← CORRECTO
            }, websocket)
            
            logger.info(f"✅ WebSocket conectado a conversación escalada: {session_id} → {conversation.metadata.escalado_a_usuario_nombre}")
        else:
            logger.info(f"✅ WebSocket conectado a conversación normal: {session_id}")
        
        # Loop principal
        while True:
            # Recibir mensaje
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            message_type = message_data.get("type")
            
            # ============================================
            # TIPO: message (enviar mensaje)
            # ============================================
            if message_type == "message":
                content = message_data.get("content")
                user_id = message_data.get("user_id")
                user_name = message_data.get("user_name")
                
                if not content:
                    continue
                
                # Determinar rol
                if user_id:
                    # Es un humano respondiendo
                    role = MessageRole.human_agent
                    
                    # Guardar en MongoDB
                    message = MessageCreate(
                        role=role,
                        content=content,
                        user_id=user_id,
                        user_name=user_name
                    )
                    await ConversationService.add_message(session_id, message)
                    
                    # Broadcast a todos
                    await manager.broadcast({
                        "type": "message",
                        "role": "human_agent",
                        "content": content,
                        "user_id": user_id,
                        "user_name": user_name,
                        "timestamp": message.timestamp.isoformat() if hasattr(message, 'timestamp') else None
                    }, session_id)
                    
                    logger.info(f"💬 Mensaje de humano {user_name} en session {session_id}")
                
                else:
                    # Es el usuario final (widget)
                    role = MessageRole.user
                    
                    # Guardar en MongoDB
                    message = MessageCreate(
                        role=role,
                        content=content
                    )
                    await ConversationService.add_message(session_id, message)
                    
                    # Broadcast a todos
                    await manager.broadcast({
                        "type": "message",
                        "role": "user",
                        "content": content,
                        "timestamp": message.timestamp.isoformat() if hasattr(message, 'timestamp') else None
                    }, session_id)
                    
                    logger.info(f"💬 Mensaje de usuario en session {session_id}")
            
            # ============================================
            # TIPO: typing (indicador de escritura)
            # ============================================
            elif message_type == "typing":
                user_name = message_data.get("user_name", "Usuario")
                
                await manager.broadcast({
                    "type": "typing",
                    "user_name": user_name,
                    "is_typing": message_data.get("is_typing", True)
                }, session_id)
            
            # ============================================
            # TIPO: join (notificar que alguien se unió)
            # ============================================
            elif message_type == "join":
                user_name = message_data.get("user_name", "Usuario")
                role = message_data.get("role", "user")
                
                await manager.broadcast({
                    "type": "user_joined",
                    "user_name": user_name,
                    "role": role
                }, session_id)
                
                logger.info(f"👋 {user_name} ({role}) se unió a session {session_id}")
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
        logger.info(f"🔌 Cliente desconectado de session {session_id}")
    
    except Exception as e:
        logger.error(f"❌ Error en WebSocket: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "content": "Error en el servidor WebSocket"
            })
        except:
            pass
        manager.disconnect(websocket, session_id)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
        logger.info(f"🔌 Cliente desconectado de session {session_id}")
    
    except Exception as e:
        logger.error(f"❌ Error en WebSocket: {e}")
        manager.disconnect(websocket, session_id)
