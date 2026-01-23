from fastapi import APIRouter, Depends, status, Query, HTTPException
from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from database.database import get_db
from services.visitante_anonimo_service import VisitanteAnonimoService
from schemas.visitante_anonimo_schemas import VisitanteAnonimoResponse, VisitanteAnonimoCreate, VisitanteAnonimoUpdate, EmailRegistration

router = APIRouter(prefix="/visitantes", tags=["Visitantes Anónimos"])


# 🔥 NUEVO - Verificar si email existe
@router.get("/email/{email}/exists")
def verificar_email_existe(email: str, db: Session = Depends(get_db)):
    service = VisitanteAnonimoService(db)
    visitante = service.obtener_por_email(email)
    
    if visitante:
        return {
            "exists": True,
            "visitante": {
                "id_visitante": visitante.id_visitante,
                "nombre": visitante.nombre,
                "apellido": visitante.apellido,
                "email": visitante.email,
                "identificador_sesion": visitante.identificador_sesion
            }
        }
    else:
        return {
            "exists": False,
            "visitante": None
        }

# 🔥 NUEVO - Registrar visitante con email
@router.post("/register-email", response_model=VisitanteAnonimoResponse, status_code=status.HTTP_201_CREATED)
def registrar_con_email(
    data: EmailRegistration, 
    db: Session = Depends(get_db)
):
    """
    Registrar nuevo visitante con email o recuperar existente
    
    Si el email existe:
    - Asocia el nuevo session_id al visitante existente
    - Actualiza última visita
    
    Si el email NO existe:
    - Crea nuevo visitante con ese email
    """
    service = VisitanteAnonimoService(db)
    
    # Buscar por email
    visitante = service.obtener_por_email(data.email)
    
    if visitante:
        # Email existe → Actualizar session_id y última visita
        update_data = VisitanteAnonimoUpdate(
            identificador_sesion=data.session_id
        )
        visitante_actualizado = service.actualizar_visitante(visitante.id_visitante, update_data)
        service.registrar_actividad(visitante.id_visitante)
        
        return visitante_actualizado
    else:
        # Email NO existe → Crear nuevo
        nuevo_visitante_data = VisitanteAnonimoCreate(
            identificador_sesion=data.session_id,
            email=data.email,
            nombre=data.nombre,
            apellido=data.apellido,
            edad=data.edad,
            ocupacion=data.ocupacion,
            pertenece_instituto=data.pertenece_instituto,
            canal_acceso="widget"
        )
        return service.crear_visitante(nuevo_visitante_data)


@router.post("/", response_model=VisitanteAnonimoResponse, status_code=status.HTTP_201_CREATED)
def crear_visitante(visitante: VisitanteAnonimoCreate, db: Session = Depends(get_db)):
    """
    Registrar un nuevo visitante anónimo.
    Se crea cuando un usuario accede al chatbot sin autenticarse.
    """
    service = VisitanteAnonimoService(db)
    return service.crear_visitante(visitante)

@router.get("/", response_model=List[VisitanteAnonimoResponse])
def listar_visitantes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    dispositivo: Optional[str] = Query(None, pattern="^(desktop|mobile|tablet)$"),
    pais: Optional[str] = None,
    fecha_desde: Optional[datetime] = None,
    canal_acceso: Optional[str] = None,  # 🔥 NUEVO FILTRO
    pertenece_instituto: Optional[bool] = None,  # 🔥 NUEVO FILTRO
    db: Session = Depends(get_db)
):
    """Listar visitantes con filtros opcionales"""
    service = VisitanteAnonimoService(db)
    return service.listar_visitantes(
        skip, 
        limit, 
        dispositivo, 
        pais, 
        fecha_desde,
        canal_acceso,  # 🔥 NUEVO
        pertenece_instituto  # 🔥 NUEVO
    )

@router.get("/estadisticas", response_model=dict)
def obtener_estadisticas_generales(db: Session = Depends(get_db)):
    """Estadísticas generales de visitantes"""
    service = VisitanteAnonimoService(db)
    return service.obtener_estadisticas_generales()

@router.get("/activos", response_model=List[VisitanteAnonimoResponse])
def obtener_visitantes_activos(
    minutos: int = Query(30, ge=1, le=1440),
    db: Session = Depends(get_db)
):
    """Obtener visitantes activos en los últimos X minutos"""
    service = VisitanteAnonimoService(db)
    return service.obtener_visitantes_activos(minutos)

# 🔥 NUEVO ENDPOINT - Listar por canal
@router.get("/canal/{canal_acceso}", response_model=List[VisitanteAnonimoResponse])
def listar_por_canal(
    canal_acceso: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Listar visitantes por canal de acceso (widget, movil)"""
    service = VisitanteAnonimoService(db)
    return service.listar_por_canal(canal_acceso, skip, limit)

# 🔥 NUEVO ENDPOINT - Miembros del instituto
@router.get("/instituto/miembros", response_model=List[VisitanteAnonimoResponse])
def listar_miembros_instituto(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Listar visitantes que pertenecen al instituto"""
    service = VisitanteAnonimoService(db)
    return service.listar_miembros_instituto(skip, limit)

# 🔥 NUEVO ENDPOINT - Estadísticas por satisfacción
@router.get("/estadisticas/satisfaccion", response_model=dict)
def obtener_estadisticas_satisfaccion(db: Session = Depends(get_db)):
    """Obtener estadísticas de satisfacción de visitantes"""
    service = VisitanteAnonimoService(db)
    return service.obtener_estadisticas_satisfaccion()

@router.get("/sesion/{identificador_sesion}", response_model=VisitanteAnonimoResponse)
def obtener_por_sesion(identificador_sesion: str, db: Session = Depends(get_db)):
    """Obtener visitante por su identificador de sesión"""
    service = VisitanteAnonimoService(db)
    return service.obtener_por_sesion(identificador_sesion)

@router.get("/{id_visitante}", response_model=VisitanteAnonimoResponse)
def obtener_visitante(id_visitante: int, db: Session = Depends(get_db)):
    """Obtener un visitante específico"""
    service = VisitanteAnonimoService(db)
    return service.obtener_visitante(id_visitante)

@router.get("/{id_visitante}/estadisticas", response_model=dict)
def obtener_estadisticas_visitante(id_visitante: int, db: Session = Depends(get_db)):
    """Obtener estadísticas detalladas del visitante"""
    service = VisitanteAnonimoService(db)
    return service.obtener_estadisticas_visitante(id_visitante)

@router.put("/{id_visitante}", response_model=VisitanteAnonimoResponse)
def actualizar_visitante(
    id_visitante: int,
    visitante: VisitanteAnonimoUpdate,
    db: Session = Depends(get_db)
):
    """Actualizar información del visitante"""
    service = VisitanteAnonimoService(db)
    return service.actualizar_visitante(id_visitante, visitante)

# 🔥 NUEVO ENDPOINT - Actualizar satisfacción
@router.put("/{id_visitante}/satisfaccion", response_model=VisitanteAnonimoResponse)
def actualizar_satisfaccion(
    id_visitante: int,
    satisfaccion: int = Query(..., ge=1, le=5, description="Satisfacción del 1 al 5"),
    db: Session = Depends(get_db)
):
    """Actualizar satisfacción estimada del visitante (1-5 estrellas)"""
    service = VisitanteAnonimoService(db)
    return service.actualizar_satisfaccion(id_visitante, satisfaccion)

# 🔥 NUEVO ENDPOINT - Actualizar perfil
@router.put("/{id_visitante}/perfil", response_model=VisitanteAnonimoResponse)
def actualizar_perfil(
    id_visitante: int,
    nombre: Optional[str] = Query(None, max_length=100),
    apellido: Optional[str] = Query(None, max_length=100),
    edad: Optional[str] = Query(None, max_length=20),
    ocupacion: Optional[str] = Query(None, max_length=100),
    pertenece_instituto: Optional[bool] = None,
    email: Optional[str] = Query(None, max_length=150),
    db: Session = Depends(get_db)
):
    """Actualizar perfil del visitante"""
    service = VisitanteAnonimoService(db)
    return service.actualizar_perfil(
        id_visitante, 
        nombre, 
        apellido, 
        edad, 
        ocupacion, 
        pertenece_instituto,
        email
    )

@router.post("/{id_visitante}/actividad", response_model=VisitanteAnonimoResponse)
def registrar_actividad(id_visitante: int, db: Session = Depends(get_db)):
    """Registrar actividad del visitante (actualizar última visita)"""
    service = VisitanteAnonimoService(db)
    return service.registrar_actividad(id_visitante)

@router.post("/{id_visitante}/nueva-conversacion", response_model=VisitanteAnonimoResponse)
def incrementar_conversacion(id_visitante: int, db: Session = Depends(get_db)):
    """Incrementar contador de conversaciones"""
    service = VisitanteAnonimoService(db)
    return service.incrementar_conversacion(id_visitante)

@router.post("/{id_visitante}/mensajes", response_model=VisitanteAnonimoResponse)
def incrementar_mensajes(
    id_visitante: int,
    cantidad: int = Query(1, ge=1),
    db: Session = Depends(get_db)
):
    """Incrementar contador de mensajes"""
    service = VisitanteAnonimoService(db)
    return service.incrementar_mensajes(id_visitante, cantidad)