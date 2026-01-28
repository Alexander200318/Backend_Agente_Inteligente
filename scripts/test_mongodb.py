# scripts/test_mongodb.py
"""
Script de prueba para verificar la conexión y operaciones básicas con MongoDB

Ejecutar:
    python scripts/test_mongodb.py
"""
import asyncio
import sys
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.mongodb import init_mongodb, close_mongodb
from services.conversation_service import ConversationService
from models.conversation_mongo import (
    ConversationCreate,
    MessageCreate,
    MessageRole,
    ConversationUpdate,
    ConversationStatus
)


async def test_mongodb_connection():
    """Test 1: Verificar conexión a MongoDB"""
    print("\n" + "="*60)
    print("TEST 1: Conexión a MongoDB")
    print("="*60)
    
    try:
        await init_mongodb()
        print("✅ Conexión a MongoDB exitosa")
        return True
    except Exception as e:
        print(f"❌ Error conectando a MongoDB: {e}")
        return False


async def test_create_conversation():
    """Test 2: Crear una conversación"""
    print("\n" + "="*60)
    print("TEST 2: Crear conversación")
    print("="*60)
    
    try:
        conversation_data = ConversationCreate(
            session_id="test-session-123",
            id_agente=1,
            agent_name="Agente de Prueba",
            agent_type="especializado",
            origin="web",
            ip_origen="127.0.0.1",
            dispositivo="desktop"
        )
        
        conversation = await ConversationService.create_conversation(conversation_data)
        
        print(f"✅ Conversación creada:")
        print(f"   - ID: {conversation.id}")
        print(f"   - Session ID: {conversation.session_id}")
        print(f"   - Agente: {conversation.agent_name}")
        print(f"   - Estado: {conversation.metadata.estado}")
        
        return conversation.session_id
        
    except Exception as e:
        print(f"❌ Error creando conversación: {e}")
        return None


async def test_add_messages(session_id: str):
    """Test 3: Agregar mensajes a la conversación"""
    print("\n" + "="*60)
    print("TEST 3: Agregar mensajes")
    print("="*60)
    
    try:
        # Mensaje del usuario
        user_message = MessageCreate(
            role=MessageRole.user,
            content="Hola, ¿cómo estás?"
        )
        
        await ConversationService.add_message(session_id, user_message)
        print("✅ Mensaje de usuario agregado")
        
        # Mensaje del asistente
        assistant_message = MessageCreate(
            role=MessageRole.assistant,
            content="¡Hola! Estoy bien, ¿en qué puedo ayudarte?",
            sources_used=2,
            model_used="llama-3.1-8b-instant",
            token_count=50
        )
        
        await ConversationService.add_message(session_id, assistant_message)
        print("✅ Mensaje del asistente agregado")
        
        # Otro mensaje del usuario
        user_message_2 = MessageCreate(
            role=MessageRole.user,
            content="Necesito información sobre matrículas"
        )
        
        conversation = await ConversationService.add_message(session_id, user_message_2)
        
        print(f"\n📊 Estadísticas de la conversación:")
        print(f"   - Total mensajes: {conversation.metadata.total_mensajes}")
        print(f"   - Mensajes usuario: {conversation.metadata.total_mensajes_usuario}")
        print(f"   - Mensajes agente: {conversation.metadata.total_mensajes_agente}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error agregando mensajes: {e}")
        return False


async def test_get_conversation(session_id: str):
    """Test 4: Obtener conversación completa"""
    print("\n" + "="*60)
    print("TEST 4: Obtener conversación")
    print("="*60)
    
    try:
        conversation = await ConversationService.get_conversation_by_session(session_id)
        
        if not conversation:
            print(f"❌ Conversación no encontrada: {session_id}")
            return False
        
        print(f"✅ Conversación recuperada:")
        print(f"   - Session ID: {conversation.session_id}")
        print(f"   - Agente: {conversation.agent_name}")
        print(f"   - Total mensajes: {len(conversation.messages)}")
        
        print(f"\n💬 Mensajes:")
        for i, msg in enumerate(conversation.messages, 1):
            print(f"   {i}. [{msg.role}] {msg.content[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error obteniendo conversación: {e}")
        return False


async def test_update_status(session_id: str):
    """Test 5: Actualizar estado de conversación"""
    print("\n" + "="*60)
    print("TEST 5: Actualizar estado")
    print("="*60)
    
    try:
        update_data = ConversationUpdate(
            estado=ConversationStatus.escalada_humano,
            requirio_atencion_humana=True,
            escalado_a_usuario_id=5,
            escalado_a_usuario_nombre="Juan Pérez"
        )
        
        conversation = await ConversationService.update_conversation_status(
            session_id, 
            update_data
        )
        
        print(f"✅ Estado actualizado:")
        print(f"   - Estado: {conversation.metadata.estado}")
        print(f"   - Requirió humano: {conversation.metadata.requirio_atencion_humana}")
        print(f"   - Escalado a: {conversation.metadata.escalado_a_usuario_nombre}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error actualizando estado: {e}")
        return False


async def test_list_conversations():
    """Test 6: Listar conversaciones"""
    print("\n" + "="*60)
    print("TEST 6: Listar conversaciones")
    print("="*60)
    
    try:
        result = await ConversationService.list_conversations(
            page=1,
            page_size=10
        )
        
        print(f"✅ Conversaciones encontradas: {result.total}")
        print(f"   - Página: {result.page}")
        print(f"   - Tamaño: {result.page_size}")
        
        for i, conv in enumerate(result.conversations, 1):
            print(f"\n   {i}. {conv.agent_name}")
            print(f"      Session: {conv.session_id}")
            print(f"      Mensajes: {conv.metadata.total_mensajes}")
            print(f"      Estado: {conv.metadata.estado}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error listando conversaciones: {e}")
        return False


async def test_stats():
    """Test 7: Obtener estadísticas"""
    print("\n" + "="*60)
    print("TEST 7: Estadísticas")
    print("="*60)
    
    try:
        stats = await ConversationService.get_conversation_stats()
        
        print(f"✅ Estadísticas generales:")
        print(f"   - Total conversaciones: {stats.total_conversaciones}")
        print(f"   - Activas: {stats.conversaciones_activas}")
        print(f"   - Finalizadas: {stats.conversaciones_finalizadas}")
        print(f"   - Escaladas: {stats.conversaciones_escaladas}")
        print(f"   - Promedio mensajes: {stats.promedio_mensajes_por_conversacion}")
        
        if stats.calificacion_promedio:
            print(f"   - Calificación promedio: {stats.calificacion_promedio}/5")
        
        return True
        
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas: {e}")
        return False


async def run_all_tests():
    """Ejecutar todos los tests"""
    print("\n" + "="*60)
    print("🧪 INICIANDO TESTS DE MONGODB")
    print("="*60)
    
    session_id = None
    
    try:
        # Test 1: Conexión
        if not await test_mongodb_connection():
            print("\n❌ Test de conexión falló. Verifica que MongoDB esté corriendo.")
            return
        
        # Test 2: Crear conversación
        session_id = await test_create_conversation()
        if not session_id:
            print("\n❌ No se pudo crear conversación de prueba")
            return
        
        # Test 3: Agregar mensajes
        await test_add_messages(session_id)
        
        # Test 4: Obtener conversación
        await test_get_conversation(session_id)
        
        # Test 5: Actualizar estado
        await test_update_status(session_id)
        
        # Test 6: Listar conversaciones
        await test_list_conversations()
        
        # Test 7: Estadísticas
        await test_stats()
        
        print("\n" + "="*60)
        print("✅ TODOS LOS TESTS COMPLETADOS")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error en tests: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Limpiar: eliminar conversación de prueba
        if session_id:
            try:
                await ConversationService.delete_conversation(session_id)
                print(f"\n🗑️ Conversación de prueba eliminada: {session_id}")
            except:
                pass
        
        # Cerrar conexión
        await close_mongodb()


if __name__ == "__main__":
    # Ejecutar tests
    asyncio.run(run_all_tests())
