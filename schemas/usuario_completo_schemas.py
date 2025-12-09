# schemas/usuario_completo_schemas.py
from pydantic import BaseModel, Field, validator
from typing import List
from datetime import datetime

from schemas.persona_schemas import PersonaCreate, PersonaResponse
from schemas.usuario_schemas import UsuarioBase, EstadoUsuarioEnum
from schemas.usuario_rol_schemas import UsuarioRolResponse
from typing import Optional

class UsuarioCompletoCreate(BaseModel):
    """
    Schema para crear usuario completo con transacción atómica.
    Combina: Usuario + Persona + Roles
    """
    # Datos del usuario (heredados de UsuarioBase)
    username: str = Field(..., min_length=4, max_length=50, description="Nombre de usuario único")
    email: str = Field(..., description="Email del usuario")
    password: str = Field(..., min_length=8, max_length=100, description="Contraseña del usuario")
    estado: EstadoUsuarioEnum = EstadoUsuarioEnum.activo
    creado_por: Optional[int] = Field(None, description="ID del usuario que crea este registro")
    
    # Datos de la persona (embebido)
    persona: PersonaCreate = Field(..., description="Información personal del usuario")
    
    # Roles a asignar
    roles: List[int] = Field(
        ..., 
        min_items=1, 
        description="Lista de IDs de roles a asignar (mínimo 1)"
    )
    
    @validator('username')
    def validar_username(cls, v):
        if not v.strip():
            raise ValueError('El username no puede estar vacío')
        # Solo alfanuméricos, guiones y guiones bajos
        if not all(c.isalnum() or c in ['_', '-'] for c in v):
            raise ValueError('Username solo puede contener letras, números, guiones y guiones bajos')
        return v.strip().lower()
    
    @validator('password')
    def validar_password(cls, v):
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        if not any(c.isupper() for c in v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not any(c.islower() for c in v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('La contraseña debe contener al menos un número')
        # ✅ AGREGAR ESTA LÍNEA
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('La contraseña debe contener al menos un carácter especial (!@#$%^&*...)')
        return v
    
    @validator('roles')
    def validar_roles_unicos(cls, v):
        if len(v) != len(set(v)):
            raise ValueError('Los IDs de roles deben ser únicos (sin duplicados)')
        if any(rol_id <= 0 for rol_id in v):
            raise ValueError('Los IDs de roles deben ser mayores a 0')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "juan_perez",
                "email": "juan.perez@example.com",
                "password": "Secure123!",
                "estado": "activo",
                "persona": {
                    "cedula": "0102417144",
                    "nombre": "Juan",
                    "apellido": "Pérez",
                    "fecha_nacimiento": "1990-05-15",
                    "genero": "masculino",
                    "telefono": "072345678",
                    "celular": "0998765432",
                    "email_personal": "juan@personal.com",
                    "direccion": "Av. Principal 123",
                    "ciudad": "Cuenca",
                    "provincia": "Azuay",
                    "tipo_persona": "docente",
                    "id_departamento": 1,
                    "cargo": "Profesor"
                },
                "roles": [2, 3]
            }
        }

class RolAsignadoInfo(BaseModel):
    """Información de rol asignado en la respuesta"""
    id_rol: int
    nombre_rol: str
    nivel_jerarquia: int
    fecha_asignacion: datetime
    
    class Config:
        from_attributes = True

class UsuarioInfo(BaseModel):
    """Información del usuario creado"""
    id_usuario: int
    username: str
    email: str
    estado: str
    id_persona: int
    requiere_cambio_password: bool = True
    fecha_creacion: Optional[datetime] = None

class PersonaInfo(BaseModel):
    """Información de la persona creada"""
    id_persona: int
    cedula: str
    nombre: str
    apellido: str
    tipo_persona: str
    email_personal: str = None

class UsuarioCompletoResponse(BaseModel):
    """
    Schema de respuesta para usuario completo creado.
    Incluye confirmación de todas las entidades creadas.
    """
    message: str = Field(
        default="Usuario creado exitosamente",
        description="Mensaje de confirmación"
    )
    usuario: UsuarioInfo = Field(..., description="Información del usuario creado")
    persona: PersonaInfo = Field(..., description="Información de la persona creada")
    roles_asignados: List[RolAsignadoInfo] = Field(
        ..., 
        description="Lista de roles asignados al usuario"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Usuario creado exitosamente",
                "usuario": {
                    "id_usuario": 5,
                    "username": "juan_perez",
                    "email": "juan.perez@example.com",
                    "estado": "activo",
                    "id_persona": 12,
                    "requiere_cambio_password": True,
                    "fecha_creacion": "2025-12-03T15:30:00"
                },
                "persona": {
                    "id_persona": 12,
                    "cedula": "0102417144",
                    "nombre": "Juan",
                    "apellido": "Pérez",
                    "tipo_persona": "docente",
                    "email_personal": "juan@personal.com"
                },
                "roles_asignados": [
                    {
                        "id_rol": 2,
                        "nombre_rol": "Administrador",
                        "nivel_jerarquia": 2,
                        "fecha_asignacion": "2025-12-03T15:30:00"
                    },
                    {
                        "id_rol": 3,
                        "nombre_rol": "Funcionario",
                        "nivel_jerarquia": 3,
                        "fecha_asignacion": "2025-12-03T15:30:00"
                    }
                ]
            }
        }

class TransaccionErrorResponse(BaseModel):
    """Schema de respuesta en caso de error en la transacción"""
    detail: str = Field(..., description="Detalle del error")
    error_type: str = Field(
        default="validation_error",
        description="Tipo de error: validation_error, integrity_error, database_error"
    )
    rollback_applied: bool = Field(
        default=True,
        description="Indica si se aplicó rollback (siempre True en errores)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Ya existe una persona con la cédula 0102417144",
                "error_type": "validation_error",
                "rollback_applied": True
            }
        }