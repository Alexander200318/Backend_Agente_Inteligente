# app/routers/agentes_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.database import get_db
from services.agent_classifier import AgentClassifier
from rag.rag_service import RAGService
from groq_service.groq_agent_service import GroqAgentService
from models.agente_virtual import AgenteVirtual

router = APIRouter(prefix="/agentes", tags=["Agentes"])

@router.post("/{id_agente}/reindex", status_code=status.HTTP_200_OK)
async def reindex_agent(id_agente: int, db: Session = Depends(get_db)):
    rag = RAGService(db)
    res = rag.reindex_agent(id_agente)
    return res

@router.post("/{id_agente}/build_model", status_code=status.HTTP_200_OK)
async def build_agent_model(id_agente: int, db: Session = Depends(get_db)):
    service = GroqAgentService(db)
    try:
        result = service.crear_o_actualizar_modelo(id_agente)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rebuild_agents_index", status_code=status.HTTP_200_OK)
async def rebuild_agents_index(db: Session = Depends(get_db)):
    classifier = AgentClassifier(db)
    return classifier.build_index()

# 🔥 CRÍTICO: Ruta GET "/" para listar agentes (ARREGLADO 30-Jan-2026)
@router.get("/", status_code=status.HTTP_200_OK)
async def listar_agentes(
    skip: int = 0, 
    limit: int = 1000, 
    db: Session = Depends(get_db)
):
    """Obtiene lista de todos los agentes disponibles con toda su configuración"""
    try:
        agentes = db.query(AgenteVirtual).filter(
            AgenteVirtual.activo == True
        ).offset(skip).limit(limit).all()
        
        return {
            "ok": True,
            "total": len(agentes),
            "agentes": [
                {
                    "id_agente": a.id_agente,
                    "nombre_agente": a.nombre_agente,
                    "descripcion": a.descripcion,
                    "activo": a.activo,
                    "tipo_agente": a.tipo_agente,
                    "area_especialidad": a.area_especialidad,
                    "icono": a.icono,
                    # 🔥 NUEVO: Configuración del agente
                    "temperatura": a.temperatura,
                    "max_tokens": a.max_tokens,
                    "prompt_tono": a.prompt_tono,
                    "prompt_reglas": a.prompt_reglas,
                    # 🔥 NUEVO: Mensajes personalizados
                    "mensaje_bienvenida": a.mensaje_bienvenida,
                    "mensaje_despedida": a.mensaje_despedida,
                    "mensaje_derivacion": a.mensaje_derivacion
                }
                for a in agentes
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listando agentes: {str(e)}")

# 🔥 CORREGIDO: Quitar /agentes/ del path
@router.get("/{id_agente}/welcome", status_code=status.HTTP_200_OK)
async def get_agent_welcome(id_agente: int, db: Session = Depends(get_db)):
    """Obtiene mensaje de bienvenida de un agente"""
    agente = db.query(AgenteVirtual).filter(
        AgenteVirtual.id_agente == id_agente
    ).first()
    
    if not agente:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    
    mensaje = agente.mensaje_bienvenida or f"Hola, soy {agente.nombre_agente}. ¿En qué puedo ayudarte?"
    
    return {
        "ok": True,
        "mensaje_bienvenida": mensaje,
        "agente_id": id_agente,
        "agente_nombre": agente.nombre_agente
    }

# Agregar en routes/agentes_router.py

@router.post("/reindex-all", status_code=status.HTTP_200_OK)
async def reindex_all_agents(db: Session = Depends(get_db)):
    """
    Re-indexa TODOS los agentes del sistema
    Útil después de actualizar la estructura de metadata
    """
    from models.agente_virtual import AgenteVirtual
    
    agentes = db.query(AgenteVirtual).filter(
        AgenteVirtual.activo == True
    ).all()
    
    rag = RAGService(db)
    resultados = []
    
    for agente in agentes:
        try:
            resultado = rag.reindex_agent(agente.id_agente)
            resultados.append({
                "id_agente": agente.id_agente,
                "nombre": agente.nombre_agente,
                "status": "✅ OK",
                "total_docs": resultado.get("total_docs", 0)
            })
        except Exception as e:
            resultados.append({
                "id_agente": agente.id_agente,
                "nombre": agente.nombre_agente,
                "status": "❌ ERROR",
                "error": str(e)
            })
    
    return {
        "ok": True,
        "total_agentes": len(agentes),
        "resultados": resultados
    }