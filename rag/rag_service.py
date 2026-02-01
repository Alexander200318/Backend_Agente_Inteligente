# app/rag/rag_service.py
import os
# Permitir descargar modelos si no están disponibles localmente
os.environ["HF_HUB_OFFLINE"] = "0"  
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer, CrossEncoder
from models.unidad_contenido import UnidadContenido
from models.categoria import Categoria
from rag.chroma_config import ChromaDBConfig
from config.redis_config import get_redis_client
from pathlib import Path   # 🔥 NUEVO
import uuid
import json
import hashlib
import torch
import traceback
import logging

logger = logging.getLogger(__name__)


class RAGService:
    # 🔥 Variables de clase compartidas (singleton pattern)
    _embedder = None
    _reranker = None
    _models_loaded = False
    
    def __init__(self, db: Session, use_cache: bool = True):
        self.db = db
        self.chroma = ChromaDBConfig()
        self._rag_available = True  # 🔥 Bandera para saber si RAG está disponible

        # 🔥 Ruta fija a los modelos locales (los que descargaste con download_hf_models.py)
        BASE_DIR = Path(__file__).resolve().parent.parent   # .../Backend_Agente_Inteligente
        HF_MODELS_DIR = BASE_DIR / "hf_models"
        EMBEDDER_PATH = HF_MODELS_DIR / "all-MiniLM-L6-v2"
        RERANKER_PATH = HF_MODELS_DIR / "ms-marco-MiniLM-L-6-v2"

        print(f"\n🚀🚀🚀 INIT RAG SERVICE START 🚀🚀🚀")
        print(f"   BASE_DIR: {BASE_DIR}")
        print(f"   EMBEDDER_PATH: {EMBEDDER_PATH}")
        print(f"   EMBEDDER EXISTS: {EMBEDDER_PATH.exists()}")
        print(f"   _models_loaded: {RAGService._models_loaded}")

        # 🔥 Cargar modelos SOLO una vez
        if not RAGService._models_loaded:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            print(f"🚀 Inicializando modelos RAG (solo primera vez) en device: {device}")

            # 🔥 CAMBIO: Usar modelos desde HuggingFace cache (offline)
            # El environment variable HF_HUB_OFFLINE=1 ya está configurado
            # Así que SentenceTransformer intentará cargar desde cache
            
            # ====== EMBEDDER ======
            try:
                # Primero intentar desde ruta local
                if EMBEDDER_PATH.exists():
                    print(f"📦 Cargando embedder desde ruta local: {EMBEDDER_PATH}")
                    RAGService._embedder = SentenceTransformer(str(EMBEDDER_PATH), device=device)
                    print("✅ Embedder cargado exitosamente desde ruta local.")
                else:
                    print(f"📦 Ruta local no existe, intentando descargar desde HuggingFace...")
                    # Desactivar modo offline para descargar
                    os.environ["HF_HUB_OFFLINE"] = "0"
                    RAGService._embedder = SentenceTransformer("all-MiniLM-L6-v2", device=device)
                    # Guardar localmente para futuras ocasiones
                    RAGService._embedder.save(str(EMBEDDER_PATH))
                    os.environ["HF_HUB_OFFLINE"] = "1"
                    print("✅ Embedder descargado y guardado.")
            except Exception as e:
                print(f"❌ Error cargando embedder: {e}")
                RAGService._embedder = None
                self._rag_available = False

            # ====== RERANKER ======
            try:
                # Primero intentar desde ruta local
                if RERANKER_PATH.exists():
                    print(f"📦 Cargando reranker desde ruta local: {RERANKER_PATH}")
                    RAGService._reranker = CrossEncoder(str(RERANKER_PATH), device=device)
                    print("✅ Reranker cargado exitosamente desde ruta local.")
                else:
                    print(f"📦 Ruta local no existe, intentando descargar desde HuggingFace...")
                    # Desactivar modo offline para descargar
                    os.environ["HF_HUB_OFFLINE"] = "0"
                    RAGService._reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", device=device)
                    # Guardar localmente para futuras ocasiones
                    RAGService._reranker.save(str(RERANKER_PATH))
                    os.environ["HF_HUB_OFFLINE"] = "1"
                    print("✅ Reranker descargado y guardado.")
            except Exception as e:
                print(f"❌ Error cargando reranker: {e}")
                RAGService._reranker = None
                self._rag_available = False

            RAGService._models_loaded = True
            
            # 🔥 Verificar si los modelos se cargaron correctamente
            if RAGService._embedder and RAGService._reranker:
                print("✅✅✅ ¡Todos los modelos cargados exitosamente! ✅✅✅")
            else:
                print("❌❌❌ FALLO: No se pudieron cargar todos los modelos ❌❌❌")
                print(f"   _embedder is None: {RAGService._embedder is None}")
                print(f"   _reranker is None: {RAGService._reranker is None}")

        # Usar las instancias compartidas de clase
        self.embedder = RAGService._embedder
        self.reranker = RAGService._reranker
        
        print(f"   embedder after assignment: {self.embedder is not None}")
        print(f"🚀🚀🚀 INIT RAG SERVICE END 🚀🚀🚀\n")
        
        # 🔥 Redis cache
        self.use_cache = use_cache
        self.redis = None
        self._cache_ttl_seconds = 3600  # 1 hora
        
        # 🔥 Cache de embeddings en memoria
        self._embedding_cache = {}
        self._max_cache_size = 1000  # Máximo 1000 embeddings en memoria
        
        if self.use_cache:
            try:
                self.redis = get_redis_client()
            except Exception as e:
                print(f"⚠️  Redis no disponible, funcionando sin caché: {e}")
                self.use_cache = False  # solo desactivar si falla

    def _get_cache_key(self, id_agente, query, n_results, use_reranking, session_id=None):
        session_part = f":{session_id}" if session_id else ""
        data = f"rag:{id_agente}{session_part}:{query}:{n_results}:{use_reranking}"
        return hashlib.md5(data.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[List[Dict]]:
        """Obtiene resultado del caché"""
        if not self.use_cache or not self.redis:
            return None
        
        try:
            cached = self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            print(f"⚠️  Error leyendo caché: {e}")
        
        return None

    def _save_to_cache(self, cache_key: str, results: List[Dict]):
        """Guarda resultado en caché"""
        if not self.use_cache or not self.redis:
            return
        
        try:
            self.redis.setex(
                cache_key,
                self._cache_ttl_seconds,
                json.dumps(results)
            )
        except Exception as e:
            print(f"⚠️  Error guardando en caché: {e}")

    # 🔥 Cache de embeddings en memoria
    def _get_cached_embedding(self, text: str, session_id: Optional[str] = None):
        """
        Obtiene embedding del cache en memoria o lo genera
        """
        # 🔥 Si RAG no está disponible, retornar un vector dummy
        if not self.embedder:
            return [0.0] * 384  # Vector dummy de 384 dimensiones (tamaño del modelo)
            
        # Agregar session al hash SOLO si existe
        cache_key = f"{session_id}:{text}" if session_id else text
        text_hash = hashlib.md5(cache_key.encode()).hexdigest()
        
        if text_hash not in self._embedding_cache:
            embedding = self.embedder.encode([text])[0].tolist()
            self._embedding_cache[text_hash] = embedding
            
            # Limitar tamaño del cache (FIFO simple)
            if len(self._embedding_cache) > self._max_cache_size:
                first_key = next(iter(self._embedding_cache))
                del self._embedding_cache[first_key]
        
        return self._embedding_cache[text_hash]

    def search(
        self, 
        id_agente: int, 
        query: str, 
        session_id: Optional[str] = None,
        n_results: int = 3,
        use_reranking: bool = False,
        use_priority_boost: bool = True,
        priority_boost_factor: float = 0.05,
        incluir_inactivos: bool = False  # 🔥 NUEVO parámetro
    ) -> List[Dict]:
        """
        Busca documentos relevantes con caché Redis y boost de prioridad
        Si RAG no está disponible, busca en BD con FULLTEXT SEARCH
        """
        # 🔥 Si RAG no está disponible, hacer búsqueda FALLBACK en BD
        if not self.embedder:
            print(f"⚠️  RAG no disponible, usando búsqueda FALLBACK en BD...")
            return self._search_in_database(id_agente, query, n_results, incluir_inactivos)
            
        cache_key = self._get_cache_key(id_agente, query, n_results, use_reranking)
        cached_results = self._get_from_cache(cache_key)
        
        if cached_results is not None:
            print(f"✅ Cache HIT: '{query[:50]}...'")
            return cached_results
        
        print(f"❌ Cache MISS: '{query[:50]}...' - Buscando...")
        
        collection = self.create_collection_if_missing(id_agente)
        
        q_emb = self._get_cached_embedding(query, session_id)
        
        initial_results = n_results * 3 if use_reranking else n_results

        # 🔥 FILTROS con sintaxis correcta de ChromaDB
        where_filter = None

        if not incluir_inactivos:
            # Filtrar: tipo = unidad_contenido AND activo = True
            where_filter = {
                "$and": [
                    {"tipo": "unidad_contenido"},
                    {"activo": True}
                ]
            }
        else:
            # Solo filtrar por tipo (permite activos e inactivos)
            where_filter = {"tipo": "unidad_contenido"}

        res = collection.query(
            query_embeddings=[q_emb], 
            n_results=initial_results,
            where=where_filter
        )
        
        print(f"📊 ChromaDB query result: res={bool(res)}, type={type(res)}")
        if res:
            print(f"📊 res keys: {res.keys() if isinstance(res, dict) else 'N/A'}")
            print(f"📊 res['documents']: {len(res.get('documents', [[]])[0]) if isinstance(res, dict) else 'N/A'}")
        
        if not res:
            # 🔥 FALLBACK: Si ChromaDB está vacío, buscar en BD
            print(f"⚠️  ChromaDB vacío, usando búsqueda FALLBACK en BD...")
            return self._search_in_database(id_agente, query, n_results, incluir_inactivos)
        
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        ids = res.get("ids", [[]])[0]
        distances = res.get("distances", [[]])[0]
        
        if not docs:
            # 🔥 FALLBACK: Si no hay documentos en ChromaDB, buscar en BD
            print(f"⚠️  No hay documentos en ChromaDB, usando búsqueda FALLBACK en BD...")
            return self._search_in_database(id_agente, query, n_results, incluir_inactivos)
        
        if use_reranking and len(docs) > 0 and self.reranker:
            print(f"🔄 Re-rankeando {len(docs)} documentos...")
            
            pairs = [[query, doc] for doc in docs]
            scores = self.reranker.predict(pairs)
            
            if use_priority_boost:
                boosted_scores = []
                for i, score in enumerate(scores):
                    prioridad = metas[i].get("prioridad", 5)
                    boost = prioridad * priority_boost_factor
                    boosted_score = score + boost
                    boosted_scores.append(boosted_score)
                    
                    if i < 3:
                        print(
                            f"  Doc {i+1}: score={score:.3f} + boost={boost:.3f} "
                            f"= {boosted_score:.3f} (prioridad={prioridad})"
                        )
                
                scores = boosted_scores
            
            ranked_indices = sorted(
                range(len(scores)), 
                key=lambda i: scores[i], 
                reverse=True
            )[:n_results]
            
            results = []
            for idx in ranked_indices:
                results.append({
                    "id": ids[idx],
                    "document": docs[idx],
                    "metadata": metas[idx],
                    "score": float(scores[idx]),
                    "base_score": float(self.reranker.predict([[query, docs[idx]]])[0]),
                    "priority": metas[idx].get("prioridad", 5),
                    "reranked": True
                })
            
            # 🔥 NUEVO: Validar en BD en tiempo real si los documentos siguen activos
            if not incluir_inactivos:
                validated_results = []
                for result in results:
                    id_contenido = result["metadata"].get("id_contenido")
                    if id_contenido:
                        # Verificar en BD si sigue siendo activo
                        unidad = self.db.query(UnidadContenido).filter(
                            UnidadContenido.id_contenido == id_contenido
                        ).first()
                        
                        if unidad and unidad.estado in ["activo", "publicado"] and not unidad.eliminado:
                            validated_results.append(result)
                        # else: omitir documentos inactivos o eliminados
                    else:
                        # Si no tiene id_contenido, incluir (podría ser categoría u otro tipo)
                        validated_results.append(result)
                
                results = validated_results
        else:
            results = []
            for i in range(min(len(docs), n_results)):
                base_score = 1 / (1 + distances[i])
                
                if use_priority_boost:
                    prioridad = metas[i].get("prioridad", 5)
                    boost = prioridad * priority_boost_factor
                    final_score = base_score + boost
                else:
                    final_score = base_score
                
                results.append({
                    "id": ids[i],
                    "document": docs[i],
                    "metadata": metas[i],
                    "score": final_score,
                    "priority": metas[i].get("prioridad", 5),
                    "reranked": False
                })
            
            results.sort(key=lambda x: x["score"], reverse=True)
        
        # 🔥 NUEVO: Validar en BD en tiempo real si los documentos siguen activos
        if not incluir_inactivos:
            validated_results = []
            for result in results:
                id_contenido = result["metadata"].get("id_contenido")
                if id_contenido:
                    # Verificar en BD si sigue siendo activo
                    unidad = self.db.query(UnidadContenido).filter(
                        UnidadContenido.id_contenido == id_contenido
                    ).first()
                    
                    if unidad and unidad.estado in ["activo", "publicado"] and not unidad.eliminado:
                        validated_results.append(result)
                    # else: omitir documentos inactivos o eliminados
                else:
                    # Si no tiene id_contenido, incluir (podría ser categoría u otro tipo)
                    validated_results.append(result)
            
            results = validated_results
        
        self._save_to_cache(cache_key, results)
        
        return results

    def clear_embedding_cache(self):
        """Limpia el cache de embeddings en memoria"""
        self._embedding_cache.clear()
        print("🗑️  Cache de embeddings limpiado")
        
    def clear_cache(self, id_agente: Optional[int] = None, session_id: Optional[str] = None):
        """
        Limpia el caché de Redis
        """
        if not self.use_cache or not self.redis:
            print("⚠️  Caché no está habilitado")
            return
        
        try:
            # 🔥 ELIMINAR TODO EL CACHÉ cuando se llama con id_agente
            # Porque las claves son hashes MD5 sin prefijo identificable
            all_keys = self.redis.keys("*")
            
            if all_keys:
                self.redis.delete(*all_keys)
                print(f"🗑️  {len(all_keys)} entradas de caché limpiadas (TODAS)")
            else:
                print(f"ℹ️  No hay caché")
                
        except Exception as e:
            print(f"❌ Error limpiando caché: {e}")

    def get_cache_stats(self) -> Dict:
        """Obtiene estadísticas del caché"""
        stats = {
            "embedding_cache_size": len(self._embedding_cache),
            "embedding_cache_max": self._max_cache_size
        }
        
        if not self.use_cache or not self.redis:
            stats["redis_enabled"] = False
            return stats
        
        try:
            info = self.redis.info("stats")
            keys_count = len(self.redis.keys("rag:*"))
            
            stats.update({
                "redis_enabled": True,
                "redis_total_keys": keys_count,
                "redis_hits": info.get("keyspace_hits", 0),
                "redis_misses": info.get("keyspace_misses", 0),
                "redis_hit_rate": info.get("keyspace_hits", 0) / max(
                    info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1
                ) * 100
            })
        except Exception as e:
            stats["redis_error"] = str(e)
        
        return stats
    
    def _collection_name(self, id_agente: int) -> str:
        return f"agente_{id_agente}"

    def create_collection_if_missing(self, id_agente: int):
        name = self._collection_name(id_agente)
        return self.chroma.get_or_create_collection(name)



    def ingest_unidad(self, unidad: UnidadContenido, categoria: Categoria):
        """Indexa UNA unidad de contenido"""
        # 🔥 Si RAG no está disponible, simplemente retornar sin error
        if not self.embedder:
            print(f"⚠️  RAG no disponible, skipping indexing para unidad {unidad.id_contenido}")
            return {"ok": True, "id": f"unidad_{unidad.id_contenido}", "skipped": True}
            
        id_agente = categoria.id_agente
        collection = self.create_collection_if_missing(id_agente)

        doc_text = self._format_document(unidad, categoria)
        emb = self._get_cached_embedding(doc_text)
        doc_id = f"unidad_{unidad.id_contenido}"

        # 🔥 PRIMERO: Intentar eliminar vector viejo (si existe)
        try:
            collection.delete(ids=[doc_id])
            print(f"🗑️ Vector anterior eliminado: {doc_id}")
        except Exception as e:
            # No hay problema si no existe
            pass

        # 🔥 SEGUNDO: Crear nuevo vector
        collection.add(  # ← Usar add() en lugar de upsert()
            ids=[doc_id],
            documents=[doc_text],
            embeddings=[emb],
            metadatas=[{
                "tipo": "unidad_contenido",
                "id_contenido": unidad.id_contenido,
                "id_categoria": unidad.id_categoria,
                "titulo": unidad.titulo,
                "prioridad": unidad.prioridad,
                "activo": (
                    unidad.estado in ["publicado", "activo"] and
                    not unidad.eliminado
                )
            }]
        )
        
        self.clear_cache(id_agente)
        
        return {"ok": True, "id": doc_id}
    
    

    def ingest_categoria(self, categoria: Categoria):
        """Indexa una categoría"""
        id_agente = categoria.id_agente
        collection = self.create_collection_if_missing(id_agente)

        text = f"Categoria: {categoria.nombre}\nDescripcion: {categoria.descripcion or ''}"
        
        emb = self._get_cached_embedding(text)
        doc_id = f"categoria_{categoria.id_categoria}"

        collection.upsert(
            ids=[doc_id],
            documents=[text],
            embeddings=[emb],
            metadatas=[{
                "tipo": "categoria",
                "id_categoria": categoria.id_categoria,
                "activo": categoria.activo and not categoria.eliminado  # 🔥 AGREGAR ESTA LÍNEA
            }]
        )
        
        self.clear_cache(id_agente)
        
        return {"ok": True, "id": doc_id}

    def indexar_categoria(self, categoria: Categoria):
        return self.ingest_categoria(categoria)

    def reindex_agent(self, id_agente: int) -> Dict:
        """Re-indexa TODO el contenido de un agente"""
        
        # 🔥 Si RAG no está disponible, retorna silenciosamente
        if not self._rag_available or self.embedder is None:
            print(f"⚠️  RAG no disponible, skipping indexing para agente {id_agente}")
            return {"ok": False, "mensaje": "RAG no disponible"}
        
        print(f"🔄 Limpiando caché del agente {id_agente}...")
        self.clear_cache(id_agente)
        
        # 🔥 PRIMERO: Obtener categorías ACTIVAS
        categorias = self.db.query(Categoria).filter(
            Categoria.id_agente == id_agente,
            Categoria.activo == True,
            Categoria.eliminado == False  # 🔥 IMPORTANTE
        ).all()

        # 🔥 SEGUNDO: Borrar colección COMPLETA (elimina vectores viejos)
        collection_name = self._collection_name(id_agente)
        try:
            self.chroma.client.delete_collection(name=collection_name)
            print(f"🗑️  Colección {collection_name} eliminada")
        except Exception as e:
            print(f"⚠️  No había colección previa: {e}")
        
        # 🔥 TERCERO: Recrear colección vacía
        collection = self.create_collection_if_missing(id_agente)

        docs = []
        metadatas = []
        ids = []


        for cat in categorias:
            # ❌ YA NO INDEXAR LA CATEGORÍA
            # text_cat = f"Categoria: {cat.nombre}..."
            # docs.append(text_cat)
            # ...
            
            # ✅ SOLO indexar contenidos ACTIVOS de esta categoría
            unidades = self.db.query(UnidadContenido).filter(
                UnidadContenido.id_categoria == cat.id_categoria,
                UnidadContenido.estado.in_(["publicado", "activo"]),
                UnidadContenido.eliminado == False
            ).all()

            for u in unidades:
                doc_text = self._format_document(u, cat)
                docs.append(doc_text)
                metadatas.append({
                    "tipo": "unidad_contenido",
                    "id_contenido": u.id_contenido,
                    "id_categoria": u.id_categoria,
                    "titulo": u.titulo,
                    "prioridad": u.prioridad,
                    "activo": True  # 🔥 Solo contenidos activos
                })
                ids.append(str(uuid.uuid4()))

        if docs:
            embeddings = self.embedder.encode(docs).tolist()
            collection.add(
                documents=docs, 
                embeddings=embeddings, 
                metadatas=metadatas, 
                ids=ids
            )
            print(f"✅ {len(docs)} documentos indexados")
        else:
            print("⚠️  No hay documentos para indexar")

        return {
            "ok": True, 
            "total_docs": len(docs), 
            "collection": collection.name,
            "cache_cleared": True
        }
    
    def _format_document(self, unidad: UnidadContenido, categoria: Categoria) -> str:
        """
        Formatea documento con jerarquía de categorías optimizada
        """
        # 1. Construir ruta completa
        path_full = self._build_categoria_path(categoria)
        path_parts = path_full.split(" > ")
        
        # 2. Datos del documento
        title = unidad.titulo or ""
        resumen = getattr(unidad, "resumen", "") or ""
        contenido = unidad.contenido or ""
        keywords = getattr(unidad, "palabras_clave", "") or ""
        
        # 3. Construir encabezado con jerarquía enfatizada
        categoria_especifica = path_parts[-1] if path_parts else categoria.nombre
        
        header_parts = [
            f"RUTA: {path_full}",
            f"CATEGORÍA: {categoria_especifica}",
            f"TEMA: {categoria_especifica}",
            f"CLASIFICACIÓN: {categoria_especifica}",
        ]
        
        # Agregar niveles superiores si existen
        if len(path_parts) > 1:
            header_parts.append(f"ÁREA: {path_parts[0]}")
        
        if len(path_parts) > 2:
            header_parts.append(f"SECCIÓN: {path_parts[-2]}")
        
        # 4. Construir documento final
        parts = [
            *header_parts,
            "",
            f"Título: {title}",
            f"Resumen: {resumen}",
            f"Palabras clave: {keywords}",
            "",
            f"Contenido: {contenido}"
        ]
        
        return "\n".join([p for p in parts if p])

    def _build_categoria_path(self, categoria: Categoria) -> str:
        path = categoria.nombre
        try:
            current = categoria
            parts = [current.nombre]
            while getattr(current, "id_categoria_padre", None):
                parent = self.db.query(Categoria).filter(
                    Categoria.id_categoria == current.id_categoria_padre
                ).first()
                if not parent:
                    break
                parts.insert(0, parent.nombre)
                current = parent
                if len(parts) > 10:
                    break
            return " > ".join(parts)
        except Exception:
            return categoria.nombre

    def delete_unidad(self, unidad_id: int, id_agente: int):
        """
        Elimina una unidad de contenido de ChromaDB
        """
        collection = self.create_collection_if_missing(id_agente)
        doc_id = f"unidad_{unidad_id}"
        
        try:
            collection.delete(ids=[doc_id])
            self.clear_cache(id_agente)
            return {"ok": True, "id": doc_id, "deleted": True}
        except Exception as e:
            print(f"❌ Error eliminando de ChromaDB: {e}")
            return {"ok": False, "error": str(e)}
        


    def desactivar_categoria_cascada_vectores(
        self, 
        ids_categorias: List[int], 
        id_agente: int
    ) -> dict:
        """
        Desactiva vectores de categorías y sus contenidos en ChromaDB
        """
        collection = self.create_collection_if_missing(id_agente)
        
        try:
            vectores_actualizados = 0
            
            # 1. Desactivar vectores de categorías
            for id_cat in ids_categorias:
                doc_id = f"categoria_{id_cat}"
                try:
                    result = collection.get(ids=[doc_id])
                    if result and result['ids']:
                        metadata = result['metadatas'][0]
                        metadata['activo'] = False
                        
                        collection.upsert(
                            ids=[doc_id],
                            documents=result['documents'],
                            embeddings=result['embeddings'],
                            metadatas=[metadata]
                        )
                        vectores_actualizados += 1
                except Exception as e:
                    print(f"⚠️ Error desactivando categoría {id_cat}: {e}")
            
            # 2. Desactivar vectores de contenidos
            # Obtener todos los vectores del agente
            all_docs = collection.get()
            
            for i, metadata in enumerate(all_docs['metadatas']):
                if (metadata.get('tipo') == 'unidad_contenido' and 
                    metadata.get('id_categoria') in ids_categorias):
                    
                    doc_id = all_docs['ids'][i]
                    try:
                        metadata['activo'] = False
                        
                        collection.upsert(
                            ids=[doc_id],
                            documents=[all_docs['documents'][i]],
                            embeddings=[all_docs['embeddings'][i]],
                            metadatas=[metadata]
                        )
                        vectores_actualizados += 1
                    except Exception as e:
                        print(f"⚠️ Error desactivando contenido {doc_id}: {e}")
            
            # Limpiar caché
            self.clear_cache(id_agente)
            
            return {
                "ok": True,
                "vectores_actualizados": vectores_actualizados,
                "categorias_procesadas": len(ids_categorias)
            }
            
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "vectores_actualizados": 0
            }


    def activar_categoria_cascada_vectores(
        self, 
        ids_categorias: List[int], 
        id_agente: int
    ) -> dict:
        """
        Activa vectores de categorías y sus contenidos en ChromaDB
        """
        collection = self.create_collection_if_missing(id_agente)
        
        try:
            vectores_actualizados = 0
            
            # 1. Activar vectores de categorías
            for id_cat in ids_categorias:
                doc_id = f"categoria_{id_cat}"
                try:
                    result = collection.get(ids=[doc_id])
                    if result and result['ids']:
                        metadata = result['metadatas'][0]
                        metadata['activo'] = True
                        
                        collection.upsert(
                            ids=[doc_id],
                            documents=result['documents'],
                            embeddings=result['embeddings'],
                            metadatas=[metadata]
                        )
                        vectores_actualizados += 1
                except Exception as e:
                    print(f"⚠️ Error activando categoría {id_cat}: {e}")
            
            # 2. Activar vectores de contenidos
            all_docs = collection.get()
            
            for i, metadata in enumerate(all_docs['metadatas']):
                if (metadata.get('tipo') == 'unidad_contenido' and 
                    metadata.get('id_categoria') in ids_categorias):
                    
                    doc_id = all_docs['ids'][i]
                    try:
                        metadata['activo'] = True
                        
                        collection.upsert(
                            ids=[doc_id],
                            documents=[all_docs['documents'][i]],
                            embeddings=[all_docs['embeddings'][i]],
                            metadatas=[metadata]
                        )
                        vectores_actualizados += 1
                    except Exception as e:
                        print(f"⚠️ Error activando contenido {doc_id}: {e}")
            
            # Limpiar caché
            self.clear_cache(id_agente)
            
            return {
                "ok": True,
                "vectores_actualizados": vectores_actualizados,
                "categorias_procesadas": len(ids_categorias)
            }
            
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "vectores_actualizados": 0
        }

    def _search_in_database(
        self, 
        id_agente: int, 
        query: str, 
        n_results: int = 3,
        incluir_inactivos: bool = False
    ) -> List[Dict]:
        """
        Búsqueda de fallback en BD cuando RAG no está disponible.
        Usa FULLTEXT SEARCH o búsqueda por coincidencia de texto simple.
        """
        try:
            from sqlalchemy import or_, and_
            
            print(f"🔍 Buscando en BD: agente={id_agente}, query='{query[:50]}...'")
            
            # Preparar palabras clave
            keywords = query.split()
            
            # Construir condiciones de búsqueda
            search_conditions = or_(
                *[
                    or_(
                        UnidadContenido.titulo.ilike(f"%{kw}%"),
                        UnidadContenido.contenido.ilike(f"%{kw}%"),
                        UnidadContenido.resumen.ilike(f"%{kw}%")
                    )
                    for kw in keywords
                ]
            )
            
            # Filtro base
            base_filter = and_(
                UnidadContenido.id_agente == id_agente,
                search_conditions
            )
            
            # Agregar filtro de estado si es necesario
            if not incluir_inactivos:
                # Filtrar solo documentos activos no eliminados
                base_filter = and_(
                    base_filter,
                    UnidadContenido.estado == "activo",
                    UnidadContenido.eliminado == False
                )
            
            print(f"🔎 Ejecutando búsqueda con filtros...")
            # Ejecutar búsqueda
            unidades = self.db.query(UnidadContenido).filter(base_filter).limit(n_results * 2).all()
            
            print(f"📊 Encontrados {len(unidades)} documentos sin filtrar")
            
            results = []
            for unidad in unidades[:n_results]:
                results.append({
                    "id": f"db_{unidad.id_contenido}",
                    "document": unidad.contenido or unidad.titulo,
                    "metadata": {
                        "id_contenido": unidad.id_contenido,
                        "titulo": unidad.titulo,
                        "prioridad": getattr(unidad, 'prioridad', 5),
                        "tipo": "unidad_contenido",
                        "activo": str(unidad.estado) == "activo",
                        "fuente": "database_fallback"
                    },
                    "score": 0.7,  # Score fijo para búsquedas en BD
                    "priority": getattr(unidad, 'prioridad', 5),
                    "reranked": False
                })
            
            if results:
                print(f"✅ [NEW_CODE] Encontrados {len(results)} documentos en BD - version_2")
                print(f"📋 Estructura primer doc: {results[0].keys() if results else 'N/A'}")
                for r in results[:2]:
                    print(f"   - {r.get('id')}: {r.get('document', 'N/A')[:50]}...")
            else:
                print(f"❌ [NEW_CODE] No se encontraron documentos en BD para '{query}'")
            
            return results
            
        except Exception as e:
            print(f"❌ Error en búsqueda de BD: {e}")
            traceback.print_exc()
            return []
