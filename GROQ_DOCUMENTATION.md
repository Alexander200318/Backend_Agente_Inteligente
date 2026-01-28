# 📚 Integración Groq - Documentación

## ✅ Instalación Completada

Se ha integrado exitosamente **Groq API** en el backend. A continuación se detalla toda la configuración y los endpoints disponibles.

---

## 🔧 Configuración

### Archivos Modificados/Creados:

1. **`.env`** - Variables de entorno
   ```
   GROQ_API_KEY=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
   GROQ_MODEL=llama-3.1-8b-instant
   GROQ_TIMEOUT=30
   GROQ_MAX_TOKENS=2000
   GROQ_TEMPERATURE=0.7
   ```

2. **`core/config.py`** - Configuración centralizada
   - Añadidas variables GROQ_* a Settings

3. **`groq/groq_client.py`** - Cliente de Groq
   - Clase `GroqClient` para interactuar con API
   - Métodos: `chat_completion()`, `streaming_chat()`, `list_available_models()`

4. **`groq/groq_agent_service.py`** - Servicio de agentes
   - Clase `GroqAgentService` para chatear con agentes virtuales
   - Integración con RAG (Retrieval-Augmented Generation)
   - Métodos: `chat_with_agent()`, `chat_with_agent_streaming()`, `test_connection()`

5. **`routers/groq_router.py`** - Endpoints REST
   - Endpoints para chat, streaming, verificación y modelos

6. **`main.py`** - Integración en aplicación principal
   - Router importado e incluido en FastAPI

---

## 📡 Endpoints Disponibles

### 1. **Chat Simple (Sin Streaming)**
```
POST /api/v1/groq/chat
```

**Request:**
```json
{
  "id_agente": 1,
  "mensaje": "¿Cuál es tu nombre?",
  "session_id": "user-123",
  "origin": "web",
  "temperatura": 0.7,
  "max_tokens": 2000,
  "k": 3,
  "use_reranking": false
}
```

**Response:**
```json
{
  "id_conversacion": 45,
  "respuesta": "Soy un asistente virtual...",
  "modelo_usado": "llama-3.1-8b-instant",
  "tokens_usados": 156,
  "documentos_recuperados": 3,
  "fuente": "groq"
}
```

---

### 2. **Chat con Streaming (WebSocket)**
```
WS /api/v1/groq/chat/stream/{session_id}/{id_agente}
```

**Enviar:**
```json
{
  "mensaje": "¿Cuál es tu nombre?",
  "origen": "web",
  "temperatura": 0.7,
  "max_tokens": 2000
}
```

**Respuestas (Streaming):**
```json
{
  "tipo": "inicio",
  "mensaje": "Procesando...",
  "agente_id": 1
}

{
  "tipo": "chunk",
  "contenido": "Soy un "
}

{
  "tipo": "chunk",
  "contenido": "asistente "
}

{
  "tipo": "fin",
  "mensaje": "Respuesta completada"
}
```

---

### 3. **Prueba de Conexión**
```
GET /api/v1/groq/test
```

**Response:**
```json
{
  "estado": "conexión exitosa",
  "modelo": "llama-3.1-8b-instant",
  "respuesta": "Conexión exitosa"
}
```

---

### 4. **Listar Modelos Disponibles**
```
GET /api/v1/groq/models
```

**Response:**
```json
{
  "total": 4,
  "modelos": [
    "llama-3.1-8b-instant",
    "llama-3.1-70b-versatile",
    "mixtral-8x7b-32768",
    "gemma-7b-it"
  ],
  "estado": "éxito"
}
```

---

### 5. **Verificar API Key**
```
POST /api/v1/groq/verify-api-key
```

**Response (Válida):**
```json
{
  "valida": true,
  "modelo": "llama-3.1-8b-instant",
  "mensaje": "API key de Groq verificada correctamente"
}
```

**Response (Inválida):**
```json
{
  "valida": false,
  "error": "GROQ_API_KEY no está configurado",
  "mensaje": "Por favor, configura la variable GROQ_API_KEY en .env"
}
```

---

## 🚀 Ejemplo de Uso - cURL

### Chat Simple:
```bash
curl -X POST "http://localhost:8000/api/v1/groq/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "id_agente": 1,
    "mensaje": "¿Cuál es tu nombre?",
    "session_id": "user-123",
    "origin": "web"
  }'
```

### Prueba de Conexión:
```bash
curl -X GET "http://localhost:8000/api/v1/groq/test"
```

### Verificar API Key:
```bash
curl -X POST "http://localhost:8000/api/v1/groq/verify-api-key"
```

---

## 🐍 Ejemplo de Uso - Python

```python
import requests

# Chat simple
response = requests.post(
    "http://localhost:8000/api/v1/groq/chat",
    json={
        "id_agente": 1,
        "mensaje": "¿Cuál es tu nombre?",
        "session_id": "user-123",
        "origin": "web"
    }
)

print(response.json())

# Resultado:
# {
#   "id_conversacion": 45,
#   "respuesta": "Soy un asistente virtual...",
#   "modelo_usado": "llama-3.1-8b-instant",
#   "tokens_usados": 156,
#   "documentos_recuperados": 3,
#   "fuente": "groq"
# }
```

---

## 🔄 Flujo de Integración

```
Usuario/Cliente
    ↓
FastAPI Endpoint (/api/v1/groq/chat)
    ↓
GroqAgentService
    ├─→ Obtener Agente Virtual
    ├─→ Obtener Visitante
    ├─→ RAG Service (buscar documentos)
    ├─→ Construir Prompt
    └─→ GroqClient
        └─→ Groq API
            ├─→ Procesar solicitud
            └─→ Enviar respuesta
    ↓
Guardar en MongoDB
    ↓
Enviar respuesta al cliente
```

---

## 📊 Modelos Disponibles en Groq

| Modelo | Descripción | Tokens | Velocidad |
|--------|-------------|--------|-----------|
| `llama-3.1-8b-instant` | Modelo ligero y rápido | 128k | ⚡⚡⚡ |
| `llama-3.1-70b-versatile` | Modelo potente y versátil | 128k | ⚡⚡ |
| `mixtral-8x7b-32768` | Modelo de expertos mixtos | 32k | ⚡⚡ |
| `gemma-7b-it` | Modelo pequeño de Google | 8k | ⚡⚡⚡ |

---

## ⚙️ Configuración Recomendada

```python
# Para respuestas rápidas:
temperatura = 0.7      # Creatividad moderada
max_tokens = 1000      # Respuestas concisas

# Para respuestas más creativas:
temperatura = 0.9      # Mayor variabilidad
max_tokens = 2000      # Respuestas más largas

# Para respuestas precisas:
temperatura = 0.3      # Menos variabilidad
max_tokens = 1000      # Conciso y preciso
```

---

## 🧪 Checklist de Pruebas

- [ ] API key configurada en `.env`
- [ ] `/api/v1/groq/test` devuelve estado exitoso
- [ ] `/api/v1/groq/verify-api-key` confirma validez
- [ ] `/api/v1/groq/models` lista modelos disponibles
- [ ] `/api/v1/groq/chat` procesa solicitudes
- [ ] WebSocket `/api/v1/groq/chat/stream/...` devuelve streaming
- [ ] Conversaciones se guardan en MongoDB
- [ ] RAG se integra correctamente

---

## 🔐 Seguridad

- ✅ API key almacenada en `.env` (no en el código)
- ✅ Validación de API key al inicializar cliente
- ✅ Logs detallados para debugging
- ✅ Manejo de errores con excepciones específicas
- ✅ Rate limiting en routers

---

## 📝 Notas

1. **Streaming**: Usa WebSocket para obtener respuestas en tiempo real
2. **RAG**: Se integra automáticamente para recuperar contexto
3. **MongoDB**: Las conversaciones se guardan automáticamente
4. **Logs**: Revisa los logs para debugging: busca "Groq" o "📤/✅/❌"

---

## 🐛 Troubleshooting

**Error: `GROQ_API_KEY no está configurado`**
- Solución: Verifica que `.env` contiene `GROQ_API_KEY=...`

**Error: `Connection refused`**
- Solución: Verifica conexión a internet (Groq requiere conexión remota)

**Error: `Invalid API key`**
- Solución: Verifica que la API key sea correcta en la consola de Groq

**Streaming lento**
- Solución: Reduce `max_tokens` o usa modelo más ligero (`llama-3.1-8b-instant`)

---

## 📞 Soporte

Para más información: https://console.groq.com/keys
