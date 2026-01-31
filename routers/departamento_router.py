from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database.database import get_db
from services.departamento_service import DepartamentoService
from schemas.departamento_schemas import (
    DepartamentoCreate,
    DepartamentoUpdate,
    DepartamentoResponse
)
from auth.dependencies import get_current_user  # 🔥 NUEVO
from models.usuario import Usuario  # 🔥 NUEVO

router = APIRouter(
    prefix="/departamentos",
    tags=["Departamentos"]
)

@router.post(
    "/",
    response_model=DepartamentoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear departamento",
    description="Crea un nuevo departamento con validaciones de negocio"
)
def crear_departamento(
    departamento: DepartamentoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)  # 🔥 NUEVO
):
    """
    Crear un nuevo departamento:
    - **nombre**: único, descriptivo (mínimo 5 caracteres)
    - **codigo**: único, sin espacios, se convierte a mayúsculas
    - **email**: formato válido
    - **telefono**: solo números
    
    🔒 Requiere autenticación
    """
    service = DepartamentoService(db)
    return service.crear_departamento(
        departamento, 
        creado_por_id=current_user.id_usuario  # 🔥 NUEVO
    )

@router.get(
    "/",
    response_model=List[DepartamentoResponse],
    summary="Listar departamentos",
    description="Obtiene listado de departamentos con filtros opcionales"
)
def listar_departamentos(
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(100, ge=1, le=500, description="Límite de registros"),
    activo: Optional[bool] = Query(None, description="Filtrar por estado"),
    facultad: Optional[str] = Query(None, description="Filtrar por facultad"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)  # 🔥 NUEVO
):
    """
    Listar departamentos:
    - Ordenados alfabéticamente por nombre
    - Con paginación
    - Filtros opcionales por estado y facultad
    
    🔒 Requiere autenticación
    """
    service = DepartamentoService(db)
    return service.listar_departamentos(skip, limit, activo, facultad)@router.get(
    "/estadisticas",
    response_model=dict,
    summary="Estadísticas generales",
    description="Obtiene contadores generales de departamentos"
)
def obtener_estadisticas_generales(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)  # 🔥 NUEVO
):
    """
    Retorna estadísticas:
    - Total de departamentos
    - Departamentos activos
    - Departamentos inactivos
    
    🔒 Requiere autenticación
    """
    service = DepartamentoService(db)
    return service.obtener_estadisticas_generales()

@router.get(
    "/buscar",
    response_model=List[DepartamentoResponse],
    summary="Buscar departamentos",
    description="Busca por nombre o código"
)
def buscar_departamentos(
    q: str = Query(..., min_length=2, description="Término de búsqueda"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)  # 🔥 NUEVO
):
    """
    Buscar departamentos por:
    - Nombre (parcial, insensible a mayúsculas)
    - Código (parcial, insensible a mayúsculas)
    
    🔒 Requiere autenticación
    """
    service = DepartamentoService(db)
    return service.buscar_departamentos(q)

@router.get(
    "/codigo/{codigo}",
    response_model=DepartamentoResponse,
    summary="Obtener por código",
    description="Obtiene un departamento por su código"
)
def obtener_por_codigo(
    codigo: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)  # 🔥 NUEVO
):
    """
    Obtener departamento por código único (ej: TI, ADM, BE)
    
    🔒 Requiere autenticación
    """
    service = DepartamentoService(db)
    return service.obtener_por_codigo(codigo)

@router.get(
    "/{id_departamento}",
    response_model=DepartamentoResponse,
    summary="Obtener departamento",
    description="Obtiene un departamento específico por ID"
)
def obtener_departamento(
    id_departamento: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener departamento por ID
    
    🔒 Requiere autenticación
    """
    service = DepartamentoService(db)
    return service.obtener_departamento(id_departamento)

@router.get(
    "/{id_departamento}/estadisticas",
    response_model=dict,
    summary="Estadísticas del departamento",
    description="Obtiene estadísticas específicas de un departamento"
)
def obtener_estadisticas_departamento(
    id_departamento: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Retorna estadísticas del departamento:
    - Total de personas asociadas
    - Total de agentes virtuales
    - Total de contenidos
    
    🔒 Requiere autenticación
    """
    service = DepartamentoService(db)
    return service.obtener_estadisticas_departamento(id_departamento)

@router.put(
    "/{id_departamento}",
    response_model=DepartamentoResponse,
    summary="Actualizar departamento",
    description="Actualiza datos de un departamento"
)
def actualizar_departamento(
    id_departamento: int,
    departamento: DepartamentoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Actualizar departamento:
    - Solo enviar los campos a modificar
    - El código se convierte automáticamente a mayúsculas
    
    🔒 Requiere autenticación
    """
    service = DepartamentoService(db)
    return service.actualizar_departamento(
        id_departamento, 
        departamento,
        actualizado_por_id=current_user.id_usuario
    )

@router.put(
    "/{id_departamento}/jefe/{id_usuario_jefe}",
    response_model=DepartamentoResponse,
    summary="Asignar jefe de departamento",
    description="Asigna un usuario como jefe del departamento"
)
def asignar_jefe_departamento(
    id_departamento: int,
    id_usuario_jefe: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Asignar jefe al departamento:
    - El usuario debe existir y estar activo
    
    🔒 Requiere autenticación
    """
    service = DepartamentoService(db)
    return service.asignar_jefe(
        id_departamento, 
        id_usuario_jefe,
        asignado_por_id=current_user.id_usuario
    )

@router.delete(
    "/{id_departamento}",
    status_code=status.HTTP_200_OK,
    summary="Desactivar departamento",
    description="Desactiva un departamento (soft delete)"
)
def eliminar_departamento(
    id_departamento: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Desactivar departamento:
    - No puede tener personas activas asociadas
    - Cambia estado a inactivo (no elimina físicamente)
    
    🔒 Requiere autenticación
    """
    service = DepartamentoService(db)
    return service.eliminar_departamento(
        id_departamento,
        eliminado_por_id=current_user.id_usuario
    )

@router.post(
    "/{id_departamento}/ollama/regenerar",
    response_model=dict,
    summary="Regenerar modelo Ollama",
    description="Regenera el modelo de Ollama con el contenido actualizado"
)
def regenerar_modelo_ollama(
    id_departamento: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Regenerar modelo de Ollama para el departamento.
    Útil después de:
    - Agregar/modificar contenidos
    - Agregar/modificar categorías
    - Cambiar información del departamento
    
    🔒 Requiere autenticación
    """
    service = DepartamentoService(db)
    return service.regenerar_modelo_ollama(id_departamento)

@router.post(
    "/ollama/consultar",
    response_model=dict,
    summary="Consultar modelo del departamento",
    description="Hacer una pregunta al modelo de IA del departamento"
)
def consultar_modelo_departamento(
    codigo_departamento: str = Query(..., description="Código del departamento (ej: TI, ADM)"),
    pregunta: str = Query(..., min_length=5, description="Pregunta para el modelo"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user) 
):
    """
    Hacer una consulta al modelo de IA del departamento.
    El modelo responderá basándose en el contenido configurado.
    
    🔒 Requiere autenticación
    """
    service = DepartamentoService(db)
    respuesta = service.consultar_modelo_departamento(codigo_departamento, pregunta)
    
    return {
        "departamento": codigo_departamento,
        "pregunta": pregunta,
        "respuesta": respuesta
    }
@router.put(
    "/{id_departamento}/restaurar",
    response_model=DepartamentoResponse,
    summary="Restaurar departamento",
    description="Reactiva un departamento previamente desactivado"
)
def restaurar_departamento(
    id_departamento: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Restaurar departamento:
    - Cambia activo de False a True
    - Valida que no exista conflicto con otro departamento activo
    
    🔒 Requiere autenticación
    """
    service = DepartamentoService(db)
    return service.restaurar_departamento(
        id_departamento,
        restaurado_por_id=current_user.id_usuario
    )