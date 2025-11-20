# app/ollama/prompt_builder.py
from pathlib import Path

TEMPLATES_DIR = Path("templates")

def build_system_prompt(agente):
    tpl = (TEMPLATES_DIR / "system_prompt_template.txt").read_text(encoding="utf-8")
    return tpl.format(
        nombre_agente=getattr(agente, "nombre_agente", ""),
        tono=getattr(agente, "tono_respuesta", "neutral"),
        estilo=getattr(agente, "estilo_comunicacion", "claro"),
        objetivo=getattr(agente, "area_especialidad", "")
    )

def build_chat_prompt(system_prompt: str, contexto: str, pregunta: str):
    tpl = (TEMPLATES_DIR / "chat_prompt_template.txt").read_text(encoding="utf-8")
    return tpl.format(system=system_prompt, contexto=contexto, pregunta=pregunta)
