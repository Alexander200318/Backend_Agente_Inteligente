from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["Widget"])

# Configurar templates
templates = Jinja2Templates(directory="templates")

@router.get("/widget", response_class=HTMLResponse)
async def get_widget(request: Request):
    """Servir el widget del chat"""
    return templates.TemplateResponse("widget.html", {
        "request": request,
        "bot_name": "TecAI"
    })

@router.get("/admin", response_class=HTMLResponse)
async def get_admin(request: Request):
    """Servir el panel de administración"""
    return templates.TemplateResponse("admin.html", {
        "request": request
    })