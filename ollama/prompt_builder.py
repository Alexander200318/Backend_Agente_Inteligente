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
{agente.prompt_especializado or ''}

**Reglas importantes:**
- NO inventes información que no esté en el CONTEXTO proporcionado
- Si no sabes algo, dilo honestamente
- Responde de forma clara y concisa
- Si el CONTEXTO está vacío, indica que no tienes información suficiente
"""
    return prompt.strip()

def build_chat_prompt(system_prompt: str, contexto: str, pregunta: str) -> str:
    """
    Construye prompt final para el chat
    """
    # Verificar si existe el template, si no usar inline
    template_path = TEMPLATES_DIR / "chat_prompt_template.txt"
    
    if template_path.exists():
        tpl = template_path.read_text(encoding="utf-8")
        return tpl.format(
            system=system_prompt, 
            contexto=contexto, 
            pregunta=pregunta
        )
    
    # Fallback: template inline
    return f"""{system_prompt}

---

**CONTEXTO RELEVANTE:**
{contexto if contexto else "No se encontró información específica."}

---

**PREGUNTA DEL USUARIO:**
{pregunta}

---

**TU RESPUESTA:**"""