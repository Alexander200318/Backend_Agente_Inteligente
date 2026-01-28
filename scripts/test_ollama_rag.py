# scripts/test_ollama_rag.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.database import SessionLocal
from groq_service.groq_agent_service import GroqAgentService

def test_full_system():
    print("=" * 60)
    print("🧪 PRUEBA COMPLETA: RAG + Groq")
    print("=" * 60)
    
    db = SessionLocal()
    service = GroqAgentService(db)
    
    # Configuración
    id_agente = 3 
    pregunta = "contacto tics"
    
    print(f"\n📝 Pregunta: {pregunta}")
    print(f"🤖 Agente: {id_agente}")
    print(f"\n{'='*60}\n")
    
    try:
        # Ejecutar chat
        resultado = service.chat_with_agent(
            id_agente=id_agente,
            pregunta=pregunta,
            k=3,
            use_reranking=True
        )
        
        # Mostrar resultados
        print(f"✅ Estado: {'OK' if resultado['ok'] else 'Error'}")
        print(f"🤖 Agente: {resultado.get('agent_name')}")
        print(f"📊 Fuentes usadas: {resultado.get('sources_used')}")
        print(f"🔧 Modelo: {resultado.get('model_used')}")
        
        print(f"\n📄 Contexto usado (preview):")
        print(f"{resultado.get('context_preview', 'N/A')}")
        
        print(f"\n💬 Respuesta del agente:")
        print("=" * 60)
        print(resultado.get('response', 'Sin respuesta'))
        print("=" * 60)
        
        print("\n🎉 ¡Sistema funcionando correctamente!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Verifica:")
        print("   1. Groq API key está configurada: .env")
        print("   2. Tienes contenido indexado para el agente 3")
        print("   3. MongoDB está activo")
    
    finally:
        db.close()

if __name__ == "__main__":
    test_full_system()