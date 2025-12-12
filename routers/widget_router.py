# routers/widget_router.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os

# Router SIN prefijo para que sea /widget directo
router = APIRouter(tags=["Widget"])


@router.get("/widget")
async def get_widget():
    """
    Sirve el archivo widget.html desde la carpeta static/
    Accesible en: http://localhost:8000/widget
    """
    try:
        # Obtener la ruta del proyecto (un nivel arriba de routers/)
        current_file = os.path.abspath(__file__)
        routers_dir = os.path.dirname(current_file)
        project_root = os.path.dirname(routers_dir)
        widget_path = os.path.join(project_root, "static", "widget.html")
        
        print(f"🔍 Buscando widget en: {widget_path}")
        print(f"📂 ¿Existe? {os.path.exists(widget_path)}")
        
        # Verificar si el archivo existe
        if not os.path.exists(widget_path):
            # Listar archivos en static para debug
            static_dir = os.path.join(project_root, "static")
            if os.path.exists(static_dir):
                files = os.listdir(static_dir)
                print(f"📁 Archivos en static/: {files}")
            else:
                print(f"❌ La carpeta static/ no existe en: {static_dir}")
            
            raise HTTPException(
                status_code=404, 
                detail=f"Widget no encontrado. Buscando en: {widget_path}"
            )
        
        return FileResponse(
            widget_path,
            media_type="text/html",
            headers={
                "Cache-Control": "no-cache",
                "Access-Control-Allow-Origin": "*"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error cargando widget: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error al cargar widget: {str(e)}"
        )


@router.get("/")
async def root():
    """
    Página de inicio con información de la API
    """
    return {
        "message": "API RAG Ollama",
        "version": "1.0.0",
        "endpoints": {
            "widget": "/widget",
            "chat_agent": "/api/v1/chat/agent",
            "chat_stream": "/api/v1/chat/agent/stream",
            "chat_auto": "/api/v1/chat/auto/stream",
            "models": "/api/v1/chat/models",
            "docs": "/docs"
        }
    }