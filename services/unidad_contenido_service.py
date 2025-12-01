# app/services/unidad_contenido_service.py

from exceptions.base import ValidationException
from typing import Optional, List
from sqlalchemy.orm import Session
from repositories.unidad_contenido_repo import UnidadContenidoRepository,UnidadContenidoCreate,UnidadContenidoUpdate
from rag.rag_service import RAGService
from models.usuario import Usuario

class UnidadContenidoService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UnidadContenidoRepository(db)
        self.rag = RAGService(db)

    def crear_contenido(self, data: UnidadContenidoCreate, creado_por: Optional[int] = None):
        if len(data.contenido) < 50:
            raise ValidationException("El contenido debe tener al menos 50 caracteres")
        
        # Validar si el usuario existe, si no, poner None
        if creado_por is not None:
            usuario = self.db.query(Usuario).filter(Usuario.id_usuario == creado_por).first()
            if not usuario:
                creado_por = None
        
        contenido = self.repo.create(data, creado_por)
        
        # 🔥 Indexar en RAG - Obtener la categoría primero
        from models.categoria import Categoria
        categoria = self.db.query(Categoria).filter(Categoria.id_categoria == contenido.id_categoria).first()
        
        if categoria:
            self.rag.ingest_unidad(contenido, categoria)
        
        return contenido
    
    def listar_por_agente(self, id_agente: int, estado: Optional[str] = None, skip: int = 0, limit: int = 100):
        return self.repo.get_by_agente(id_agente, estado, skip, limit)
    
    def actualizar_contenido(self, id_contenido: int, data: UnidadContenidoUpdate, actualizado_por: Optional[int] = None):
        # Validar si el usuario existe, si no, poner None
        if actualizado_por is not None:
            usuario = self.db.query(Usuario).filter(Usuario.id_usuario == actualizado_por).first()
            if not usuario:
                actualizado_por = None
        
        contenido = self.repo.update(id_contenido, data, actualizado_por)
        
        # 🔥 Reindexar en RAG - Obtener la categoría primero
        from models.categoria import Categoria
        categoria = self.db.query(Categoria).filter(Categoria.id_categoria == contenido.id_categoria).first()
        
        if categoria:
            self.rag.ingest_unidad(contenido, categoria)
        
        return contenido
    
    def publicar_contenido(self, id_contenido: int, publicado_por: Optional[int] = None):
        # Validar si el usuario existe, si no, poner None
        if publicado_por is not None:
            usuario = self.db.query(Usuario).filter(Usuario.id_usuario == publicado_por).first()
            if not usuario:
                publicado_por = None
        
        contenido = self.repo.publicar(id_contenido, publicado_por)
        
        return contenido
    


    def eliminar_contenido(self, id_contenido: int) -> dict:
        """
        Elimina contenido de BD y ChromaDB
        """
        # 1. Obtener el contenido antes de eliminar (necesitamos id_agente)
        contenido = self.repo.get_by_id(id_contenido)
        id_agente = contenido.id_agente
        
        # 2. Eliminar de ChromaDB primero
        rag_result = self.rag.delete_unidad(id_contenido, id_agente)
        
        # 3. Eliminar de la base de datos
        db_result = self.repo.delete(id_contenido)
        
        return {
            "ok": True,
            "id_contenido": id_contenido,
            "deleted_from_chromadb": rag_result.get("ok", False),
            "deleted_from_database": db_result
        }
