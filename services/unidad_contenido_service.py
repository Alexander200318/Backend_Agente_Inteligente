from exceptions.base import ValidationException
from typing import Optional, List
from sqlalchemy.orm import Session
from repositories.unidad_contenido_repo import UnidadContenidoRepository,UnidadContenidoCreate,UnidadContenidoUpdate
from rag.rag_service import RAGService

class UnidadContenidoService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UnidadContenidoRepository(db)
        self.rag = RAGService()

    def crear_contenido(self, data: UnidadContenidoCreate, creado_por: int):
        if len(data.contenido) < 50:
            raise ValidationException("El contenido debe tener al menos 50 caracteres")
        
        contenido = self.repo.create(data, creado_por)
        
        # 🔥 Indexar en RAG
        self.rag.indexar_unidad(contenido)
        
        return contenido
    
    def listar_por_agente(self, id_agente: int, estado: Optional[str] = None, skip: int = 0, limit: int = 100):
        return self.repo.get_by_agente(id_agente, estado, skip, limit)
    



    
    def actualizar_contenido(self, id_contenido: int, data: UnidadContenidoUpdate, actualizado_por: int):
        contenido = self.repo.update(id_contenido, data, actualizado_por)
        
        # 🔥 Reindexar en RAG
        self.rag.indexar_unidad(contenido)
        
        return contenido
    



    def publicar_contenido(self, id_contenido: int, publicado_por: int):
        contenido = self.repo.publicar(id_contenido, publicado_por)
        
        
        return contenido
    

