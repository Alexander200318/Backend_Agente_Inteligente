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
    
    def get_by_id(self, id_categoria: int, incluir_eliminados: bool = False):
        """
        Obtiene una categoría por ID.
        Por defecto excluye las eliminadas.
        """
        query = self.db.query(Categoria).filter(Categoria.id_categoria == id_categoria)
        
        # ✅ Excluir eliminados por defecto
        if not incluir_eliminados:
            query = query.filter(Categoria.eliminado == False)
        
        cat = query.first()
        if not cat:
            raise NotFoundException("Categoria", id_categoria)
        return cat
    
    def get_by_agente(
        self, 
        id_agente: int, 
        activo: Optional[bool] = None,
        incluir_eliminados: bool = False  # ✅ NUEVO
    ):
        """
        Lista categorías por agente.
        Por defecto excluye las eliminadas.
        """
        query = self.db.query(Categoria).filter(Categoria.id_agente == id_agente)
        
        # ✅ Excluir eliminados por defecto
        if not incluir_eliminados:
            query = query.filter(Categoria.eliminado == False)
        
        if activo is not None:
            query = query.filter(Categoria.activo == activo)
        
        return query.order_by(Categoria.orden, Categoria.nombre).all()
    
    def update(self, id_categoria: int, data: CategoriaUpdate):
        try:
            # ✅ Permitir actualizar incluso si está eliminada (para poder restaurarla)
            cat = self.get_by_id(id_categoria, incluir_eliminados=True)
            
            for field, value in data.dict(exclude_unset=True).items():
                setattr(cat, field, value)
            
            self.db.commit()
            self.db.refresh(cat)
            return cat
        except Exception as e:
            self.db.rollback()
            raise DatabaseException(str(e))
    
    def delete(self, id_categoria: int):
        """
        ⚠️ ELIMINACIÓN FÍSICA - Solo usar si realmente quieres borrar el registro.
        Para eliminado lógico, usa update() con eliminado=True
        """
        cat = self.get_by_id(id_categoria, incluir_eliminados=True)
        try:
            self.db.delete(cat)
            self.db.commit()
            return {"message": "Categoría eliminada físicamente", "id": id_categoria}
        except Exception as e:
            self.db.rollback()
            raise DatabaseException(str(e))
    
    # ✅ NUEVO: Método específico para eliminado lógico
    def soft_delete(self, id_categoria: int):
        """
        Eliminado lógico: marca eliminado=True y activo=False
        """
        try:
            cat = self.get_by_id(id_categoria, incluir_eliminados=False)
            cat.eliminado = True
            cat.activo = False
            self.db.commit()
            self.db.refresh(cat)
            return cat
        except Exception as e:
            self.db.rollback()
            raise DatabaseException(str(e))
    
    def restore(self, id_categoria: int):
        """
        Restaura una categoría eliminada lógicamente.
        Marca eliminado=False y activo=True para que vuelva a aparecer.
        """
        try:
            # ✅ Obtener incluyendo eliminados (para poder restaurarla)
            cat = self.get_by_id(id_categoria, incluir_eliminados=True)
            
            # ✅ Validar que SÍ esté eliminada
            if not cat.eliminado:
                from exceptions.base import ValidationException
                raise ValidationException(
                    "La categoría no está eliminada, no se puede restaurar"
                )
            
            # ✅ RESTAURACIÓN COMPLETA: Ambos campos en True
            cat.eliminado = False  # Ya no está eliminada
            cat.activo = True       # Vuelve a estar activa
            
            self.db.commit()
            self.db.refresh(cat)
            return cat
            
        except Exception as e:
            self.db.rollback()
            raise DatabaseException(str(e))