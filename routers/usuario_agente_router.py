from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from database.database import get_db
from services.usuario_agente_service import UsuarioAgenteService
from schemas.usuario_agente_schemas import UsuarioAgenteResponse, UsuarioAgenteCreate, UsuarioAgenteUpdate

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

# Verificar permisos de un usuario sobre un agente específico
@router.get("/verificar/{id_usuario}/{id_agente}", status_code=status.HTTP_200_OK)
def verificar_permisos_usuario_agente(
    id_usuario: int,
    id_agente: int,
    db: Session = Depends(get_db)
):
    """
    Verifica los permisos de un usuario sobre un agente específico.
    Retorna los permisos si existe la asignación activa, error 403 si no.
    """
    service = UsuarioAgenteService(db)
    permisos = service.verificar_permisos(id_usuario, id_agente)
    
    if not permisos:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"El usuario {id_usuario} no tiene acceso al agente {id_agente}"
        )
    
    return {
        "tiene_acceso": True,
        "id_usuario": id_usuario,
        "id_agente": id_agente,
        "permisos": {
            "puede_ver_contenido": permisos.puede_ver_contenido,
            "puede_crear_contenido": permisos.puede_crear_contenido,
            "puede_editar_contenido": permisos.puede_editar_contenido,
            "puede_eliminar_contenido": permisos.puede_eliminar_contenido,
            "puede_publicar_contenido": permisos.puede_publicar_contenido,
            "puede_ver_metricas": permisos.puede_ver_metricas,
            "puede_exportar_datos": permisos.puede_exportar_datos,
            "puede_configurar_agente": permisos.puede_configurar_agente,
            "puede_gestionar_permisos": permisos.puede_gestionar_permisos,
            "puede_gestionar_categorias": permisos.puede_gestionar_categorias,
            "puede_gestionar_widgets": permisos.puede_gestionar_widgets
        },
        "activo": permisos.activo,
        "fecha_asignacion": permisos.fecha_asignacion.isoformat() if permisos.fecha_asignacion else None
    }

# Listar todos los agentes accesibles por un usuario
@router.get("/usuario/{id_usuario}/agentes-accesibles", status_code=status.HTTP_200_OK)
def listar_agentes_accesibles(
    id_usuario: int,
    db: Session = Depends(get_db)
):
    """
    Lista todos los IDs de agentes a los que el usuario tiene acceso activo.
    Útil para filtrar contenidos en el frontend.
    """
    service = UsuarioAgenteService(db)
    ids_agentes = service.listar_agentes_accesibles(id_usuario)
    
    return {
        "id_usuario": id_usuario,
        "agentes_accesibles": ids_agentes,
        "total_agentes": len(ids_agentes)
    }

# Obtener permisos de un usuario para un agente específico
@router.get("/usuario/{id_usuario}/agente/{id_agente}", response_model=UsuarioAgenteResponse)
def obtener_permisos_usuario_agente(
    id_usuario: int,
    id_agente: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene los permisos de un usuario sobre un agente específico.
    Retorna la asignación completa con todos los permisos.
    """
    service = UsuarioAgenteService(db)
    asignacion = service.obtener_por_usuario_agente(id_usuario, id_agente)
    
    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró asignación para usuario {id_usuario} y agente {id_agente}"
        )
    
    return asignacion


# Actualizar permisos de un usuario para un agente específico
@router.put("/usuario/{id_usuario}/agente/{id_agente}", response_model=UsuarioAgenteResponse)
def actualizar_permisos_usuario_agente(
    id_usuario: int,
    id_agente: int,
    data: UsuarioAgenteUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualiza los permisos de un usuario sobre un agente específico.
    Permite modificar permisos individuales sin conocer el id_usuario_agente.
    """
    service = UsuarioAgenteService(db)
    asignacion_actualizada = service.actualizar_por_usuario_agente(id_usuario, id_agente, data)
    
    if not asignacion_actualizada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró asignación para usuario {id_usuario} y agente {id_agente}"
        )
    
    return asignacion_actualizada


# Eliminar permanentemente una asignación
@router.delete("/usuario/{id_usuario}/agente/{id_agente}", status_code=status.HTTP_200_OK)
def eliminar_asignacion_usuario_agente(
    id_usuario: int,
    id_agente: int,
    db: Session = Depends(get_db)
):
    """
    Elimina PERMANENTEMENTE la asignación de un usuario a un agente.
    Esta acción borra el registro de la base de datos y NO se puede deshacer.
    
    Diferencia con revocar_acceso:
    - revocar_acceso: Desactiva (activo=False) pero mantiene el registro
    - eliminar: Borra completamente el registro de la base de datos
    """
    service = UsuarioAgenteService(db)
    resultado = service.eliminar_asignacion(id_usuario, id_agente)
    
    return {
        "success": True,
        "message": f"Asignación eliminada: Usuario {id_usuario} - Agente {id_agente}",
        "data": resultado
    }