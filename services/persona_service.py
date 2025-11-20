from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from repositories.persona_repo import PersonaRepository
from repositories.departamento_repo import DepartamentoRepository
from schemas.persona_schemas import PersonaCreate, PersonaUpdate
from models.persona import Persona, TipoPersonaEnum, EstadoPersonaEnum
from exceptions.base import ValidationException

class PersonaService:
    """Servicio con lógica de negocio para Persona"""
    
    def __init__(self, db: Session):
        self.db = db
        self.persona_repo = PersonaRepository(db)
        self.departamento_repo = DepartamentoRepository(db)
    
    def crear_persona(self, persona_data: PersonaCreate) -> Persona:
        """
        Crear persona con validaciones de negocio
        - Valida edad mínima
        - Verifica cédula única
        - Valida departamento si existe
        """
        
        # Validación: edad mínima para personal
        if persona_data.fecha_nacimiento:
            edad = (datetime.now().date() - persona_data.fecha_nacimiento).days // 365
            
            if persona_data.tipo_persona in [TipoPersonaEnum.docente, TipoPersonaEnum.administrativo]:
                if edad < 18:
                    raise ValidationException(
                        "El personal docente y administrativo debe ser mayor de 18 años"
                    )
            
            if edad < 0 or edad > 120:
                raise ValidationException("Fecha de nacimiento inválida")
        
        # Validación: departamento requerido para docentes y administrativos
        if persona_data.tipo_persona in [TipoPersonaEnum.docente, TipoPersonaEnum.administrativo]:
            if not persona_data.id_departamento:
                raise ValidationException(
                    f"El personal {persona_data.tipo_persona.value} debe tener un departamento asignado"
                )
        
        # Validación: departamento existe y está activo
        if persona_data.id_departamento:
            departamento = self.departamento_repo.get_by_id(persona_data.id_departamento)
            
            if not departamento.activo:
                raise ValidationException(
                    f"No se puede asignar el departamento '{departamento.nombre}' porque está inactivo"
                )
        
        # Validación: email requerido para personal
        if persona_data.tipo_persona in [TipoPersonaEnum.docente, TipoPersonaEnum.administrativo]:
            if not persona_data.email_personal:
                raise ValidationException(
                    "El personal debe tener un email registrado"
                )
        
        # El repositorio ya valida la cédula única
        return self.persona_repo.create(persona_data)
    
    def obtener_persona(self, id_persona: int) -> Persona:
        """Obtener persona por ID"""
        return self.persona_repo.get_by_id(id_persona)
    
    def buscar_por_cedula(self, cedula: str) -> Persona:
        """Buscar persona por cédula"""
        # Limpiar cédula
        cedula_limpia = cedula.strip().replace('-', '').replace(' ', '')
        
        persona = self.persona_repo.get_by_cedula(cedula_limpia)
        
        if not persona:
            raise ValidationException(f"Persona con cédula {cedula} no encontrada")
        
        return persona
    
    def listar_personas(
        self,
        skip: int = 0,
        limit: int = 100,
        tipo_persona: Optional[TipoPersonaEnum] = None,
        estado: Optional[EstadoPersonaEnum] = None,
        id_departamento: Optional[int] = None,
        busqueda: Optional[str] = None
    ) -> List[Persona]:
        """Listar personas con filtros y validaciones"""
        
        # Validación: límite máximo
        if limit > 500:
            raise ValidationException("El límite máximo es 500 registros")
        
        # Si hay búsqueda por texto, usar el método de búsqueda
        if busqueda:
            return self.persona_repo.search_by_name(busqueda, limit)
        
        # Convertir enums a string para el repositorio
        tipo_str = tipo_persona.value if tipo_persona else None
        estado_str = estado.value if estado else None
        
        return self.persona_repo.get_all(
            skip=skip,
            limit=limit,
            tipo_persona=tipo_str,
            estado=estado_str,
            id_departamento=id_departamento
        )
    
    def actualizar_persona(self, id_persona: int, persona_data: PersonaUpdate) -> Persona:
        """Actualizar persona con validaciones de negocio"""
        
        # Obtener persona actual
        persona_actual = self.persona_repo.get_by_id(id_persona)
        
        # Validación: no permitir cambio de tipo si tiene usuario
        if persona_data.tipo_persona and persona_data.tipo_persona != persona_actual.tipo_persona:
            if hasattr(persona_actual, 'usuario') and persona_actual.usuario:
                raise ValidationException(
                    "No se puede cambiar el tipo de persona porque tiene un usuario asociado"
                )
        
        # Validación: departamento existe y está activo si se está actualizando
        if persona_data.id_departamento is not None:
            departamento = self.departamento_repo.get_by_id(persona_data.id_departamento)
            
            if not departamento.activo:
                raise ValidationException(
                    f"No se puede asignar el departamento '{departamento.nombre}' porque está inactivo"
                )
        
        # Validación: fecha de nacimiento
        if persona_data.fecha_nacimiento:
            edad = (datetime.now().date() - persona_data.fecha_nacimiento).days // 365
            tipo_actual = persona_data.tipo_persona or persona_actual.tipo_persona
            
            if tipo_actual in [TipoPersonaEnum.docente, TipoPersonaEnum.administrativo]:
                if edad < 18:
                    raise ValidationException(
                        "El personal docente y administrativo debe ser mayor de 18 años"
                    )
        
        return self.persona_repo.update(id_persona, persona_data)
    
    def cambiar_estado(self, id_persona: int, estado: EstadoPersonaEnum) -> Persona:
        """Cambiar estado de persona con validaciones"""
        
        persona = self.persona_repo.get_by_id(id_persona)
        
        # Validación: no desactivar si tiene usuario activo
        if estado == EstadoPersonaEnum.inactivo:
            if hasattr(persona, 'usuario') and persona.usuario:
                if persona.usuario.estado == "activo":
                    raise ValidationException(
                        "No se puede inactivar una persona con un usuario activo. "
                        "Primero desactive el usuario."
                    )
        
        # Validación: no retirar personal activo sin pasar por inactivo
        if estado == EstadoPersonaEnum.retirado and persona.estado == EstadoPersonaEnum.activo:
            raise ValidationException(
                "Debe primero inactivar a la persona antes de marcarla como retirada"
            )
        
        # Actualizar el estado
        persona.estado = estado
        self.db.commit()
        self.db.refresh(persona)
        
        return persona
    
    def eliminar_persona(self, id_persona: int) -> dict:
        """Eliminar persona (soft delete) con validaciones"""
        
        persona = self.persona_repo.get_by_id(id_persona)
        
        # Validación: no eliminar si tiene usuario
        if hasattr(persona, 'usuario') and persona.usuario:
            raise ValidationException(
                "No se puede eliminar una persona que tiene un usuario asociado. "
                "Primero elimine el usuario."
            )
        
        # Validación adicional: confirmar tipo de persona
        if persona.tipo_persona == TipoPersonaEnum.docente:
            # Aquí podrías agregar validaciones adicionales
            # Por ejemplo, verificar si tiene clases asignadas
            pass
        
        return self.persona_repo.delete(id_persona)
    
    def obtener_estadisticas(self) -> dict:
        """Obtener estadísticas generales con cálculos adicionales"""
        
        # Total de personas
        total = self.persona_repo.count()
        
        # Por tipo de persona
        stats_tipo = {}
        for tipo in TipoPersonaEnum:
            stats_tipo[tipo.value] = self.persona_repo.count(tipo_persona=tipo.value)
        
        # Por estado
        stats_estado = {}
        for estado in EstadoPersonaEnum:
            stats_estado[estado.value] = self.persona_repo.count(estado=estado.value)
        
        # Calcular porcentajes
        porcentajes = {}
        if total > 0:
            activos = stats_estado.get('activo', 0)
            porcentajes = {
                'activos': round((activos / total) * 100, 2),
                'docentes': round((stats_tipo.get('docente', 0) / total) * 100, 2),
                'administrativos': round((stats_tipo.get('administrativo', 0) / total) * 100, 2),
                'estudiantes': round((stats_tipo.get('estudiante', 0) / total) * 100, 2),
                'externos': round((stats_tipo.get('externo', 0) / total) * 100, 2)
            }
        
        return {
            "total_personas": total,
            "por_tipo": stats_tipo,
            "por_estado": stats_estado,
            "porcentajes": porcentajes,
            "activos": stats_estado.get('activo', 0),
            "inactivos": stats_estado.get('inactivo', 0),
            "retirados": stats_estado.get('retirado', 0)
        }
    
    def validar_disponibilidad_cedula(self, cedula: str, exclude_id: Optional[int] = None) -> dict:
        """Validar si una cédula está disponible"""
        
        # Limpiar cédula
        cedula_limpia = cedula.strip().replace('-', '').replace(' ', '')
        
        persona_existente = self.persona_repo.get_by_cedula(cedula_limpia)
        
        # Si existe y no es la que estamos excluyendo
        if persona_existente and (exclude_id is None or persona_existente.id_persona != exclude_id):
            return {
                "cedula": cedula_limpia,
                "disponible": False,
                "mensaje": "La cédula ya está registrada"
            }
        
        return {
            "cedula": cedula_limpia,
            "disponible": True,
            "mensaje": "Cédula disponible"
        }
    
    def buscar_por_nombre(self, search_term: str, limit: int = 20) -> List[Persona]:
        """Buscar personas por nombre o apellido"""
        
        if not search_term or len(search_term.strip()) < 2:
            raise ValidationException("El término de búsqueda debe tener al menos 2 caracteres")
        
        return self.persona_repo.search_by_name(search_term.strip(), limit)