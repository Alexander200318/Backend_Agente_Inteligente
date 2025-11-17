from fastapi import APIRouter, Depends, status, Query

from fastapi import APIRouter, Depends

from fastapi import APIRouter, Depends, status, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from database.database import get_db
from services.rol_service import RolService
from schemas.rol_schemas import RolResponse, RolCreate,RolUpdate




router = APIRouter(prefix="/roles", tags=["Roles"])

@router.post("/", response_model=RolResponse, status_code=status.HTTP_201_CREATED)
def crear_rol(rol: RolCreate, db: Session = Depends(get_db)):
    service = RolService(db)
    return service.crear_rol(rol)

@router.get("/", response_model=List[RolResponse])
def listar_roles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    activo: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    service = RolService(db)
    return service.listar_roles(skip, limit, activo)

@router.get("/estadisticas", response_model=dict)
def obtener_estadisticas(db: Session = Depends(get_db)):
    service = RolService(db)
    return service.obtener_estadisticas()

@router.get("/{id_rol}", response_model=RolResponse)
def obtener_rol(id_rol: int, db: Session = Depends(get_db)):
    service = RolService(db)
    return service.obtener_rol(id_rol)

@router.put("/{id_rol}", response_model=RolResponse)
def actualizar_rol(id_rol: int, rol: RolUpdate, db: Session = Depends(get_db)):
    service = RolService(db)
    return service.actualizar_rol(id_rol, rol)

@router.delete("/{id_rol}", status_code=status.HTTP_200_OK)
def eliminar_rol(id_rol: int, db: Session = Depends(get_db)):
    service = RolService(db)
    return service.eliminar_rol(id_rol)