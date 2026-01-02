from fastapi import HTTPException, status, Response, Depends 
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session 

from core.security import decode_access_token, should_renew_token, create_sliding_token
from database.database import get_db  
from models.usuario import Usuario  

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    response: Response = None,  
    db: Session = Depends(get_db)
) -> Usuario:
    """
    🔒 Dependencia para obtener usuario autenticado con sliding expiration.
    Si el token está por expirar, lo renueva automáticamente.
    """
    
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    id_usuario = payload.get("sub")
    if not id_usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido: sin identificador de usuario"
        )
    
    usuario = db.query(Usuario).filter(
        Usuario.id_usuario == int(id_usuario)
    ).first()
    
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    if usuario.estado != "activo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
    
    # 🔥 SLIDING EXPIRATION: Renovar token si está por expirar
    if should_renew_token(payload) and response:
        try:
            # Crear nuevo token manteniendo el iat original
            new_token = create_sliding_token(
                data={"sub": str(usuario.id_usuario)},
                original_iat=payload.get("iat")
            )
            
            # Enviar nuevo token en header de respuesta
            response.headers["X-New-Token"] = new_token
            print(f"🔄 Token renovado para usuario {usuario.username}")
        except HTTPException:
            # Si falló la renovación (ej: excedió vida máxima), dejar que expire
            pass
    
    return usuario