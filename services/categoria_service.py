from typing import Optional
from sqlalchemy.orm import Session
from repositories.categoria_repo import CategoriaRepository, CategoriaCreate, CategoriaUpdate
from rag.rag_service import RAGService
from models.unidad_contenido import UnidadContenido
from exceptions.base import ValidationException

class CategoriaService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CategoriaRepository(db)
        self.rag = RAGService(db)
    
    def crear_categoria(self, data: CategoriaCreate, creado_por: Optional[int] = None):
        categoria = self.repo.create(data, creado_por)
        # 🔥 Indexar categoría en Chroma
        self.rag.indexar_categoria(categoria)
        return categoria
    
    def listar_por_agente(self, id_agente: int, activo: Optional[bool] = None):
        return self.repo.get_by_agente(id_agente, activo)
    
    def actualizar_categoria(self, id_categoria: int, data: CategoriaUpdate):
        categoria = self.repo.update(id_categoria, data)
        # 🔥 Reindexar categoría
        self.rag.indexar_categoria(categoria)
        return categoria
    
    def eliminar_categoria(self, id_categoria: int):
        """
        Elimina una categoría solo si NO tiene contenido asociado
        """
        # 🔥 Verificar si tiene contenido asociado
        contenidos_count = self.db.query(UnidadContenido).filter(
            UnidadContenido.id_categoria == id_categoria
        ).count()
        
        if contenidos_count > 0:
            raise ValidationException(
                f"No se puede eliminar la categoría porque tiene {contenidos_count} contenido(s) asociado(s)"
            )
        
        # 🔥 Verificar si tiene subcategorías
        from models.categoria import Categoria
        subcategorias_count = self.db.query(Categoria).filter(
            Categoria.id_categoria_padre == id_categoria
        ).count()
        
        if subcategorias_count > 0:
            raise ValidationException(
                f"No se puede eliminar la categoría porque tiene {subcategorias_count} subcategoría(s)"
            )
        
        # Si no tiene contenido ni subcategorías, eliminar
        return self.repo.delete(id_categoria)