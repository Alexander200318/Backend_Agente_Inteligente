# app/ollama/prompt_builder.py
from pathlib import Path
from models.agente_virtual import AgenteVirtual

# 🔥 Usar ruta absoluta
BASE_DIR = Path(__file__).parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"

def build_system_prompt(agente: AgenteVirtual) -> str:
    """
    Construye prompt del sistema usando datos reales del agente
    """
    # Opción 1: Usar prompt_sistema directamente si existe
    if agente.prompt_sistema:
        return agente.prompt_sistema
    
    # Opción 2: Construir dinámicamente
    prompt = f"""Eres {agente.nombre_agente}.

**Tu especialidad:** {agente.area_especialidad or 'Asistente general'}

**Descripción:** {agente.descripcion or 'Asistente virtual'}

**Instrucciones adicionales:**
{agente.prompt_especializado or ''}"""
    
    # 🔥 AGREGAR DESPEDIDA
    if agente.mensaje_despedida:
        prompt += f"""

**REGLA DE DESPEDIDA:**
Cuando el usuario se despida usando palabras como: "gracias", "adiós", "chao", "hasta luego", "nos vemos", "bye", "muchas gracias",
responde ÚNICAMENTE con este mensaje exacto:
"{agente.mensaje_despedida}"

NO agregues nada más después del mensaje de despedida.
"""
    
    prompt += """

**Reglas importantes:**
- Responde ÚNICAMENTE con información del CONTEXTO proporcionado
- NO uses conocimiento general que no esté en el contexto
- Si no sabes algo, dilo honestamente
- Responde de forma clara y concisa
"""
    return prompt.strip()


def build_chat_prompt(system_prompt: str, contexto: str, pregunta: str) -> str:
    """
    Construye prompt final para el chat
    🔥 MODO ESTRICTO: Solo responde con vectores asignados
    """
    
    # 🔥 VERIFICAR SI HAY CONTEXTO VÁLIDO
    tiene_contexto = (
        contexto and 
        contexto.strip() and 
        not contexto.startswith("No se encontró información") and
        not contexto.startswith("Error al buscar")
    )
    
    if not tiene_contexto:
        # 🔥 SIN CONTEXTO → Forzar mensaje de "no tengo información"
        return f"""{system_prompt}

---

⚠️ IMPORTANTE: NO hay información disponible en tu base de conocimientos para esta pregunta.

---

**PREGUNTA DEL USUARIO:**
{pregunta}

---

**INSTRUCCIÓN OBLIGATORIA:**
Debes responder EXACTAMENTE esto (sin agregar nada más):

"Lo siento, no tengo información específica sobre ese tema en mi base de conocimientos actual. 

¿Puedo ayudarte con algo relacionado a mis áreas de especialidad?"

NO uses conocimiento general.
NO inventes información.
SOLO responde el mensaje indicado.
"""
    
    # 🔥 CON CONTEXTO → Usar template normal (si existe) o fallback
    template_path = TEMPLATES_DIR / "chat_prompt_template.txt"
    
    if template_path.exists():
        tpl = template_path.read_text(encoding="utf-8")
        return tpl.format(
            system=system_prompt, 
            contexto=contexto, 
            pregunta=pregunta
        )
    
    # 🔥 Fallback: template inline ESTRICTO
    return f"""{system_prompt}

---

**CONTEXTO DISPONIBLE (TODA TU INFORMACIÓN):**
{contexto}

---

**PREGUNTA DEL USUARIO:**
{pregunta}

---

**INSTRUCCIONES CRÍTICAS:**
1. Responde ÚNICAMENTE usando información del CONTEXTO DISPONIBLE arriba
2. NO uses conocimiento general que no esté en el contexto
3. NO inventes datos
4. Si el contexto no es suficiente para responder completamente, dilo
5. Cita las fuentes cuando sea posible ("Según la información proporcionada...")

**TU RESPUESTA:**"""