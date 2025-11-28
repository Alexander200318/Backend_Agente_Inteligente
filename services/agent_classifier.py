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

        try:
            if self.collection.count() == 0:
                print("⚠️  agents_index vacío, construyendo índice de agentes...")
                self.build_index()
        except Exception as e:
            print("Error verificando/creando índice de agentes:", e)

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
        # Por si acaso, si está vacía, reconstruir
        try:
            if self.collection.count() == 0:
                self.build_index()
        except Exception as e:
            print("Error al contar la colección:", e)

        q_emb = self.embedder.encode([pregunta]).tolist()[0]
        res = self.collection.query(query_embeddings=[q_emb], n_results=top_k)
        metas = res.get("metadatas", [[]])[0]

        if not metas:
            return None

        return metas[0]["id_agente"]
