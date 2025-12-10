# app/services/unidad_contenido_service.py

from exceptions.base import ValidationException, NotFoundException
from typing import Optional, List
from datetime import date
from sqlalchemy.orm import Session
from repositories.unidad_contenido_repo import (
    UnidadContenidoRepository,
    UnidadContenidoCreate,
    UnidadContenidoUpdate
)
from rag.rag_service import RAGService
from models.usuario import Usuario
from models.categoria import Categoria  # ✅ Importar al inicio

class UnidadContenidoService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UnidadContenidoRepository(db)
        self.rag = RAGService(db)

    def _validar_usuario(self, id_usuario: Optional[int]) -> Optional[int]:
        """Valida si el usuario existe, retorna None si no existe"""
        if id_usuario is None:
            return None
        
        usuario = self.db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
        return id_usuario if usuario else None

    def _validar_fechas_vigencia(self, fecha_inicio: Optional[date], fecha_fin: Optional[date]):
        """Valida que las fechas de vigencia sean coherentes"""
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise ValidationException(
                "La fecha de fin de vigencia no puede ser anterior a la fecha de inicio"
            )

    def _indexar_en_rag(self, contenido):
        """Indexa el contenido en RAG de forma segura"""
        try:
            categoria = self.db.query(Categoria).filter(
                Categoria.id_categoria == contenido.id_categoria
            ).first()
            
            if categoria:
                self.rag.ingest_unidad(contenido, categoria)
            else:
                print(f"⚠️ Categoría {contenido.id_categoria} no encontrada para indexar")
        except Exception as e:
            print(f"⚠️ Error al indexar en RAG: {str(e)}")
            # No fallar la operación principal si RAG falla

    def crear_contenido(self, data: UnidadContenidoCreate, creado_por: Optional[int] = None):
        """Crea un nuevo contenido e indexa en RAG"""
        # Validaciones
        if len(data.contenido) < 50:
            raise ValidationException("El contenido debe tener al menos 50 caracteres")
        
        self._validar_fechas_vigencia(data.fecha_vigencia_inicio, data.fecha_vigencia_fin)
        
        # Validar usuario
        creado_por = self._validar_usuario(creado_por)
        
        # Crear contenido
        contenido = self.repo.create(data, creado_por)
        
        # Indexar en RAG (no falla si hay error)
        self._indexar_en_rag(contenido)
        
        return contenido
    
    def obtener_por_id(self, id_contenido: int):
        """Obtiene un contenido por ID"""
        contenido = self.repo.get_by_id(id_contenido)
        if not contenido:
            raise NotFoundException(f"Contenido {id_contenido} no encontrado")
        return contenido
    
    def listar_por_agente(
        self, 
        id_agente: int, 
        estado: Optional[str] = None, 
        skip: int = 0, 
        limit: int = 100
    ):
        """Lista contenidos de un agente con filtros"""
        return self.repo.get_by_agente(id_agente, estado, skip, limit)
    
    def listar_todos(
        self,
        skip: int = 0,
        limit: int = 100,
        estado: Optional[str] = None,
        id_agente: Optional[int] = None,
        id_categoria: Optional[int] = None,
        id_departamento: Optional[int] = None
    ):
        """Lista todos los contenidos con filtros opcionales"""
        return self.repo.get_all(
            skip=skip,
            limit=limit,
            estado=estado,
            id_agente=id_agente,
            id_categoria=id_categoria,
            id_departamento=id_departamento
        )
    
    def actualizar_contenido(
        self, 
        id_contenido: int, 
        data: UnidadContenidoUpdate, 
        actualizado_por: Optional[int] = None
    ):
        """Actualiza un contenido y reindexÃ¡ en RAG"""
        # Validar fechas si se están actualizando
        if data.fecha_vigencia_inicio or data.fecha_vigencia_fin:
            contenido_actual = self.obtener_por_id(id_contenido)
            inicio = data.fecha_vigencia_inicio or contenido_actual.fecha_vigencia_inicio
            fin = data.fecha_vigencia_fin or contenido_actual.fecha_vigencia_fin
            self._validar_fechas_vigencia(inicio, fin)
        
        # Validar contenido mínimo si se está actualizando
        if data.contenido and len(data.contenido) < 50:
            raise ValidationException("El contenido debe tener al menos 50 caracteres")
        
        # Validar usuario
        actualizado_por = self._validar_usuario(actualizado_por)
        
        # Actualizar contenido
        contenido = self.repo.update(id_contenido, data, actualizado_por)
        
        # Reindexar en RAG
        self._indexar_en_rag(contenido)
        
        return contenido
    
    def publicar_contenido(self, id_contenido: int, publicado_por: Optional[int] = None):
        """Publica un contenido (cambia estado a 'activo')"""
        publicado_por = self._validar_usuario(publicado_por)
        return self.repo.publicar(id_contenido, publicado_por)
    
    def cambiar_estado(
        self, 
        id_contenido: int, 
        nuevo_estado: str, 
        actualizado_por: Optional[int] = None
    ):
        """Cambia el estado de un contenido"""
        estados_validos = ["borrador", "revision", "activo", "inactivo", "archivado"]
        if nuevo_estado not in estados_validos:
            raise ValidationException(f"Estado '{nuevo_estado}' no válido")
        
        actualizado_por = self._validar_usuario(actualizado_por)
        
        data = UnidadContenidoUpdate(estado=nuevo_estado)
        return self.repo.update(id_contenido, data, actualizado_por)

    def eliminar_contenido(self, id_contenido: int) -> dict:
        """Elimina contenido de BD y ChromaDB"""
        # 1. Obtener el contenido antes de eliminar
        contenido = self.obtener_por_id(id_contenido)
        id_agente = contenido.id_agente
        
        # 2. Eliminar de ChromaDB primero
        try:
            rag_result = self.rag.delete_unidad(id_contenido, id_agente)
            rag_deleted = rag_result.get("ok", False)
        except Exception as e:
            print(f"⚠️ Error al eliminar de ChromaDB: {str(e)}")
            rag_deleted = False
        
        # 3. Eliminar de la base de datos
        db_result = self.repo.delete(id_contenido)
        
        return {
            "ok": True,
            "id_contenido": id_contenido,
            "deleted_from_chromadb": rag_deleted,
            "deleted_from_database": db_result
        }
    
    def buscar_contenidos(self, termino: str, id_agente: Optional[int] = None):
        """Busca contenidos por término"""
        return self.repo.search(termino, id_agente)
    
    def obtener_estadisticas(self, id_agente: Optional[int] = None):
        """Obtiene estadísticas de contenidos"""
        return self.repo.get_statistics(id_agente)