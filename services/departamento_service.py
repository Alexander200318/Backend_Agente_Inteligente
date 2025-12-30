from sqlalchemy.orm import Session
from typing import List, Optional
from repositories.departamento_repo import DepartamentoRepository
from schemas.departamento_schemas import DepartamentoCreate, DepartamentoUpdate
from models.departamento import Departamento

from exceptions.base import ValidationException

class DepartamentoService:
    """Servicio con lógica de negocio para Departamento"""
    
    def __init__(self, db: Session):
        self.db = db
        self.repo = DepartamentoRepository(db)
        
    
    def crear_departamento(
        self, 
        depto_data: DepartamentoCreate,
        creado_por_id: Optional[int] = None,
        crear_modelo_ollama: bool = True
    ) -> Departamento:
        """
        Crear departamento con validaciones de negocio
        """
        
        # Validación: código no puede tener espacios
        if ' ' in depto_data.codigo:
            raise ValidationException("El código no puede contener espacios")
        
        # Validación: nombre debe ser descriptivo
        if len(depto_data.nombre.strip()) < 5:
            raise ValidationException("El nombre debe ser más descriptivo (mínimo 5 caracteres)")
        
        return self.repo.create(depto_data, creado_por_id)
    
    def obtener_departamento(self, id_departamento: int) -> Departamento:
        """Obtener departamento por ID"""
        return self.repo.get_by_id(id_departamento)
    
    def obtener_por_codigo(self, codigo: str) -> Departamento:
        """Obtener departamento por código"""
        departamento = self.repo.get_by_codigo(codigo)
        if not departamento:
            raise ValidationException(f"No existe departamento con código '{codigo}'")
        return departamento
    
    def listar_departamentos(
        self,
        skip: int = 0,
        limit: int = 100,
        activo: Optional[bool] = None,
        facultad: Optional[str] = None
    ) -> List[Departamento]:
        """Listar departamentos con filtros"""
        
        # Validación: límite máximo
        if limit > 500:
            raise ValidationException("El límite máximo es 500 registros")
        
        return self.repo.get_all(skip, limit, activo, facultad)
    
    def actualizar_departamento(
        self,
        id_departamento: int,
        depto_data: DepartamentoUpdate,
        actualizado_por_id: Optional[int] = None
    ) -> Departamento:
        """Actualizar departamento con validaciones"""
        
        # Validación: si se actualiza código, no puede tener espacios
        if depto_data.codigo and ' ' in depto_data.codigo:
            raise ValidationException("El código no puede contener espacios")
        
        return self.repo.update(id_departamento, depto_data, actualizado_por_id)
    
    def eliminar_departamento(
        self,
        id_departamento: int,
        eliminado_por_id: Optional[int] = None
    ) -> dict:
        """Desactivar departamento (soft delete)"""
        
        # Validación de negocio: verificar si tiene personas activas
        depto = self.repo.get_by_id(id_departamento)
        stats = self.repo.get_estadisticas(id_departamento)
        
        if stats['total_personas'] > 0:
            raise ValidationException(
                f"No se puede desactivar el departamento porque tiene {stats['total_personas']} persona(s) asociada(s). "
                "Por favor, reasigne o desactive las personas primero."
            )
        
        return self.repo.delete(id_departamento)
    
    def asignar_jefe(
        self,
        id_departamento: int,
        id_usuario_jefe: int,
        asignado_por_id: Optional[int] = None
    ) -> Departamento:
        """Asignar jefe al departamento"""
        
        # Obtener departamento
        depto = self.repo.get_by_id(id_departamento)
        
        # Validar que el usuario existe (se haría con UsuarioRepository)
        # Por ahora solo asignamos
        update_data = DepartamentoUpdate(jefe_departamento=id_usuario_jefe)
        return self.repo.update(id_departamento, update_data, asignado_por_id)
    
    def obtener_estadisticas_departamento(self, id_departamento: int) -> dict:
        """Obtener estadísticas completas del departamento"""
        depto = self.repo.get_by_id(id_departamento)
        stats = self.repo.get_estadisticas(id_departamento)
        
        return {
            "departamento": {
                "id": depto.id_departamento,
                "nombre": depto.nombre,
                "codigo": depto.codigo,
                "activo": depto.activo
            },
            **stats
        }
    
    def obtener_estadisticas_generales(self) -> dict:
        """Obtener estadísticas generales de departamentos"""
        return {
            "total_departamentos": self.repo.count(),
            "departamentos_activos": self.repo.count(activo=True),
            "departamentos_inactivos": self.repo.count(activo=False)
        }
    
    def buscar_departamentos(self, termino: str) -> List[Departamento]:
        """Buscar departamentos por nombre o código"""
        if len(termino.strip()) < 2:
            raise ValidationException("El término de búsqueda debe tener al menos 2 caracteres")
        
        return self.repo.search(termino)
    
    # 🔥 NUEVAS FUNCIONES PARA OLLAMA
    
    def regenerar_modelo_ollama(self, id_departamento: int) -> dict:
        """
        Regenerar modelo de Ollama para el departamento
        """
        # Obtener departamento
        depto = self.repo.get_by_id(id_departamento)
        
        # TODO: Aquí iría la lógica real de Ollama
        # Por ahora retornamos un mensaje de éxito simulado
        return {
            "status": "success",
            "message": f"Modelo Ollama regenerado para departamento '{depto.nombre}'",
            "departamento_id": id_departamento,
            "codigo": depto.codigo
        }
    
    def consultar_modelo_departamento(self, codigo_departamento: str, pregunta: str) -> str:
        """
        Consultar al modelo de IA del departamento
        """
        # Obtener departamento por código
        depto = self.obtener_por_codigo(codigo_departamento)
        
        # TODO: Aquí iría la lógica real de consulta a Ollama
        # Por ahora retornamos una respuesta simulada
        return (
            f"Esta es una respuesta simulada del modelo de '{depto.nombre}' "
            f"para la pregunta: '{pregunta}'. "
            "Integración real con Ollama pendiente."
        )