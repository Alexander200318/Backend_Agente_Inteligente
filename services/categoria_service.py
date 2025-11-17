
from typing import Optional
from sqlalchemy.orm import Session
from repositories.categoria_repo import CategoriaRepository,CategoriaCreate,CategoriaUpdate


class CategoriaService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CategoriaRepository(db)
    
    def crear_categoria(self, data: CategoriaCreate, creado_por: Optional[int] = None):
        return self.repo.create(data, creado_por)
    
    def listar_por_agente(self, id_agente: int, activo: Optional[bool] = None):
        return self.repo.get_by_agente(id_agente, activo)
    
    def actualizar_categoria(self, id_categoria: int, data: CategoriaUpdate):
        return self.repo.update(id_categoria, data)
    
    def eliminar_categoria(self, id_categoria: int):
        return self.repo.delete(id_categoria)