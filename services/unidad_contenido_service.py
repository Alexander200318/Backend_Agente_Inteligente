from exceptions.base import ValidationException
from typing import Optional, List
from sqlalchemy.orm import Session
from repositories.unidad_contenido_repo import UnidadContenidoRepository,UnidadContenidoCreate,UnidadContenidoUpdate
from datetime import date


class UnidadContenidoService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UnidadContenidoRepository(db)
    
    def crear_contenido(self, data: UnidadContenidoCreate, creado_por: int):
        if len(data.contenido) < 50:
            raise ValidationException("El contenido debe tener al menos 50 caracteres")
        
        contenido = self.repo.create(data, creado_por)
        
        # Actualizar modelo de Ollama automáticamente
        self._actualizar_modelo_ollama(data.id_agente)
        
        return contenido
    
    def listar_por_agente(self, id_agente: int, estado: Optional[str] = None, skip: int = 0, limit: int = 100):
        return self.repo.get_by_agente(id_agente, estado, skip, limit)
    
    def actualizar_contenido(self, id_contenido: int, data: UnidadContenidoUpdate, actualizado_por: int):
        contenido = self.repo.update(id_contenido, data, actualizado_por)
        
        # Actualizar modelo de Ollama
        self._actualizar_modelo_ollama(contenido.id_agente)
        
        return contenido
    
    def publicar_contenido(self, id_contenido: int, publicado_por: int):
        contenido = self.repo.publicar(id_contenido, publicado_por)
        
        # Actualizar modelo de Ollama al publicar
        self._actualizar_modelo_ollama(contenido.id_agente)
        
        return contenido
    
    def _actualizar_modelo_ollama(self, id_agente: int):
        """Actualizar modelo de Ollama cuando cambia el contenido"""
        try:
            from models.agente_virtual import AgenteVirtual
            from services.ollama_service import DepartamentoOllamaService
            
            # Obtener departamento del agente
            agente = self.db.query(AgenteVirtual).filter(
                AgenteVirtual.id_agente == id_agente
            ).first()
            
            if agente and agente.id_departamento:
                ollama_service = DepartamentoOllamaService(self.db)
                resultado = ollama_service.actualizar_modelo_departamento(
                    agente.id_departamento
                )
                print(f"✅ Modelo Ollama actualizado: {resultado['nombre_modelo']}")
        except Exception as e:
            print(f"⚠️  No se pudo actualizar modelo Ollama: {e}")
