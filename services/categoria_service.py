from typing import Optional, List
from sqlalchemy.orm import Session

from repositories.categoria_repo import (
    CategoriaRepository,
    CategoriaCreate,
    CategoriaUpdate,
)
from rag.rag_service import RAGService
from models.categoria import Categoria
from models.unidad_contenido import UnidadContenido
from exceptions.base import ValidationException


class CategoriaService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CategoriaRepository(db)
        self.rag = RAGService(db)

    # ============================================
    # 🔹 Crear categoría
    # ============================================
    def crear_categoria(
        self,
        data: CategoriaCreate,
        creado_por: Optional[int] = None
    ) -> Categoria:
        categoria = self.repo.create(data, creado_por)
        # 🔥 Indexar categoría en Chroma para el RAG
        self.rag.indexar_categoria(categoria)
        return categoria

    # ============================================
    # 🔹 Listar categorías con filtros opcionales
    # ============================================
    def listar_categorias(
        self,
        activo: Optional[bool] = None,
        id_agente: Optional[int] = None
    ) -> List[Categoria]:
        """
        Lista todas las categorías con filtros opcionales:
        - activo: True / False
        - id_agente: filtrar por agente
        """
        query = self.db.query(Categoria)

        if activo is not None:
            query = query.filter(Categoria.activo == activo)

        if id_agente is not None:
            query = query.filter(Categoria.id_agente == id_agente)

        # Ordenar por orden y luego por nombre
        query = query.order_by(Categoria.orden, Categoria.nombre)

        return query.all()

    # ============================================
    # 🔹 Listar categorías por agente (modo repo)
    # ============================================
    def listar_por_agente(
        self,
        id_agente: int,
        activo: Optional[bool] = None
    ) -> List[Categoria]:
        return self.repo.get_by_agente(id_agente, activo)

    # ============================================
    # 🔹 Actualizar categoría
    # ============================================
    def actualizar_categoria(
        self,
        id_categoria: int,
        data: CategoriaUpdate
    ) -> Categoria:
        categoria = self.repo.update(id_categoria, data)
        # 🔥 Reindexar categoría en Chroma
        self.rag.indexar_categoria(categoria)
        return categoria

    # ============================================
    # 🔹 Eliminar categoría (con validaciones)
    # ============================================
    def eliminar_categoria(self, id_categoria: int):
        """
        Elimina una categoría solo si:
        - NO tiene contenidos asociados
        - NO tiene subcategorías
        """

        # 🔥 Verificar si tiene contenido asociado
        contenidos_count = (
            self.db.query(UnidadContenido)
            .filter(UnidadContenido.id_categoria == id_categoria)
            .count()
        )

        if contenidos_count > 0:
            raise ValidationException(
                f"No se puede eliminar la categoría porque tiene {contenidos_count} contenido(s) asociado(s)"
            )

        # 🔥 Verificar si tiene subcategorías
        subcategorias_count = (
            self.db.query(Categoria)
            .filter(Categoria.id_categoria_padre == id_categoria)
            .count()
        )

        if subcategorias_count > 0:
            raise ValidationException(
                f"No se puede eliminar la categoría porque tiene {subcategorias_count} subcategoría(s)"
            )

        # Si no tiene contenido ni subcategorías, eliminar
        return self.repo.delete(id_categoria)
