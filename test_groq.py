#!/usr/bin/env python3
"""
Script de prueba rápida de Groq API
Ejecutar con: python test_groq.py
"""

import os
import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
sys.path.insert(0, str(Path(__file__).parent))

def test_groq_connection():
    """Prueba la conexión con Groq"""
    print("\n" + "="*60)
    print("🧪 PRUEBA DE GROQ API")
    print("="*60 + "\n")
    
    # 1. Cargar variables de entorno
    print("📋 Paso 1: Cargando variables de entorno...")
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ Error: GROQ_API_KEY no está configurada en .env")
        return False
    
    print(f"✅ API key encontrada: {api_key[:10]}...{api_key[-5:]}")
    
    # 2. Importar cliente directamente de groq (sin settings)
    print("\n📋 Paso 2: Importando cliente de Groq...")
    try:
        from groq import Groq
        print("✅ Cliente de Groq importado correctamente")
    except Exception as e:
        print(f"❌ Error al importar: {e}")
        return False
    
    # 3. Inicializar cliente
    print("\n📋 Paso 3: Inicializando cliente...")
    try:
        client = Groq(api_key=api_key)
        print("✅ Cliente inicializado")
        print(f"   API configurada correctamente")
    except Exception as e:
        print(f"❌ Error al inicializar: {e}")
        return False
    
    # 4. Listar modelos
    print("\n📋 Paso 4: Listando modelos disponibles...")
    try:
        models = client.models.list()
        model_list = [m.id for m in models.data]
        print(f"✅ {len(model_list)} modelos disponibles:")
        for model in model_list:
            print(f"   - {model}")
    except Exception as e:
        print(f"❌ Error al listar modelos: {e}")
    
    # 5. Chat simple
    print("\n📋 Paso 5: Realizando chat simple...")
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "user", "content": "Di 'Hola' si me escuchas"}
            ],
            max_tokens=100
        )
        
        print("✅ Respuesta recibida:")
        print(f"   Contenido: {response.choices[0].message.content}")
        print(f"   Modelo: {response.model}")
        print(f"   Tokens usados: {response.usage.total_tokens}")
    except Exception as e:
        print(f"❌ Error en chat: {e}")
        return False
    
    # 6. Streaming
    print("\n📋 Paso 6: Probando streaming...")
    try:
        print("   Respuesta (streaming): ", end="", flush=True)
        
        with client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "user", "content": "Cuéntame algo breve sobre IA"}
            ],
            max_tokens=200,
            stream=True
        ) as response:
            for chunk in response:
                if chunk.choices[0].delta.content:
                    print(chunk.choices[0].delta.content, end="", flush=True)
        
        print("\n✅ Streaming completado")
    except Exception as e:
        print(f"❌ Error en streaming: {e}")
        return False
    
    print("\n" + "="*60)
    print("✅ TODAS LAS PRUEBAS EXITOSAS")
    print("="*60 + "\n")
    
    return True


def test_service():
    """Prueba el servicio de Groq"""
    print("\n" + "="*60)
    print("🧪 PRUEBA DE GROQ SERVICE")
    print("="*60 + "\n")
    
    # Necesitamos una sesión de DB para esto
    print("📋 Inicializando servicio...")
    try:
        from database.database import SessionLocal
        from groq_service.groq_agent_service import GroqAgentService
        
        db = SessionLocal()
        service = GroqAgentService(db)
        
        print("✅ Servicio inicializado")
        
        # Test de conexión
        print("\n📋 Probando conexión...")
        result = service.test_connection()
        
        print(f"✅ Estado: {result['estado']}")
        if 'respuesta' in result:
            print(f"   Respuesta: {result['respuesta']}")
        if 'error' in result:
            print(f"   Error: {result['error']}")
        
        db.close()
        
    except Exception as e:
        print(f"⚠️ No se pudo probar el servicio (DB puede no estar disponible)")
        print(f"   Error: {e}")
        return False
    
    print("\n" + "="*60)
    print("✅ PRUEBA DE SERVICIO COMPLETADA")
    print("="*60 + "\n")
    
    return True


if __name__ == "__main__":
    success = test_groq_connection()
    
    if success:
        print("\n🎉 ¡Groq está configurado correctamente!")
        print("\nPróximos pasos:")
        print("1. Ejecutar: python main.py")
        print("2. Acceder a: http://localhost:8000/docs")
        print("3. Probar endpoints:")
        print("   - GET /api/v1/groq/test")
        print("   - POST /api/v1/groq/chat")
        print("   - WS /api/v1/groq/chat/stream/{session_id}/{agente_id}")
    else:
        print("\n❌ Hay problemas con la configuración de Groq")
        sys.exit(1)
