from typing import Optional
from sqlalchemy.orm import Session, joinedload
from models.categoria import Categoria
from schemas.categoria_schemas import CategoriaCreate, CategoriaUpdate
from exceptions.base import (
    NotFoundException, 
    DatabaseException
)

class CategoriaRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, data: CategoriaCreate, creado_por: Optional[int] = None):
        try:
            categoria = Categoria(**data.dict())
            if creado_por:
                categoria.creado_por = creado_por
            self.db.add(categoria)
            self.db.commit()
            self.db.refresh(categoria)
            return categoria
        except Exception as e:
            self.db.rollback()
            raise DatabaseException(str(e))
    
    def get_by_id(self, id_categoria: int):
        cat = self.db.query(Categoria).filter(Categoria.id_categoria == id_categoria).first()
        if not cat:
            raise NotFoundException("Categoria", id_categoria)
        return cat
    
    def get_by_agente(self, id_agente: int, activo: Optional[bool] = None):
        query = self.db.query(Categoria).filter(Categoria.id_agente == id_agente)
        if activo is not None:
            query = query.filter(Categoria.activo == activo)
        return query.order_by(Categoria.orden, Categoria.nombre).all()
    
    def update(self, id_categoria: int, data: CategoriaUpdate):
        try:
            cat = self.get_by_id(id_categoria)
            for field, value in data.dict(exclude_unset=True).items():
                setattr(cat, field, value)
            self.db.commit()
            self.db.refresh(cat)
            return cat
        except Exception as e:
            self.db.rollback()
            raise DatabaseException(str(e))
    
    def delete(self, id_categoria: int):
        cat = self.get_by_id(id_categoria)
        try:
            cat.activo = False
            self.db.commit()
            return {"message": "Categoría desactivada", "id": id_categoria}
        except Exception as e:
            self.db.rollback()
            raise DatabaseException(str(e))