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
from models.categoria import Categoria

class UnidadContenidoService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UnidadContenidoRepository(db)
        self.rag = RAGService(db)

    def _validar_usuario(self, id_usuario: Optional[int]) -> Optional[int]:
        if id_usuario is None:
            return None
        usuario = self.db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
        return id_usuario if usuario else None

    def _validar_fechas_vigencia(self, fecha_inicio: Optional[date], fecha_fin: Optional[date]):
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise ValidationException(
                "La fecha de fin de vigencia no puede ser anterior a la fecha de inicio"
            )

    def _indexar_en_rag(self, contenido):
        try:
            categoria = self.db.query(Categoria).filter(
                Categoria.id_categoria == contenido.id_categoria
            ).first()
            
            if categoria:
                # 🔥 LOG TEMPORAL PARA DEBUG
                print(f"=" * 80)
                print(f"📝 INDEXANDO CONTENIDO:")
                print(f"   ID: {contenido.id_contenido}")
                print(f"   Título: {contenido.titulo}")
                print(f"   Estado: {contenido.estado}")  # 👈 Ver estado real
                print(f"   Eliminado: {contenido.eliminado}")
                activo_calculado = (contenido.estado in ["publicado", "activo"] and not contenido.eliminado)
                print(f"   Activo calculado: {activo_calculado}")
                print(f"=" * 80)
                
                self.rag.ingest_unidad(contenido, categoria)
            else:
                print(f"⚠️ Categoría {contenido.id_categoria} no encontrada para indexar")
        except Exception as e:
            print(f"⚠️ Error al indexar en RAG: {str(e)}")

    def crear_contenido(self, data: UnidadContenidoCreate, creado_por: Optional[int] = None):
        if len(data.contenido) < 50:
            raise ValidationException("El contenido debe tener al menos 50 caracteres")
        
        self._validar_fechas_vigencia(data.fecha_vigencia_inicio, data.fecha_vigencia_fin)
        creado_por = self._validar_usuario(creado_por)
        contenido = self.repo.create(data, creado_por)
        self._indexar_en_rag(contenido)
        return contenido
    
    def obtener_por_id(self, id_contenido: int, include_deleted: bool = False):
        contenido = self.repo.get_by_id(id_contenido, include_deleted)
        if not contenido:
            raise NotFoundException(f"Contenido {id_contenido} no encontrado")
        return contenido
    
    def listar_por_agente(
        self, 
        id_agente: int, 
        estado: Optional[str] = None, 
        skip: int = 0, 
        limit: int = 100,
        include_deleted: bool = False
    ):
        return self.repo.get_by_agente(id_agente, estado, skip, limit, include_deleted)
    
    def listar_todos(
        self,
        skip: int = 0,
        limit: int = 100,
        estado: Optional[str] = None,
        id_agente: Optional[int] = None,
        id_categoria: Optional[int] = None,
        id_departamento: Optional[int] = None,
        include_deleted: bool = False
    ):
        return self.repo.get_all(
            skip=skip,
            limit=limit,
            estado=estado,
            id_agente=id_agente,
            id_categoria=id_categoria,
            id_departamento=id_departamento,
            include_deleted=include_deleted
        )
    
    def actualizar_contenido(
        self, 
        id_contenido: int, 
        data: UnidadContenidoUpdate, 
        actualizado_por: Optional[int] = None
    ):
        if data.fecha_vigencia_inicio or data.fecha_vigencia_fin:
            contenido_actual = self.obtener_por_id(id_contenido)
            inicio = data.fecha_vigencia_inicio or contenido_actual.fecha_vigencia_inicio
            fin = data.fecha_vigencia_fin or contenido_actual.fecha_vigencia_fin
            self._validar_fechas_vigencia(inicio, fin)
        
        if data.contenido and len(data.contenido) < 50:
            raise ValidationException("El contenido debe tener al menos 50 caracteres")
        
        actualizado_por = self._validar_usuario(actualizado_por)
        contenido = self.repo.update(id_contenido, data, actualizado_por)
        self.db.commit()
        
        id_agente = contenido.id_agente
        
        # 🔥 NUEVA instancia de RAGService después del commit
        rag_fresh = RAGService(self.db)
        rag_fresh.clear_cache(id_agente)
        
        try:
            resultado = rag_fresh.reindex_agent(id_agente)
            print(f"✅ Agente {id_agente} reindexado: {resultado.get('total_docs')} docs")
        except Exception as e:
            print(f"⚠️ Error reindexando: {e}")
        
        return contenido
    
    def publicar_contenido(self, id_contenido: int, publicado_por: Optional[int] = None):
        publicado_por = self._validar_usuario(publicado_por)
        return self.repo.publicar(id_contenido, publicado_por)
    
    def cambiar_estado(
        self, 
        id_contenido: int, 
        nuevo_estado: str, 
        actualizado_por: Optional[int] = None
    ):
        estados_validos = ["borrador", "revision", "activo", "inactivo", "archivado"]
        if nuevo_estado not in estados_validos:
            raise ValidationException(f"Estado '{nuevo_estado}' no válido")
        
        actualizado_por = self._validar_usuario(actualizado_por)
        data = UnidadContenidoUpdate(estado=nuevo_estado)
        contenido = self.repo.update(id_contenido, data, actualizado_por)
        self.db.commit()
        
        id_agente = contenido.id_agente
        
        # 🔥 NUEVA instancia de RAGService después del commit
        rag_fresh = RAGService(self.db)
        rag_fresh.clear_cache(id_agente)
        
        try:
            resultado = rag_fresh.reindex_agent(id_agente)
            print(f"✅ Agente {id_agente} reindexado: {resultado.get('total_docs')} docs")
        except Exception as e:
            print(f"⚠️ Error reindexando: {e}")
        
        return contenido

    def eliminar_contenido(
        self, 
        id_contenido: int,
        eliminado_por: Optional[int] = None,
        hard_delete: bool = False
    ) -> dict:
        contenido = self.obtener_por_id(id_contenido)
        id_agente = contenido.id_agente
        
        if hard_delete:
            try:
                rag_result = self.rag.delete_unidad(id_contenido, id_agente)
                rag_deleted = rag_result.get("ok", False)
            except Exception as e:
                print(f"⚠️ Error al eliminar de ChromaDB: {str(e)}")
                rag_deleted = False
        else:
            rag_deleted = None
        
        eliminado_por = self._validar_usuario(eliminado_por)
        db_result = self.repo.delete(id_contenido, eliminado_por, hard_delete)
        
        return {
            "ok": True,
            "id_contenido": id_contenido,
            "tipo_eliminacion": "fisica" if hard_delete else "logica",
            "deleted_from_chromadb": rag_deleted,
            "deleted_from_database": db_result
        }
    
    def buscar_contenidos(self, termino: str, id_agente: Optional[int] = None):
        return self.repo.search(termino, id_agente)
    
    def obtener_estadisticas(self, id_agente: Optional[int] = None):
        return self.repo.get_statistics(id_agente)
    
    def restaurar_contenido(self, id_contenido: int):
        return self.repo.restore(id_contenido)
    
    def actualizar_vigencias_masivo(self, id_agente: Optional[int] = None):
        """
        Actualiza el estado de todos los contenidos según sus fechas de vigencia
        """
        return self.repo.actualizar_vigencias_masivo(id_agente)
    

    def desactivar_contenido(self, id_contenido: int) -> dict:
        """
        Desactiva una unidad de contenido específica
        """
        contenido = self.obtener_por_id(id_contenido)
        id_agente = contenido.id_agente
        
        contenido.estado = "inactivo"
        self.db.commit()
        
        # 🔥 NUEVA instancia de RAGService después del commit
        rag_fresh = RAGService(self.db)
        rag_fresh.clear_cache(id_agente)
        
        try:
            resultado = rag_fresh.reindex_agent(id_agente)
            resultado_rag = {
                "ok": True,
                "reindexado": True,
                "total_docs": resultado.get("total_docs")
            }
        except Exception as e:
            print(f"⚠️ Error reindexando: {e}")
            resultado_rag = {"ok": False, "error": str(e)}
        
        return {
            "ok": True,
            "id_contenido": id_contenido,
            "titulo": contenido.titulo,
            "estado": "inactivo",
            "chromadb": resultado_rag
        }


    def activar_contenido(self, id_contenido: int) -> dict:
        """
        Activa una unidad de contenido específica
        """
        contenido = self.obtener_por_id(id_contenido)
        id_agente = contenido.id_agente
        
        contenido.estado = "activo"
        self.db.commit()
        
        # 🔥 NUEVA instancia de RAGService después del commit
        rag_fresh = RAGService(self.db)
        rag_fresh.clear_cache(id_agente)
        
        try:
            resultado = rag_fresh.reindex_agent(id_agente)
            resultado_rag = {
                "ok": True,
                "reindexado": True,
                "total_docs": resultado.get("total_docs")
            }
        except Exception as e:
            print(f"⚠️ Error reindexando: {e}")
            resultado_rag = {"ok": False, "error": str(e)}
        
        return {
            "ok": True,
            "id_contenido": id_contenido,
            "titulo": contenido.titulo,
            "estado": "activo",
            "chromadb": resultado_rag
        }
