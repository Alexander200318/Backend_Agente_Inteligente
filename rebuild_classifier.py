from database.database import SessionLocal
from services.agent_classifier import AgentClassifier
from rag.chroma_config import ChromaDBConfig

db = SessionLocal()

# Eliminar índice anterior
chroma = ChromaDBConfig()
try:
    chroma.client.delete_collection("agents_index")
    print("Coleccion agents_index eliminada")
except:
    print("No habia coleccion previa")

# Crear nuevo índice
classifier = AgentClassifier(db)
result = classifier.build_index()
print(f"Indice reconstruido: {result}")

# Probar clasificación
print("\nPRUEBA DE CLASIFICACION:")
print("="*60)

test_queries = [
    "quienes son los docentes o profesores de aqui",
    "lenguajes de programacion",
    "seguridad industrial"
]

for query in test_queries:
    agent_id = classifier.classify(query)
    print(f"'{query}'")
    print(f"  -> Agente: {agent_id}")
    print()

db.close()
