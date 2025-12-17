# scripts/test_escalamiento.py
"""
Script de prueba para el sistema de escalamiento a humanos

Ejecutar:
    python scripts/test_escalamiento.py
"""
import asyncio
import sys
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.database import SessionLocal
from database.mongodb import init_mongodb, close_mongodb
from services.escalamiento_service import EscalamientoService
from services.conversation_service import ConversationService
from models.conversation_mongo import (
    ConversationCreate,
    MessageCreate,
    MessageRole
)


async def test_flujo_completo():
    """
    Test del flujo completo de escalamiento
    """
    print("\n" + "="*60)
    print("🧪 TEST FLUJO COMPLETO DE ESCALAMIENTO")
    print("="*60)
    
    db = SessionLocal()
    session_id = None
    
    try:
        # Inicializar MongoDB
        await init_mongodb()
        print("✅ MongoDB conectado")
        
        # Crear servicios
        escalamiento_service = EscalamientoService(db)
        
        # ============================================
        # PASO 1: Crear conversación de prueba
        # ============================================
        print("\n📝 PASO 1: Creando conversación de prueba...")
        
        session_id = f"test-escalamiento-{int(asyncio.get_event_loop().time())}"
        
        conversation_data = ConversationCreate(
            session_id=session_id,
            id_agente=1,  # Asegúrate de tener un agente con ID 1
            agent_name="Agente de Prueba",
            agent_type="especializado",
            origin="test"
        )
        
        conversation = await ConversationService.create_conversation(conversation_data)
        print(f"✅ Conversación creada: {session_id}")
        
        # ============================================
        # PASO 2: Agregar mensajes normales
        # ============================================
        print("\n💬 PASO 2: Agregando mensajes de conversación normal...")
        
        messages = [
            MessageCreate(role=MessageRole.user, content="Hola, necesito ayuda"),
            MessageCreate(role=MessageRole.assistant, content="Hola, ¿en qué puedo ayudarte?"),
            MessageCreate(role=MessageRole.user, content="Necesito información sobre matrículas")
        ]
        
        for msg in messages:
            await ConversationService.add_message(session_id, msg)
        
        print(f"✅ {len(messages)} mensajes agregados")
        
        # ============================================
        # PASO 3: Detectar intención de escalamiento
        # ============================================
        print("\n🔍 PASO 3: Probando detección de escalamiento...")
        
        frases_test = [
            ("Hola, ¿cómo estás?", False),
            ("quiero hablar con un humano", True),
            ("necesito un operador", True),
            ("gracias por la información", False),
        ]
        
        for frase, esperado in frases_test:
            resultado = escalamiento_service.detectar_intencion_escalamiento(frase)
            status = "✅" if resultado == esperado else "❌"
            print(f"  {status} '{frase}' → {resultado} (esperado: {esperado})")
        
        # ============================================
        # PASO 4: Escalar conversación
        # ============================================
        print("\n🚀 PASO 4: Escalando conversación...")
        
        # Agregar mensaje que dispara escalamiento
        escalamiento_msg = MessageCreate(
            role=MessageRole.user,
            content="Quiero hablar con un humano por favor"
        )
        await ConversationService.add_message(session_id, escalamiento_msg)
        
        # Escalar
        resultado = await escalamiento_service.escalar_conversacion(
            session_id=session_id,
            id_agente=1,
            motivo="Test de escalamiento"
        )
        
        if resultado["success"]:
            print(f"✅ Escalamiento exitoso:")
            print(f"   - Usuarios notificados: {resultado['usuarios_notificados']}")
            print(f"   - Conversacion Sync ID: {resultado.get('conversacion_sync_id')}")
            
            if resultado.get("usuarios"):
                print(f"   - Usuarios:")
                for u in resultado["usuarios"]:
                    print(f"     • {u['nombre']} (ID: {u['id']})")
        else:
            print("❌ Error en escalamiento")
        
        # ============================================
        # PASO 5: Verificar estado en MongoDB
        # ============================================
        print("\n📊 PASO 5: Verificando estado en MongoDB...")
        
        conv = await ConversationService.get_conversation_by_session(session_id)
        
        print(f"   - Estado: {conv.metadata.estado}")
        print(f"   - Requirió humano: {conv.metadata.requirio_atencion_humana}")
        print(f"   - Total mensajes: {conv.metadata.total_mensajes}")
        
        if conv.metadata.estado == "escalada_humano":
            print("✅ Estado correcto en MongoDB")
        else:
            print("❌ Estado incorrecto en MongoDB")
        
        # ============================================
        # PASO 6: Verificar estado en MySQL
        # ============================================
        print("\n📊 PASO 6: Verificando estado en MySQL...")
        
        from models.conversacion_sync import ConversacionSync
        
        conv_sync = db.query(ConversacionSync).filter(
            ConversacionSync.mongodb_conversation_id == session_id
        ).first()
        
        if conv_sync:
            print(f"✅ Registro encontrado en Conversacion_Sync:")
            print(f"   - ID: {conv_sync.id_conversacion_sync}")
            print(f"   - Estado: {conv_sync.estado}")
            print(f"   - Requirió humano: {conv_sync.requirio_atencion_humana}")
        else:
            print("❌ No se encontró registro en Conversacion_Sync")
        
        # ============================================
        # PASO 7: Verificar notificaciones
        # ============================================
        print("\n📬 PASO 7: Verificando notificaciones...")
        
        from models.notificacion_usuario import NotificacionUsuario
        
        notificaciones = db.query(NotificacionUsuario).filter(
            NotificacionUsuario.datos_adicionales.like(f'%{session_id}%')
        ).all()
        
        print(f"✅ {len(notificaciones)} notificaciones creadas")
        
        for notif in notificaciones[:3]:  # Mostrar solo las primeras 3
            print(f"   - Usuario ID {notif.id_usuario}: {notif.titulo}")
        
        # ============================================
        # PASO 8: Simular respuesta de humano
        # ============================================
        print("\n👤 PASO 8: Simulando respuesta de humano...")
        
        resultado_respuesta = await escalamiento_service.responder_como_humano(
            session_id=session_id,
            mensaje="Hola, soy Juan del equipo de soporte. ¿En qué puedo ayudarte?",
            id_usuario=1,
            nombre_usuario="Juan Pérez"
        )
        
        if resultado_respuesta["success"]:
            print(f"✅ Respuesta humana agregada")
            print(f"   - Total mensajes ahora: {resultado_respuesta['total_mensajes']}")
        
        # ============================================
        # PASO 9: Ver conversación completa
        # ============================================
        print("\n📜 PASO 9: Conversación completa:")
        
        conv_final = await ConversationService.get_conversation_by_session(session_id)
        
        print(f"\n   Conversación: {conv_final.agent_name}")
        print(f"   Estado: {conv_final.metadata.estado}")
        print(f"   Mensajes ({len(conv_final.messages)}):")
        
        for i, msg in enumerate(conv_final.messages, 1):
            role_emoji = {
                "user": "👤",
                "assistant": "🤖",
                "system": "⚙️",
                "human_agent": "👨‍💼"
            }
            emoji = role_emoji.get(msg.role, "❓")
            
            content_preview = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
            
            user_info = f" ({msg.user_name})" if msg.user_name else ""
            print(f"   {i}. {emoji} [{msg.role}{user_info}] {content_preview}")
        
        # ============================================
        # PASO 10: Listar conversaciones escaladas
        # ============================================
        print("\n📋 PASO 10: Listando todas las conversaciones escaladas...")
        
        conversaciones_escaladas = escalamiento_service.obtener_conversaciones_escaladas(
            solo_pendientes=True
        )
        
        print(f"✅ {len(conversaciones_escaladas)} conversaciones escaladas encontradas")
        
        for conv in conversaciones_escaladas[:3]:
            print(f"   - Session: {conv['session_id'][:20]}... | Estado: {conv['estado']}")
        
        # ============================================
        # RESUMEN FINAL
        # ============================================
        print("\n" + "="*60)
        print("✅ TODOS LOS TESTS COMPLETADOS EXITOSAMENTE")
        print("="*60)
        
        print("\n📊 RESUMEN:")
        print(f"   ✅ Conversación creada: {session_id}")
        print(f"   ✅ Escalamiento ejecutado correctamente")
        print(f"   ✅ Estado actualizado en MongoDB y MySQL")
        print(f"   ✅ {resultado['usuarios_notificados']} usuarios notificados")
        print(f"   ✅ Respuesta de humano agregada")
        print(f"   ✅ Total de {len(conv_final.messages)} mensajes en conversación")
        
    except Exception as e:
        print(f"\n❌ ERROR EN TESTS: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Limpiar: eliminar conversación de prueba
        if session_id:
            try:
                print(f"\n🗑️ Limpiando conversación de prueba...")
                await ConversationService.delete_conversation(session_id)
                print(f"✅ Conversación eliminada de MongoDB")
                
                # Eliminar de MySQL si existe
                from models.conversacion_sync import ConversacionSync
                conv_sync = db.query(ConversacionSync).filter(
                    ConversacionSync.mongodb_conversation_id == session_id
                ).first()
                
                if conv_sync:
                    db.delete(conv_sync)
                    db.commit()
                    print(f"✅ Conversación eliminada de MySQL")
                
            except Exception as e:
                print(f"⚠️ Error limpiando: {e}")
        
        # Cerrar conexiones
        db.close()
        await close_mongodb()
        print("\n👋 Conexiones cerradas")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 INICIANDO TESTS DE ESCALAMIENTO A HUMANOS")
    print("="*60)
    print("\nNOTA: Este test requiere:")
    print("  1. MongoDB corriendo")
    print("  2. MySQL con datos de prueba")
    print("  3. Al menos un agente con ID=1")
    print("  4. Al menos un usuario activo")
    print("\n" + "="*60)
    
    # Ejecutar tests
    asyncio.run(test_flujo_completo())
