# app/services/agent_classifier.py
from rag.chroma_config import ChromaDBConfig
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from models.agente_virtual import AgenteVirtual

class AgentClassifier:
    """
    Clase que mantiene una colección 'agents_index' con embeddings de
    descripciones/personas de cada agente para clasificar la pregunta.
    """

    def __init__(self, db: Session):
        self.db = db
        self.chroma = ChromaDBConfig()
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        self.index_name = "agents_index"
        # crear colección si falta
        self.collection = self.chroma.get_or_create_collection(self.index_name)

    def build_index(self):
        agentes = self.db.query(AgenteVirtual).filter(AgenteVirtual.activo==True).all()
        docs = []
        metas = []
        ids = []
        for a in agentes:
            text = f"{a.nombre_agente}. Area: {a.area_especialidad or ''}. Descripcion: {a.descripcion or ''}"
            docs.append(text)
            metas.append({"id_agente": a.id_agente})
            ids.append(f"agent_{a.id_agente}")
        if docs:
            embeddings = self.embedder.encode(docs).tolist()
            # replace whole collection (delete+create would be simpler depending on chroma)
            try:
                self.chroma.client.delete_collection(self.index_name)
            except Exception:
                pass
            self.collection = self.chroma.get_or_create_collection(self.index_name)
            self.collection.add(documents=docs, embeddings=embeddings, metadatas=metas, ids=ids)
        return {"ok": True, "total": len(docs)}

    def classify(self, pregunta: str, top_k: int = 1):
        q_emb = self.embedder.encode([pregunta]).tolist()[0]
        res = self.collection.query(query_embeddings=[q_emb], n_results=top_k)
        ids = res.get("ids", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        if not metas:
            return None
        return metas[0]["id_agente"]
