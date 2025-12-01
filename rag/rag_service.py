# app/rag/rag_service.py
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer, CrossEncoder
from models.unidad_contenido import UnidadContenido
from models.categoria import Categoria
from rag.chroma_config import ChromaDBConfig
from config.redis_config import get_redis_client
import uuid
import json
import hashlib

class RAGService:
    def __init__(self, db: Session, use_cache: bool = True):
        self.db = db
        self.chroma = ChromaDBConfig()
        
        # Modelos de IA
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        
        # 🔥 Redis cache
        self.use_cache = use_cache
        self.redis = None
        self._cache_ttl_seconds = 3600  # 1 hora
        
        # 🔥 NUEVO: Cache de embeddings en memoria
        self._embedding_cache = {}
        self._max_cache_size = 1000  # Máximo 1000 embeddings en memoria
        
        if self.use_cache:
            try:
                self.redis = get_redis_client()
            except Exception as e:
                print(f"⚠️  Redis no disponible, funcionando sin caché: {e}")
                self.use_cache = False

    def _get_cache_key(self, id_agente: int, query: str, n_results: int, use_reranking: bool) -> str:
        """Genera clave única para caché"""
        data = f"rag:{id_agente}:{query}:{n_results}:{use_reranking}"
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

    # 🔥 NUEVO: Cache de embeddings en memoria
    def _get_cached_embedding(self, text: str):
        """
        Obtiene embedding del cache en memoria o lo genera
        """
        # Usar hash del texto como key
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        if text_hash not in self._embedding_cache:
            # Generar embedding
            embedding = self.embedder.encode([text])[0].tolist()
            
            # Guardar en cache
            self._embedding_cache[text_hash] = embedding
            
            # 🔥 Limitar tamaño del cache (FIFO simple)
            if len(self._embedding_cache) > self._max_cache_size:
                # Eliminar el primer elemento
                first_key = next(iter(self._embedding_cache))
                del self._embedding_cache[first_key]
        
        return self._embedding_cache[text_hash]

    def search(
        self, 
        id_agente: int, 
        query: str, 
        n_results: int = 3,  # 🔥 CAMBIO: Reducir de 3 a 2
        use_reranking: bool = False,  # 🔥 CAMBIO: Desactivar por defecto
        use_priority_boost: bool = True,
        priority_boost_factor: float = 0.05
    ) -> List[Dict]:
        """
        Busca documentos relevantes con caché Redis y boost de prioridad
        """
        # Verificar caché primero
        cache_key = self._get_cache_key(id_agente, query, n_results, use_reranking)
        cached_results = self._get_from_cache(cache_key)
        
        if cached_results is not None:
            print(f"✅ Cache HIT: '{query[:50]}...'")
            return cached_results
        
        print(f"❌ Cache MISS: '{query[:50]}...' - Buscando...")
        
        # Búsqueda en ChromaDB
        collection = self.create_collection_if_missing(id_agente)
        
        # 🔥 CAMBIO: Usar embedding cacheado
        q_emb = self._get_cached_embedding(query)
        
        # Traer más candidatos si vamos a re-rankear
        initial_results = n_results * 3 if use_reranking else n_results
        res = collection.query(query_embeddings=[q_emb], n_results=initial_results)
        
        if not res:
            return []
        
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        ids = res.get("ids", [[]])[0]
        distances = res.get("distances", [[]])[0]
        
        if not docs:
            return []
        
        # Re-ranking con CrossEncoder
        if use_reranking and len(docs) > 0:
            print(f"🔄 Re-rankeando {len(docs)} documentos...")
            
            pairs = [[query, doc] for doc in docs]
            scores = self.reranker.predict(pairs)
            
            # 🔥 APLICAR BOOST DE PRIORIDAD
            if use_priority_boost:
                boosted_scores = []
                for i, score in enumerate(scores):
                    prioridad = metas[i].get("prioridad", 5)
                    boost = prioridad * priority_boost_factor
                    boosted_score = score + boost
                    boosted_scores.append(boosted_score)
                    
                    if i < 3:
                        print(f"  Doc {i+1}: score={score:.3f} + boost={boost:.3f} = {boosted_score:.3f} (prioridad={prioridad})")
                
                scores = boosted_scores
            
            # Ordenar por score final
            ranked_indices = sorted(
                range(len(scores)), 
                key=lambda i: scores[i], 
                reverse=True
            )
            
            ranked_indices = ranked_indices[:n_results]
            
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
        else:
            # Sin re-ranking, usar distancias de ChromaDB
            results = []
            for i in range(min(len(docs), n_results)):
                # Convertir distancia a score
                base_score = 1 / (1 + distances[i])
                
                # Aplicar boost de prioridad
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
            
            # Ordenar por score final
            results.sort(key=lambda x: x["score"], reverse=True)
        
        # Guardar en caché
        self._save_to_cache(cache_key, results)
        
        return results

    # 🔥 NUEVO: Limpiar cache de embeddings
    def clear_embedding_cache(self):
        """Limpia el cache de embeddings en memoria"""
        self._embedding_cache.clear()
        print("🗑️  Cache de embeddings limpiado")
        
    def clear_cache(self, id_agente: Optional[int] = None):
        """
        Limpia el caché de Redis
        """
        if not self.use_cache or not self.redis:
            print("⚠️  Caché no está habilitado")
            return
        
        try:
            if id_agente is None:
                # Limpiar todo el caché RAG
                keys = self.redis.keys("rag:*")
                if keys:
                    self.redis.delete(*keys)
                    print(f"🗑️  {len(keys)} entradas de caché limpiadas")
                else:
                    print("ℹ️  No hay entradas en caché")
            else:
                # Limpiar solo un agente específico
                pattern = f"rag:{id_agente}:*"
                keys = self.redis.keys(pattern)
                if keys:
                    self.redis.delete(*keys)
                    print(f"🗑️  {len(keys)} entradas del agente {id_agente} limpiadas")
                else:
                    print(f"ℹ️  No hay caché para el agente {id_agente}")
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

    # ========== Resto de métodos sin cambios ==========
    
    def _collection_name(self, id_agente: int) -> str:
        return f"agente_{id_agente}"

    def create_collection_if_missing(self, id_agente: int):
        name = self._collection_name(id_agente)
        return self.chroma.get_or_create_collection(name)

    def ingest_unidad(self, unidad: UnidadContenido, categoria: Categoria):
        """Indexa UNA unidad de contenido"""
        id_agente = categoria.id_agente
        collection = self.create_collection_if_missing(id_agente)

        doc_text = self._format_document(unidad, categoria)
        
        # 🔥 CAMBIO: Usar embedding cacheado
        emb = self._get_cached_embedding(doc_text)
        doc_id = f"unidad_{unidad.id_contenido}"

        collection.upsert(
            ids=[doc_id],
            documents=[doc_text],
            embeddings=[emb],
            metadatas=[{
                "tipo": "unidad_contenido",
                "id_contenido": unidad.id_contenido,
                "id_categoria": unidad.id_categoria,
                "titulo": unidad.titulo,
                "prioridad": unidad.prioridad
            }]
        )
        
        self.clear_cache(id_agente)
        
        return {"ok": True, "id": doc_id}

    def ingest_categoria(self, categoria: Categoria):
        """Indexa una categoría"""
        id_agente = categoria.id_agente
        collection = self.create_collection_if_missing(id_agente)

        text = f"Categoria: {categoria.nombre}\nDescripcion: {categoria.descripcion or ''}"
        
        # 🔥 CAMBIO: Usar embedding cacheado
        emb = self._get_cached_embedding(text)
        doc_id = f"categoria_{categoria.id_categoria}"

        collection.upsert(
            ids=[doc_id],
            documents=[text],
            embeddings=[emb],
            metadatas=[{
                "tipo": "categoria",
                "id_categoria": categoria.id_categoria
            }]
        )
        
        self.clear_cache(id_agente)
        
        return {"ok": True, "id": doc_id}

    def indexar_categoria(self, categoria: Categoria):
        return self.ingest_categoria(categoria)

    def reindex_agent(self, id_agente: int) -> Dict:
        """Re-indexa TODO el contenido de un agente"""
        
        print(f"🔄 Limpiando caché del agente {id_agente}...")
        self.clear_cache(id_agente)
        
        collection = self.create_collection_if_missing(id_agente)

        # Borrar colección y recrear
        try:
            self.chroma.client.delete_collection(name=collection.name)
        except Exception:
            pass
        collection = self.create_collection_if_missing(id_agente)

        # Obtener categorías y unidades
        categorias = self.db.query(Categoria).filter(
            Categoria.id_agente == id_agente,
            Categoria.activo == True
        ).all()

        docs = []
        embeddings = []
        metadatas = []
        ids = []

        for cat in categorias:
            text_cat = f"Categoria: {cat.nombre}\nDescripcion: {cat.descripcion or ''}"
            docs.append(text_cat)
            metadatas.append({
                "tipo": "categoria", 
                "id_categoria": cat.id_categoria,
                "prioridad": 5
            })
            ids.append(str(uuid.uuid4()))

            unidades = self.db.query(UnidadContenido).filter(
                UnidadContenido.id_categoria == cat.id_categoria,
                UnidadContenido.estado.in_(["publicado", "activo"])
            ).all()

            for u in unidades:
                doc_text = self._format_document(u, cat)
                docs.append(doc_text)
                metadatas.append({
                    "tipo": "unidad_contenido",
                    "id_contenido": u.id_contenido,
                    "id_categoria": u.id_categoria,
                    "titulo": u.titulo,
                    "prioridad": u.prioridad
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

        return {
            "ok": True, 
            "total_docs": len(docs), 
            "collection": collection.name,
            "cache_cleared": True
        }
    
    def _format_document(self, unidad: UnidadContenido, categoria: Categoria) -> str:
        title = unidad.titulo or ""
        resumen = getattr(unidad, "resumen", "") or ""
        contenido = unidad.contenido or ""
        keywords = getattr(unidad, "palabras_clave", "") or ""
        path = self._build_categoria_path(categoria)

        parts = [
            f"CategoriaPath: {path}",
            f"Titulo: {title}",
            f"Resumen: {resumen}",
            f"Contenido: {contenido}",
            f"PalabrasClave: {keywords}",
        ]
        return "\n\n".join([p for p in parts if p])

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