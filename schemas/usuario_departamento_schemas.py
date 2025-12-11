# schemas/usuario_departamento_schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class CambiarDepartamentoRequest(BaseModel):
    """Schema para cambiar departamento de un usuario"""
    id_departamento: Optional[int] = Field(
        None, 
        description="ID del departamento. Usar null para remover departamento"
    )
    motivo: Optional[str] = Field(
        None, 
        max_length=500,
        description="Motivo del cambio de departamento"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "id_departamento": 3,
                "motivo": "Transferencia por reorganización administrativa"
            }
        }

class CambiarDepartamentoResponse(BaseModel):
    """Respuesta al cambiar departamento"""
    message: str
    usuario: dict
    departamento_anterior: Optional[dict] = None
    departamento_nuevo: Optional[dict] = None
    fecha_cambio: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Departamento actualizado exitosamente",
                "usuario": {
                    "id_usuario": 5,
                    "username": "juan_perez",
                    "persona": {
                        "id_persona": 12,
                        "nombre": "Juan",
                        "apellido": "Pérez"
                    }
                },
                "departamento_anterior": {
                    "id_departamento": 1,
                    "nombre": "Sistemas",
                    "codigo": "SIS"
                },
                "departamento_nuevo": {
                    "id_departamento": 3,
                    "nombre": "Recursos Humanos",
                    "codigo": "RRHH"
                },
                "fecha_cambio": "2025-12-10T15:30:00"
            }
        }