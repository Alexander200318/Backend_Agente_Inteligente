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
    # 🔹 Crear categoría CON usuario del token
    # ============================================
    def crear_categoria_con_usuario(
        self,
        data: dict  # ✅ CAMBIO: Ahora recibe dict con creado_por incluido
    ) -> Categoria:
        """
        Crea una categoría incluyendo el creado_por del token.
        El dict 'data' ya incluye: nombre, descripcion, id_agente, creado_por, etc.
        """
        # Convertir dict a objeto CategoriaCreate para validación
        categoria_create = CategoriaCreate(**data)
        
        # Crear con creado_por incluido
        categoria = self.repo.create(
            categoria_create,
            creado_por=data.get("creado_por")
        )
        
        # 🔥 Indexar categoría en Chroma para el RAG
        self.rag.indexar_categoria(categoria)
        return categoria

    # ============================================
    # 🔹 Crear categoría (método legacy - mantener compatibilidad)
    # ============================================
    def crear_categoria(
        self,
        data: CategoriaCreate,
        creado_por: Optional[int] = None
    ) -> Categoria:
        """
        Método legacy para mantener compatibilidad con código existente.
        Recomendado usar crear_categoria_con_usuario() en nuevos endpoints.
        """
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
        id_agente: Optional[int] = None,
        incluir_eliminados: bool = False  # ✅ NUEVO
    ) -> List[Categoria]:
        """
        Lista todas las categorías con filtros opcionales:
        - activo: True / False
        - id_agente: filtrar por agente
        - incluir_eliminados: si False (default), excluye eliminados
        """
        query = self.db.query(Categoria)

        # ✅ NUEVO: Excluir eliminados por defecto
        if not incluir_eliminados:
            query = query.filter(Categoria.eliminado == False)

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
        activo: Optional[bool] = None,
        incluir_eliminados: bool = False  # ✅ NUEVO
    ) -> List[Categoria]:
        return self.repo.get_by_agente(id_agente, activo, incluir_eliminados)

    # ============================================
    # 🔹 Actualizar categoría CON usuario del token
    # ============================================
    def actualizar_categoria_con_usuario(
        self,
        id_categoria: int,
        data: dict  # ✅ CAMBIO: Recibe dict con creado_por opcional
    ) -> Categoria:
        """
        Actualiza una categoría, opcionalmente actualizando creado_por.
        """
        # Convertir dict a CategoriaUpdate (solo campos presentes)
        update_data = {k: v for k, v in data.items() if v is not None}
        categoria_update = CategoriaUpdate(**update_data)
        
        categoria = self.repo.update(id_categoria, categoria_update)
        
        # 🔥 Reindexar categoría en Chroma
        self.rag.indexar_categoria(categoria)
        return categoria

    # ============================================
    # 🔹 Actualizar categoría (método legacy)
    # ============================================
    def actualizar_categoria(
        self,
        id_categoria: int,
        data: CategoriaUpdate
    ) -> Categoria:
        """
        Método legacy para mantener compatibilidad.
        Recomendado usar actualizar_categoria_con_usuario() en nuevos endpoints.
        """
        categoria = self.repo.update(id_categoria, data)
        # 🔥 Reindexar categoría en Chroma
        self.rag.indexar_categoria(categoria)
        return categoria

    # ============================================
    # 🔹 Eliminar categoría (ELIMINADO LÓGICO) - VERSIÓN MEJORADA
    # ============================================
    def eliminar_categoria(self, id_categoria: int):
        """
        Elimina una categoría de forma LÓGICA (marca eliminado=True).
        Valida que NO tenga contenidos ni subcategorías activas.
        """

        # 🔥 CRÍTICO: Verificar contenidos ACTIVOS (no eliminados)
        contenidos_activos = (
            self.db.query(UnidadContenido)
            .filter(
                UnidadContenido.id_categoria == id_categoria,
                UnidadContenido.eliminado == False  # 👈 DEBE ESTAR ESTO
            )
            .count()
        )

        if contenidos_activos > 0:
            raise ValidationException(
                f"No se puede eliminar la categoría porque tiene {contenidos_activos} "
                f"contenido(s) activo(s) asociado(s). Primero debes eliminar o mover los contenidos."
            )


        # 🔥 CRÍTICO: Verificar subcategorías ACTIVAS (no eliminadas)
        subcategorias_activas = (
            self.db.query(Categoria)
            .filter(
                Categoria.id_categoria_padre == id_categoria,
                Categoria.eliminado == False  # ✅ SOLO subcategorías NO eliminadas
            )
            .count()
        )

        if subcategorias_activas > 0:
            # ✅ Mensaje más claro
            raise ValidationException(
                f"No se puede eliminar la categoría porque tiene {subcategorias_activas} "
                f"subcategoría(s) activa(s) asociada(s). Primero debes eliminar o mover las subcategorías."
            )

        # ✅ ELIMINADO LÓGICO: usar método del repositorio
        return self.repo.soft_delete(id_categoria)

    # ============================================
    # 🔹 NUEVO: Restaurar categoría eliminada
    # ============================================
    def restaurar_categoria(self, id_categoria: int):
        """
        Restaura una categoría que fue eliminada lógicamente.
        """
        return self.repo.restore(id_categoria)
    
    # ============================================
    # 🔹 NUEVO: Obtener estadísticas de una categoría
    # ============================================
    def obtener_estadisticas_categoria(self, id_categoria: int) -> dict:
        """
        Obtiene estadísticas completas de una categoría:
        - Contenidos activos
        - Contenidos eliminados
        - Subcategorías activas
        - Subcategorías eliminadas
        """
        contenidos_activos = (
            self.db.query(UnidadContenido)
            .filter(
                UnidadContenido.id_categoria == id_categoria,
                UnidadContenido.eliminado == False
            )
            .count()
        )
        
        contenidos_eliminados = (
            self.db.query(UnidadContenido)
            .filter(
                UnidadContenido.id_categoria == id_categoria,
                UnidadContenido.eliminado == True
            )
            .count()
        )
        
        subcategorias_activas = (
            self.db.query(Categoria)
            .filter(
                Categoria.id_categoria_padre == id_categoria,
                Categoria.eliminado == False
            )
            .count()
        )
        
        subcategorias_eliminadas = (
            self.db.query(Categoria)
            .filter(
                Categoria.id_categoria_padre == id_categoria,
                Categoria.eliminado == True
            )
            .count()
        )
        
        return {
            "contenidos": {
                "activos": contenidos_activos,
                "eliminados": contenidos_eliminados,
                "total": contenidos_activos + contenidos_eliminados
            },
            "subcategorias": {
                "activas": subcategorias_activas,
                "eliminadas": subcategorias_eliminadas,
                "total": subcategorias_activas + subcategorias_eliminadas
            },
            "puede_eliminarse": contenidos_activos == 0 and subcategorias_activas == 0
        }