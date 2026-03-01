# app/services/agent_classifier.py
from rag.chroma_config import ChromaDBConfig
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from models.agente_virtual import AgenteVirtual
from pathlib import Path
import traceback

class AgentClassifier:
    """
    Clase que mantiene una colección 'agents_index' con embeddings de
    descripciones/personas de cada agente para clasificar la pregunta.
    """

    def __init__(self, db: Session):
        self.db = db
        self.chroma = ChromaDBConfig()
        
        # 🔥 Intentar cargar embedder local o desde HuggingFace
        self.embedder = self._load_embedder()
        self.index_name = "agents_index"
        # crear colección si falta
        self.collection = self.chroma.get_or_create_collection(self.index_name)

        try:
            if self.collection.count() == 0:
                print("⚠️  agents_index vacío, construyendo índice de agentes...")
                self.build_index()
        except Exception as e:
            print("Error verificando/creando índice de agentes:", e)

    def _load_embedder(self):
        """Intenta cargar embedder localmente o desde HuggingFace"""
        # Ruta local
        BASE_DIR = Path(__file__).resolve().parent.parent  # Backend_Agente_Inteligente
        HF_MODELS_DIR = BASE_DIR / "hf_models"
        EMBEDDER_PATH = HF_MODELS_DIR / "all-MiniLM-L6-v2"
        
        try:
            if EMBEDDER_PATH.exists():
                print("📦 Cargando embedder desde ruta local...")
                return SentenceTransformer(str(EMBEDDER_PATH))
        except Exception as e:
            print(f"⚠️  No se pudo cargar desde {EMBEDDER_PATH}: {e}")
        
        try:
            print("📦 Intentando cargar embedder desde HuggingFace...")
            return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        except Exception as e:
            print(f"❌ Error con HuggingFace: {e}")
            traceback.print_exc()
            return None

    def build_index(self):
        agentes = self.db.query(AgenteVirtual).filter(AgenteVirtual.activo==True).all()
        docs = []
        metas = []
        ids = []
        
        for a in agentes:
            # 🔥 NUEVO: Incluir palabras clave de los documentos del agente
            from models.unidad_contenido import UnidadContenido, EstadoContenidoEnum
            
            # Obtener palabras clave de los documentos activos del agente
            documentos = self.db.query(UnidadContenido).filter(
                UnidadContenido.id_agente == a.id_agente,
                UnidadContenido.estado == EstadoContenidoEnum.activo,
                UnidadContenido.eliminado == False
            ).all()
            
            # Acumular contenido de TODOS los documentos
            contenido_completo = []
            for doc in documentos:
                if doc.titulo:
                    # Repetir el título varias veces para dar más peso
                    contenido_completo.extend([doc.titulo] * 3)
                if doc.palabras_clave:
                    contenido_completo.extend(doc.palabras_clave.split(','))
                if doc.contenido:
                    # Incluir contenido completo
                    contenido_completo.append(doc.contenido)
                if doc.resumen:
                    contenido_completo.append(doc.resumen)
            
            contenido_str = ". ".join([str(p).strip() for p in contenido_completo if p])
            
            # Construir texto con mayor enfoque en el contenido
            text = f"{a.nombre_agente}. {a.area_especialidad or ''}. {a.descripcion or ''}. {contenido_str}"
            docs.append(text)
            metas.append({"id_agente": a.id_agente})
            ids.append(f"agent_{a.id_agente}")
            
        if docs and self.embedder is not None:
            embeddings = self.embedder.encode(docs).tolist()
            # replace whole collection (delete+create would be simpler depending on chroma)
            try:
                self.chroma.client.delete_collection(self.index_name)
            except Exception:
                pass
            self.collection = self.chroma.get_or_create_collection(self.index_name)
            self.collection.add(documents=docs, embeddings=embeddings, metadatas=metas, ids=ids)
        elif docs:
            print("⚠️  Embedder no disponible, skipping agents_index")
        return {"ok": True, "total": len(docs)}

    def classify(self, pregunta: str, top_k: int = 1):
        # 🔥 NUEVO: Búsqueda keyword primero
        pregunta_lower = pregunta.lower()
        
        # Palabras clave por agente (manual)
        keyword_map = {
            1: ["desarrollo", "software", "programación", "lenguaje", "docentes", "profesores", "java", "python", "javascript"],
            2: ["infraestructura", "tecnológica", "servidores", "redes"],
            3: ["procesos", "industriales", "talleres", "laboratorios"],
            4: ["deporte", "salud", "educación física", "cancha", "canchas", "deportes"],
            5: ["gestión", "finanzas", "administración"],
            6: ["seguridad", "rescate", "emergencia"],
            7: ["médico", "medicina", "salud"],
        }
        
        # Buscar coincidencias exactas
        matched_agents = []
        for agent_id, keywords in keyword_map.items():
            if any(kw in pregunta_lower for kw in keywords):
                matched_agents.append(agent_id)
        
        if matched_agents:
            return matched_agents if top_k > 1 else matched_agents[0]
        
        # Si no hay coincidencia keyword, usar embeddings
        if self.embedder is None:
            print("⚠️  Embedder no disponible para clasificación, usando fallback a búsqueda en BD")
            # Devolver agente 1 por defecto (Agente TIC)
            return [1] if top_k > 1 else 1
            
        try:
            if self.collection.count() == 0:
                self.build_index()
        except Exception as e:
            print("Error al contar la colección:", e)

        q_emb = self.embedder.encode([pregunta]).tolist()[0]
        res = self.collection.query(query_embeddings=[q_emb], n_results=top_k if top_k > 1 else 3)
        metas = res.get("metadatas", [[]])[0]

        if not metas:
            return None

        agent_ids = [m["id_agente"] for m in metas]
        return agent_ids if top_k > 1 else agent_ids[0]

