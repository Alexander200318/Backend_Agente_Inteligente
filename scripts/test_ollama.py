# scripts/test_ollama.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ollama.ollama_client import OllamaClient

def test_ollama():
    print("🧪 Probando conexión a Ollama...\n")
    
    client = OllamaClient()
    
    # 1. Listar modelos
    try:
        print("📋 Modelos disponibles:")
        models = client.list_models()
        
        if not models:
            print("❌ No hay modelos instalados")
            print("\n💡 Instala un modelo:")
            print("   ollama pull llama3")
            print("   ollama pull mistral")
            return
        
        for m in models:
            print(f"  ✅ {m.get('name')}")
        
        # 2. Probar generación
        print("\n🤖 Probando generación de texto...")
        model_name = models[0].get('name')
        
        response = client.generate(
            model_name=model_name,
            prompt="Di 'Hola, estoy funcionando correctamente' en una sola línea",
            temperature=0.3,
            max_tokens=50
        )
        
        print(f"\n✅ Respuesta de {model_name}:")
        print(f"   {response.get('response', 'Sin respuesta')}")
        
        print("\n🎉 Ollama funciona correctamente!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Soluciones:")
        print("   1. Inicia Ollama: ollama serve")
        print("   2. Verifica que esté en http://localhost:11434")
        print("   3. Instala un modelo: ollama pull llama3")

if __name__ == "__main__":
    test_ollama()