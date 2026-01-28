"""
Ejemplos de uso de la API de Groq desde clientes Python y JavaScript
"""

# ============================================================
# EJEMPLO 1: CHAT SIMPLE CON PYTHON (requests)
# ============================================================

import requests
import json

def chat_groq_python():
    """Ejemplo de chat simple con Groq desde Python"""
    
    url = "http://localhost:8000/api/v1/groq/chat"
    
    payload = {
        "id_agente": 1,
        "mensaje": "¿Cuál es el significado de la vida?",
        "session_id": "user-123",
        "origin": "web",
        "temperatura": 0.7,
        "max_tokens": 2000,
        "k": 3,
        "use_reranking": False
    }
    
    response = requests.post(url, json=payload)
    data = response.json()
    
    print(f"Respuesta: {data['respuesta']}")
    print(f"Tokens usados: {data['tokens_usados']}")
    print(f"Documentos: {data['documentos_recuperados']}")


# ============================================================
# EJEMPLO 2: STREAMING CON PYTHON (websocket-client)
# ============================================================

import websocket
import json

def chat_groq_streaming_python():
    """Ejemplo de chat con streaming desde Python"""
    
    def on_message(ws, message):
        data = json.loads(message)
        
        if data['tipo'] == 'chunk':
            print(data['contenido'], end='', flush=True)
        elif data['tipo'] == 'fin':
            print(f"\n[{data['mensaje']}]")
        elif data['tipo'] == 'error':
            print(f"Error: {data['error']}")
    
    def on_error(ws, error):
        print(f"Error: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        print("Conexión cerrada")
    
    def on_open(ws):
        message = {
            "mensaje": "¿Cuál es el significado de la vida?",
            "origen": "web",
            "temperatura": 0.7,
            "max_tokens": 2000
        }
        ws.send(json.dumps(message))
    
    ws = websocket.WebSocketApp(
        "ws://localhost:8000/api/v1/groq/chat/stream/user-123/1",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    ws.run_forever()


# ============================================================
# EJEMPLO 3: CHAT SIMPLE CON JAVASCRIPT/FETCH
# ============================================================

javascript_chat_simple = """
async function chatGroqSimple() {
  const response = await fetch('http://localhost:8000/api/v1/groq/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      id_agente: 1,
      mensaje: "¿Cuál es el significado de la vida?",
      session_id: "user-123",
      origin: "web",
      temperatura: 0.7,
      max_tokens: 2000,
      k: 3,
      use_reranking: false
    })
  });
  
  const data = await response.json();
  
  console.log("Respuesta:", data.respuesta);
  console.log("Tokens usados:", data.tokens_usados);
  console.log("Documentos:", data.documentos_recuperados);
  
  return data;
}

// Uso
chatGroqSimple();
"""


# ============================================================
# EJEMPLO 4: STREAMING CON JAVASCRIPT/WEBSOCKET
# ============================================================

javascript_chat_streaming = """
function chatGroqStreaming() {
  const ws = new WebSocket('ws://localhost:8000/api/v1/groq/chat/stream/user-123/1');
  
  ws.onopen = (event) => {
    console.log("Conectado a Groq");
    
    const message = {
      mensaje: "¿Cuál es el significado de la vida?",
      origen: "web",
      temperatura: 0.7,
      max_tokens: 2000
    };
    
    ws.send(JSON.stringify(message));
  };
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.tipo === 'chunk') {
      // Mostrar fragmento en tiempo real
      document.getElementById('response').innerHTML += data.contenido;
    } else if (data.tipo === 'fin') {
      console.log("Respuesta completada");
    } else if (data.tipo === 'error') {
      console.error("Error:", data.error);
    }
  };
  
  ws.onerror = (error) => {
    console.error("Error en WebSocket:", error);
  };
  
  ws.onclose = (event) => {
    console.log("Conexión cerrada");
  };
}

// Uso
chatGroqStreaming();
"""


# ============================================================
# EJEMPLO 5: VERIFICAR CONEXIÓN
# ============================================================

def verify_groq_connection():
    """Verifica que Groq está disponible"""
    
    url = "http://localhost:8000/api/v1/groq/test"
    
    response = requests.get(url)
    data = response.json()
    
    if data['estado'] == 'conexión exitosa':
        print("✅ Groq está funcionando")
        print(f"Modelo: {data['modelo']}")
        print(f"Respuesta de prueba: {data['respuesta']}")
    else:
        print("❌ Error en la conexión")
        print(f"Error: {data['error']}")


# ============================================================
# EJEMPLO 6: LISTAR MODELOS DISPONIBLES
# ============================================================

def list_groq_models():
    """Lista todos los modelos disponibles en Groq"""
    
    url = "http://localhost:8000/api/v1/groq/models"
    
    response = requests.get(url)
    data = response.json()
    
    print(f"Total de modelos: {data['total']}")
    print("\nModelos disponibles:")
    
    for model in data['modelos']:
        print(f"  - {model}")


# ============================================================
# EJEMPLO 7: CLASS WRAPPER EN PYTHON
# ============================================================

class GroqChatClient:
    """Wrapper para simplificar el uso de Groq API"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def chat(self, id_agente, mensaje, session_id, **kwargs):
        """Chat simple"""
        url = f"{self.base_url}/api/v1/groq/chat"
        
        payload = {
            "id_agente": id_agente,
            "mensaje": mensaje,
            "session_id": session_id,
            **kwargs
        }
        
        response = self.session.post(url, json=payload)
        return response.json()
    
    def test_connection(self):
        """Prueba de conexión"""
        url = f"{self.base_url}/api/v1/groq/test"
        response = self.session.get(url)
        return response.json()
    
    def list_models(self):
        """Lista modelos"""
        url = f"{self.base_url}/api/v1/groq/models"
        response = self.session.get(url)
        return response.json()


# Uso del wrapper
def example_wrapper():
    client = GroqChatClient()
    
    # Prueba de conexión
    result = client.test_connection()
    print(f"Estado: {result['estado']}")
    
    # Chat
    response = client.chat(
        id_agente=1,
        mensaje="¿Quién eres?",
        session_id="user-123",
        origen="web"
    )
    print(f"Respuesta: {response['respuesta']}")
    
    # Modelos
    models = client.list_models()
    print(f"Modelos disponibles: {models['total']}")


# ============================================================
# EJEMPLO 8: USO EN CELERY TASK
# ============================================================

from celery import shared_task
import requests

@shared_task
def process_chat_groq(id_agente, mensaje, session_id):
    """Task de Celery para procesar chat con Groq"""
    
    url = "http://localhost:8000/api/v1/groq/chat"
    
    payload = {
        "id_agente": id_agente,
        "mensaje": mensaje,
        "session_id": session_id,
        "origin": "celery-task"
    }
    
    response = requests.post(url, json=payload)
    data = response.json()
    
    # Aquí se podría guardar resultado, enviar email, etc.
    return {
        "conversacion_id": data["id_conversacion"],
        "respuesta": data["respuesta"],
        "tokens": data["tokens_usados"]
    }


# ============================================================
# EJEMPLO 9: ASYNC/AWAIT CON AIOHTTP
# ============================================================

async_chat_example = """
import aiohttp
import asyncio
import json

async def chat_groq_async(mensaje):
    url = "http://localhost:8000/api/v1/groq/chat"
    
    payload = {
        "id_agente": 1,
        "mensaje": mensaje,
        "session_id": "user-123",
        "origin": "web"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            data = await response.json()
            return data

# Uso
async def main():
    resultado = await chat_groq_async("¿Hola qué tal?")
    print(resultado)

asyncio.run(main())
"""


# ============================================================
# EJEMPLO 10: CHATBOT INTERACTIVO EN TERMINAL
# ============================================================

interactive_chatbot = """
import requests

class InteractiveChatbot:
    def __init__(self, agent_id=1, session_id="default"):
        self.agent_id = agent_id
        self.session_id = session_id
        self.base_url = "http://localhost:8000/api/v1/groq"
    
    def run(self):
        print("Chatbot Groq - Escribe 'salir' para terminar")
        print("=" * 50)
        
        while True:
            user_input = input("Tú: ").strip()
            
            if user_input.lower() in ['salir', 'exit', 'quit']:
                print("¡Hasta luego!")
                break
            
            if not user_input:
                continue
            
            response = requests.post(
                f"{self.base_url}/chat",
                json={
                    "id_agente": self.agent_id,
                    "mensaje": user_input,
                    "session_id": self.session_id,
                    "origin": "terminal"
                }
            )
            
            data = response.json()
            print(f"Bot: {data['respuesta']}")
            print("-" * 50)

# Uso
if __name__ == "__main__":
    chatbot = InteractiveChatbot()
    chatbot.run()
"""


if __name__ == "__main__":
    print("Ejemplos de uso de Groq API")
    print("\nEjemplo 1: Chat simple")
    try:
        chat_groq_python()
    except Exception as e:
        print(f"Error: {e}")
    
    print("\nEjemplo 5: Verificar conexión")
    try:
        verify_groq_connection()
    except Exception as e:
        print(f"Error: {e}")
    
    print("\nEjemplo 6: Listar modelos")
    try:
        list_groq_models()
    except Exception as e:
        print(f"Error: {e}")
