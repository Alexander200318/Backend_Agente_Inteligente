# app/routers/unidad_contenido_router.py
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from database.database import get_db
from services.unidad_contenido_service import UnidadContenidoService
from schemas.unidad_contenido_schemas import UnidadContenidoResponse, UnidadContenidoCreate, UnidadContenidoUpdate
from exceptions.base import NotFoundException, ValidationException
from datetime import date
from rag.rag_service import RAGService

# 🔥 NUEVO: Importar dependencia de autenticación
from auth.dependencies import get_current_user
from models.usuario import Usuario

router = APIRouter(prefix="/contenidos", tags=["Contenidos"])

@router.post("/", response_model=UnidadContenidoResponse, status_code=201)
def crear_contenido(
    data: UnidadContenidoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)  # 🔥 Usuario autenticado
):
    """Crea un nuevo contenido"""
    return UnidadContenidoService(db).crear_contenido(data, creado_por=current_user.id_usuario)

@router.get("/agente/{id_agente}", response_model=List[UnidadContenidoResponse])
@router.get("/agente/{id_agente}/", response_model=List[UnidadContenidoResponse])  # 🔥 CON barra final también
def listar_contenidos(
    id_agente: int, 
    estado: Optional[str] = None, 
    skip: int = 0, 
    limit: int = 100,
    include_deleted: bool = Query(False, description="Incluir contenidos eliminados"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)  # 🔥 Usuario autenticado
):
    """Lista contenidos de un agente con filtros opcionales"""
    return UnidadContenidoService(db).listar_por_agente(
        id_agente, estado, skip, limit, include_deleted
    )

@router.get("/{id_contenido}", response_model=UnidadContenidoResponse)
@router.get("/{id_contenido}/", response_model=UnidadContenidoResponse)  # 🔥 CON barra final también
def obtener_contenido(
    id_contenido: int,
    include_deleted: bool = Query(False, description="Incluir si está eliminado"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)  # 🔥 Usuario autenticado
):
    """Obtiene un contenido por ID"""
    service = UnidadContenidoService(db)
    try:
        return service.obtener_por_id(id_contenido, include_deleted)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/{id_contenido}", response_model=UnidadContenidoResponse)
@router.put("/{id_contenido}/", response_model=UnidadContenidoResponse)  # 🔥 CON barra final también
def actualizar_contenido(
    id_contenido: int,
    data: UnidadContenidoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)  # 🔥 Usuario autenticado
):
    """Actualiza un contenido existente"""
    resultado = UnidadContenidoService(db).actualizar_contenido(
        id_contenido, data, actualizado_por=current_user.id_usuario
    )

    rag = RAGService(db)
    rag.clear_cache(resultado.id_agente)    
    rag.reindex_agent(resultado.id_agente)


    return resultado


@router.post("/{id_contenido}/publicar", response_model=UnidadContenidoResponse)
@router.post("/{id_contenido}/publicar/", response_model=UnidadContenidoResponse)  # 🔥 CON barra final también
def publicar_contenido(
    id_contenido: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)  # 🔥 Usuario autenticado
):
    """Publica un contenido (cambia estado a activo)"""
    resultado = UnidadContenidoService(db).publicar_contenido(
        id_contenido, publicado_por=current_user.id_usuario
    )

    rag = RAGService(db)
    rag.clear_cache(resultado.id_agente)   
    rag.reindex_agent(resultado.id_agente)

    return resultado


@router.delete("/{id_contenido}")
@router.delete("/{id_contenido}/")  # 🔥 CON barra final también
def eliminar_contenido(
    id_contenido: int,
    hard_delete: bool = Query(False, description="Si True, elimina físicamente. Si False, soft delete"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)  # 🔥 Usuario autenticado
):
    """
    Elimina un contenido:
    - Soft delete (por defecto): Marca como eliminado en BD, mantiene en ChromaDB
    - Hard delete (?hard_delete=true): Elimina de BD y ChromaDB permanentemente
    """
    service = UnidadContenidoService(db)
    
    try:
        resultado = service.eliminar_contenido(
            id_contenido,
            eliminado_por=current_user.id_usuario,  # 🔥 ID real del usuario autenticado
            hard_delete=hard_delete
        )
        if not hard_delete:
            rag = RAGService(db)
            
            rag.reindex_agent(resultado["id_agente"])
            rag.clear_cache(resultado["id_agente"])

        return resultado
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{id_contenido}/restore", response_model=UnidadContenidoResponse)
@router.post("/{id_contenido}/restore/", response_model=UnidadContenidoResponse)  # 🔥 CON barra final también
def restaurar_contenido(
    id_contenido: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)  # 🔥 Usuario autenticado
):
    """
    Restaura un contenido eliminado lógicamente
    """
    service = UnidadContenidoService(db)
    
    try:
        contenido = service.restaurar_contenido(id_contenido)

        rag = RAGService(db)
        
        rag.reindex_agent(contenido.id_agente)
        rag.clear_cache(contenido.id_agente)
        return contenido
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[UnidadContenidoResponse])
def listar_todos_contenidos(
    skip: int = 0,
    limit: int = 100,
    estado: Optional[str] = None,
    id_agente: Optional[int] = None,
    id_categoria: Optional[int] = None,
    id_departamento: Optional[int] = None,
    include_deleted: bool = Query(False, description="Incluir contenidos eliminados"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)  # 🔥 Usuario autenticado
):
    """Lista todos los contenidos con filtros opcionales"""
    return UnidadContenidoService(db).listar_todos(
        skip=skip,
        limit=limit,
        estado=estado,
        id_agente=id_agente,
        id_categoria=id_categoria,
        id_departamento=id_departamento,
        include_deleted=include_deleted
    )

@router.post("/reindex/all")
def reindexar_todo_contenido(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)  # 🔥 Usuario autenticado (solo admin)
):
    """
    Re-indexa TODOS los contenidos activos y NO eliminados en ChromaDB
    Útil después de resetear ChromaDB
    """
    from models.unidad_contenido import UnidadContenido
    from models.categoria import Categoria
    
    service = UnidadContenidoService(db)
    
    # 🔥 Obtener todos los contenidos activos y NO eliminados
    contenidos = db.query(UnidadContenido).filter(
        UnidadContenido.estado == "activo",
        UnidadContenido.eliminado == False  # Excluir eliminados
    ).all()
    
    reindexados = 0
    errores = []
    
    for contenido in contenidos:
        try:
            # Obtener categoría
            categoria = db.query(Categoria).filter(
                Categoria.id_categoria == contenido.id_categoria
            ).first()
            
            if categoria:
                service.rag.ingest_unidad(contenido, categoria)
                reindexados += 1
        except Exception as e:
            errores.append({
                "id_contenido": contenido.id_contenido,
                "error": str(e)
            })
    
    return {
        "ok": True,
        "total_contenidos": len(contenidos),
        "reindexados": reindexados,
        "errores": errores
    }

@router.get("/papelera/listar", response_model=List[UnidadContenidoResponse])
def listar_papelera(
    skip: int = 0,
    limit: int = 100,
    id_agente: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)  # 🔥 Usuario autenticado
):
    """
    Lista solo los contenidos eliminados (papelera de reciclaje)
    """
    from models.unidad_contenido import UnidadContenido
    
    query = db.query(UnidadContenido).filter(
        UnidadContenido.eliminado == True
    )
    
    if id_agente:
        query = query.filter(UnidadContenido.id_agente == id_agente)
    
    contenidos = query.order_by(
        UnidadContenido.fecha_eliminacion.desc()
    ).offset(skip).limit(limit).all()
    
    return contenidos

@router.delete("/papelera/vaciar")
def vaciar_papelera(
    id_agente: Optional[int] = Query(None, description="Si se especifica, solo vacía para ese agente"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)  # 🔥 Usuario autenticado
):
    """
    Elimina permanentemente todos los contenidos en papelera (hard delete)
    """
    from models.unidad_contenido import UnidadContenido
    
    service = UnidadContenidoService(db)
    
    # Obtener contenidos eliminados
    query = db.query(UnidadContenido).filter(
        UnidadContenido.eliminado == True
    )
    
    if id_agente:
        query = query.filter(UnidadContenido.id_agente == id_agente)
    
    contenidos = query.all()
    
    eliminados = 0
    errores = []
    
    for contenido in contenidos:
        try:
            service.eliminar_contenido(
                contenido.id_contenido,
                eliminado_por=current_user.id_usuario,  # 🔥 ID real del usuario
                hard_delete=True
            )
            eliminados += 1
        except Exception as e:
            errores.append({
                "id_contenido": contenido.id_contenido,
                "error": str(e)
            })
    
    return {
        "ok": True,
        "total_en_papelera": len(contenidos),
        "eliminados_permanentemente": eliminados,
        "errores": errores
    }

@router.post("/vigencia/actualizar-todos")
def actualizar_vigencias_masivo(
    id_agente: Optional[int] = Query(None, description="Si se especifica, solo actualiza ese agente"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    🔥 Actualiza el estado de todos los contenidos según sus fechas de vigencia
    
    Lógica automática:
    - Antes de fecha_vigencia_inicio → inactivo
    - Entre fecha_vigencia_inicio y fecha_vigencia_fin → activo
    - Después de fecha_vigencia_fin → inactivo
    """
    service = UnidadContenidoService(db)
    
    try:
        resultado = service.actualizar_vigencias_masivo(id_agente=id_agente)
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))