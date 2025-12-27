
from fastapi import Request, HTTPException, status
from core.security import decode_access_token
from sqlalchemy.orm import Session
from database.database import get_db
from models.usuario import Usuario

async def verificar_autenticacion(request: Request, db: Session):
    """
    🔒 Middleware para verificar autenticación en rutas protegidas
    """
    # Obtener token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado"
        )
    
    token = auth_header.replace("Bearer ", "")
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado"
        )
    
    # Verificar usuario
    id_usuario = payload.get("sub")
    usuario = db.query(Usuario).filter(
        Usuario.id_usuario == int(id_usuario)
    ).first()
    
    if not usuario or usuario.estado != "activo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inválido o inactivo"
        )
    
    return usuario