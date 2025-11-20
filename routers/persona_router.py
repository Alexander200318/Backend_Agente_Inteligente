from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database.database import get_db
from services.persona_service import PersonaService
from schemas.persona_schemas import (
    PersonaResponse, 
    PersonaCreate, 
    PersonaUpdate,
    TipoPersonaEnum,
    EstadoPersonaEnum
)

router = APIRouter(prefix="/personas", tags=["Personas"])


# =======================
#   1) CREAR
# =======================
@router.post("/", response_model=PersonaResponse, status_code=status.HTTP_201_CREATED)
def crear_persona(persona: PersonaCreate, db: Session = Depends(get_db)):
    service = PersonaService(db)
    return service.crear_persona(persona)


# =======================
#   2) LISTAR
# =======================
@router.get("/", response_model=List[PersonaResponse])
def listar_personas(
    skip: int = Query(0),
    limit: int = Query(100),
    tipo_persona: Optional[TipoPersonaEnum] = None,
    estado: Optional[EstadoPersonaEnum] = None,
    id_departamento: Optional[int] = None,
    busqueda: Optional[str] = None,
    db: Session = Depends(get_db),
):
    service = PersonaService(db)
    return service.listar_personas(
        skip=skip,
        limit=limit,
        tipo_persona=tipo_persona,
        estado=estado,
        id_departamento=id_departamento,
        busqueda=busqueda
    )


# =======================
#   3) ESTADÍSTICAS
# =======================
@router.get("/estadisticas", response_model=dict)
def obtener_estadisticas(db: Session = Depends(get_db)):
    service = PersonaService(db)
    return service.obtener_estadisticas()


# =======================
#   4) RUTAS ESPECÍFICAS
# =======================
@router.get("/cedula/{cedula}", response_model=PersonaResponse)
def buscar_por_cedula(cedula: str, db: Session = Depends(get_db)):
    service = PersonaService(db)
    return service.buscar_por_cedula(cedula)


@router.get("/validar-cedula/{cedula}", response_model=dict)
def validar_disponibilidad_cedula(
    cedula: str,
    exclude_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    service = PersonaService(db)
    return service.validar_disponibilidad_cedula(cedula, exclude_id)


@router.get("/buscar/nombre", response_model=List[PersonaResponse])
def buscar_por_nombre(
    q: str = Query(...),
    limit: int = Query(20),
    db: Session = Depends(get_db),
):
    service = PersonaService(db)
    return service.buscar_por_nombre(q, limit)


# =======================
#   5) ESTA DEBE IR SIEMPRE AL FINAL
# =======================
@router.get("/{id_persona}", response_model=PersonaResponse)
def obtener_persona(id_persona: int, db: Session = Depends(get_db)):
    service = PersonaService(db)
    return service.obtener_persona(id_persona)


# =======================
#   6) ACTUALIZAR
# =======================
@router.put("/{id_persona}", response_model=PersonaResponse)
def actualizar_persona(id_persona: int, persona: PersonaUpdate, db: Session = Depends(get_db)):
    service = PersonaService(db)
    return service.actualizar_persona(id_persona, persona)


@router.patch("/{id_persona}/estado", response_model=PersonaResponse)
def cambiar_estado_persona(id_persona: int, estado: EstadoPersonaEnum, db: Session = Depends(get_db)):
    service = PersonaService(db)
    return service.cambiar_estado(id_persona, estado)


# =======================
#   7) ELIMINAR
# =======================
@router.delete("/{id_persona}", status_code=status.HTTP_200_OK)
def eliminar_persona(id_persona: int, db: Session = Depends(get_db)):
    service = PersonaService(db)
    return service.eliminar_persona(id_persona)
