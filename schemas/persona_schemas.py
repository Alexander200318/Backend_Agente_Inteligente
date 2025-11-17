from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional
from datetime import date, datetime
from enum import Enum

class GeneroEnum(str, Enum):
    masculino = "masculino"
    femenino = "femenino"
    otro = "otro"
    prefiero_no_decir = "prefiero_no_decir"

class TipoPersonaEnum(str, Enum):
    docente = "docente"
    administrativo = "administrativo"
    estudiante = "estudiante"
    externo = "externo"

class EstadoPersonaEnum(str, Enum):
    activo = "activo"
    inactivo = "inactivo"
    retirado = "retirado"

class PersonaBase(BaseModel):
    cedula: str = Field(..., min_length=10, max_length=20, description="Cédula de identidad")
    nombre: str = Field(..., min_length=2, max_length=100)
    apellido: str = Field(..., min_length=2, max_length=100)
    fecha_nacimiento: Optional[date] = None
    genero: Optional[GeneroEnum] = None
    
    telefono: Optional[str] = Field(None, max_length=20)
    celular: Optional[str] = Field(None, max_length=20)
    email_personal: Optional[EmailStr] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = Field(None, max_length=100)
    provincia: Optional[str] = Field(None, max_length=100)
    
    tipo_persona: TipoPersonaEnum = TipoPersonaEnum.administrativo
    id_departamento: Optional[int] = None
    cargo: Optional[str] = Field(None, max_length=100)
    fecha_ingreso_institucion: Optional[date] = None
    
    contacto_emergencia_nombre: Optional[str] = Field(None, max_length=150)
    contacto_emergencia_telefono: Optional[str] = Field(None, max_length=20)
    contacto_emergencia_relacion: Optional[str] = Field(None, max_length=50)
    
    foto_perfil: Optional[str] = Field(None, max_length=255)

    @validator('cedula')
    def validar_cedula(cls, v):
        if not v.strip():
            raise ValueError('La cédula no puede estar vacía')
        # Validación básica de cédula ecuatoriana (10 dígitos)
        cedula_limpia = v.strip().replace('-', '').replace(' ', '')
        if not cedula_limpia.isdigit():
            raise ValueError('La cédula debe contener solo números')
        if len(cedula_limpia) != 10:
            raise ValueError('La cédula debe tener 10 dígitos')
        return cedula_limpia

    @validator('nombre', 'apellido')
    def validar_nombres(cls, v):
        if not v.strip():
            raise ValueError('Este campo no puede estar vacío')
        # Solo letras y espacios
        if not all(c.isalpha() or c.isspace() for c in v):
            raise ValueError('Solo se permiten letras y espacios')
        return v.strip().title()

    @validator('fecha_nacimiento')
    def validar_fecha_nacimiento(cls, v):
        if v and v > date.today():
            raise ValueError('La fecha de nacimiento no puede ser futura')
        if v and (date.today().year - v.year) > 100:
            raise ValueError('Edad no válida')
        return v

    @validator('telefono', 'celular', 'contacto_emergencia_telefono')
    def validar_telefono(cls, v):
        if v:
            telefono_limpio = v.strip().replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
            if not telefono_limpio.isdigit():
                raise ValueError('El teléfono debe contener solo números')
            if len(telefono_limpio) < 7 or len(telefono_limpio) > 15:
                raise ValueError('Número de teléfono inválido')
        return v

class PersonaCreate(PersonaBase):
    pass

class PersonaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    apellido: Optional[str] = Field(None, min_length=2, max_length=100)
    fecha_nacimiento: Optional[date] = None
    genero: Optional[GeneroEnum] = None
    telefono: Optional[str] = None
    celular: Optional[str] = None
    email_personal: Optional[EmailStr] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    provincia: Optional[str] = None
    tipo_persona: Optional[TipoPersonaEnum] = None
    id_departamento: Optional[int] = None
    cargo: Optional[str] = None
    fecha_ingreso_institucion: Optional[date] = None
    contacto_emergencia_nombre: Optional[str] = None
    contacto_emergencia_telefono: Optional[str] = None
    contacto_emergencia_relacion: Optional[str] = None
    foto_perfil: Optional[str] = None
    estado: Optional[EstadoPersonaEnum] = None

class PersonaResponse(PersonaBase):
    id_persona: int
    estado: EstadoPersonaEnum
    fecha_registro: datetime
    fecha_actualizacion: Optional[datetime]

    class Config:
        from_attributes = True  # Reemplaza orm_mode en Pydantic v2