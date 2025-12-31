# routers/widget_router.py
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database.database import get_db
from models.widget_config import WidgetConfig
from typing import Optional

router = APIRouter(tags=["Widget"])

templates = Jinja2Templates(directory="templates")

# 🔥 Ruta GENÉRICA (sin ID) - Para uso simple
@router.get("/widget", response_class=HTMLResponse)
async def get_widget_generic(request: Request):
    """Servir el widget genérico del chat"""
    return templates.TemplateResponse("widget.html", {
        "request": request,
        "bot_name": "TecAI",
        "widget_id": None,
        "agent_id": None
    })

# 🔥 Ruta ESPECÍFICA (con ID) - Para widgets personalizados
@router.get("/widget/{id_widget}", response_class=HTMLResponse)
async def get_widget_specific(request: Request, id_widget: int, db: Session = Depends(get_db)):
    """Servir widget específico desde BD"""
    widget_config = db.query(WidgetConfig).filter(
        WidgetConfig.id_widget == id_widget,
        WidgetConfig.activo == True
    ).first()
    
    if not widget_config:
        raise HTTPException(404, "Widget no encontrado")
    
    return templates.TemplateResponse("widget.html", {
        "request": request,
        "widget_id": id_widget,
        "bot_name": widget_config.nombre_widget,
        "agent_id": widget_config.id_agente
    })

@router.get("/admin", response_class=HTMLResponse)
async def get_admin(request: Request):
    """Servir el panel de administración"""
    return templates.TemplateResponse("admin.html", {
        "request": request
    })