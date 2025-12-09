# routers/aseguramiento_router.py
from fastapi import APIRouter, HTTPException
import httpx

from core.config import settings

router = APIRouter(
    prefix="/cedulas",
    tags=["Aseguramiento / Fenix"]
)

@router.get("/{cedula}")
async def consultar_cedula(cedula: str):
    """
    Proxy hacia el servicio de aseguramiento / Fenix.
    El frontend debe llamar a ESTE endpoint, NO directo al servidor externo.
    """
    url = f"{settings.ASEGURAMIENTO_BASE_URL}/cedula/{cedula}"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)

        # Si el servidor externo responde error, lo propagamos
        if resp.status_code != 200:
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"Error consultando Fenix: {resp.text}"
            )

        return resp.json()

    except HTTPException:
        # Re-lanzamos HTTPException para que FastAPI la maneje
        raise
    except Exception as e:
        # Error de red, timeout, etc.
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al consultar Fenix: {str(e)}"
        )
