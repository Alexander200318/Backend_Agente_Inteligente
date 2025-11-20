
from typing import Optional
from sqlalchemy.orm import Session
from repositories.categoria_repo import CategoriaRepository,CategoriaCreate,CategoriaUpdate
from rag.rag_service import RAGService

class CategoriaService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CategoriaRepository(db)
        self.rag = RAGService()
    
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
        return self.repo.delete(id_categoria)