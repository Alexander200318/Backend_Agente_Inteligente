# app/rag/rag_service.py
from typing import List, Dict
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer
from models.unidad_contenido import UnidadContenido
from models.categoria import Categoria
from models.agente_virtual import AgenteVirtual
from rag.chroma_config import ChromaDBConfig
import uuid

class RAGService:
    def __init__(self, db: Session):
        self.db = db
        self.chroma = ChromaDBConfig()
        # Modelo de embeddings (local, rápido)
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")

    def _collection_name(self, id_agente: int) -> str:
        return f"agente_{id_agente}"

    def create_collection_if_missing(self, id_agente: int):
        name = self._collection_name(id_agente)
        return self.chroma.get_or_create_collection(name)

    def ingest_unidad(self, unidad: UnidadContenido, categoria: Categoria):
        """
        Indexa UNA unidad de contenido (upsert).
        """
        id_agente = categoria.id_agente
        collection = self.create_collection_if_missing(id_agente)

        doc_text = self._format_document(unidad, categoria)
        emb = self.embedder.encode([doc_text]).tolist()[0]
        doc_id = f"unidad_{unidad.id_contenido}"

        collection.upsert(
            ids=[doc_id],
            documents=[doc_text],
            embeddings=[emb],
            metadatas=[{
                "tipo": "unidad_contenido",
                "id_contenido": unidad.id_contenido,
                "id_categoria": unidad.id_categoria,
                "titulo": unidad.titulo
            }]
        )
        return {"ok": True, "id": doc_id}

    def ingest_categoria(self, categoria: Categoria):
        id_agente = categoria.id_agente
        collection = self.create_collection_if_missing(id_agente)

        text = f"Categoria: {categoria.nombre}\nDescripcion: {categoria.descripcion or ''}"
        emb = self.embedder.encode([text]).tolist()[0]
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
        return {"ok": True, "id": doc_id}

    def reindex_agent(self, id_agente: int) -> Dict:
        """
        Re-indexa TODO el contenido de un agente: categorias + unidades.
        Útil al crear el agente o al hacer una sincronización completa.
        """
        collection = self.create_collection_if_missing(id_agente)

        # Borrado simple: eliminar colección y recrear (Chroma no tiene drop_collection en todas las versiones)
        try:
            # Try to delete collection if exists (some versions provide it)
            self.chroma.client.delete_collection(name=collection.name)
        except Exception:
            pass
        collection = self.create_collection_if_missing(id_agente)

        # Obtener categorías y unidades del agente
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
            metadatas.append({"tipo": "categoria", "id_categoria": cat.id_categoria})
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
                    "titulo": u.titulo
                })
                ids.append(str(uuid.uuid4()))

        if docs:
            embeddings = self.embedder.encode(docs).tolist()
            collection.add(documents=docs, embeddings=embeddings, metadatas=metadatas, ids=ids)

        return {"ok": True, "total_docs": len(docs), "collection": collection.name}

    def search(self, id_agente: int, query: str, n_results: int = 4) -> List[Dict]:
        collection = self.create_collection_if_missing(id_agente)
        q_emb = self.embedder.encode([query]).tolist()[0]
        res = collection.query(query_embeddings=[q_emb], n_results=n_results)
        # res: dict with keys 'ids','documents','metadatas','distances'
        if not res:
            return []
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        ids = res.get("ids", [[]])[0]
        results = []
        for i, d in enumerate(docs):
            results.append({"id": ids[i], "document": d, "metadata": metas[i]})
        return results

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
        # construye cadena padre>hijo si tu modelo tiene id_categoria_padre; si no, devuelve nombre
        path = categoria.nombre
        try:
            current = categoria
            parts = [current.nombre]
            while getattr(current, "id_categoria_padre", None):
                parent = self.db.query(Categoria).filter(Categoria.id_categoria == current.id_categoria_padre).first()
                if not parent:
                    break
                parts.insert(0, parent.nombre)
                current = parent
                if len(parts) > 10:
                    break
            return " > ".join(parts)
        except Exception:
            return categoria.nombre
