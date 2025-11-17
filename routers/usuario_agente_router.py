from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from database.database import get_db
from services.usuario_agente_service import UsuarioAgenteService
from schemas.usuario_agente_schemas import UsuarioAgenteResponse, UsuarioAgenteCreate,UsuarioAgenteUpdate



from fastapi import APIRouter, Depends, status

router = APIRouter(prefix="/usuario-agente", tags=["Usuario-Agente"])

@router.post("/", response_model=UsuarioAgenteResponse, status_code=status.HTTP_201_CREATED)
def asignar_usuario_agente(data: UsuarioAgenteCreate, db: Session = Depends(get_db)):
    service = UsuarioAgenteService(db)
    return service.asignar_usuario_agente(data)

@router.get("/usuario/{id_usuario}", response_model=List[UsuarioAgenteResponse])
def listar_agentes_usuario(id_usuario: int, activo: Optional[bool] = None, db: Session = Depends(get_db)):
    service = UsuarioAgenteService(db)
    return service.listar_por_usuario(id_usuario, activo)

@router.get("/agente/{id_agente}", response_model=List[UsuarioAgenteResponse])
def listar_usuarios_agente(id_agente: int, activo: Optional[bool] = None, db: Session = Depends(get_db)):
    service = UsuarioAgenteService(db)
    return service.listar_por_agente(id_agente, activo)

@router.put("/{id_usuario_agente}", response_model=UsuarioAgenteResponse)
def actualizar_permisos(id_usuario_agente: int, data: UsuarioAgenteUpdate, db: Session = Depends(get_db)):
    service = UsuarioAgenteService(db)
    return service.actualizar_permisos(id_usuario_agente, data)

@router.delete("/{id_usuario_agente}", status_code=status.HTTP_200_OK)
def revocar_acceso(id_usuario_agente: int, db: Session = Depends(get_db)):
    service = UsuarioAgenteService(db)
    return service.revocar_acceso(id_usuario_agente)