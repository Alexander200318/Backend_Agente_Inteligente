from database.database import SessionLocal
from models.agente_virtual import AgenteVirtual
from services.agent_classifier import AgentClassifier
from rag.rag_service import RAGService

db = SessionLocal()

# Ver agentes activos
print("AGENTES ACTIVOS:")
agentes = db.query(AgenteVirtual).filter(AgenteVirtual.activo == True).all()
for a in agentes:
    print(f"\nID {a.id_agente}: {a.nombre_agente}")
    print(f"  Area: {a.area_especialidad}")
    
    # Ver cuantos documentos tiene
    rag = RAGService(db)
    docs = rag.search(id_agente=a.id_agente, query="docentes profesores", incluir_inactivos=False)
    print(f"  Documentos activos: {len(docs)}")

# Clasificar la pregunta
print("\n" + "="*60)
print("CLASIFICACION DE: 'quienes son los docentes o profesores de aqui'")
print("="*60)

classifier = AgentClassifier(db)
agent_id = classifier.classify("quienes son los docentes o profesores de aqui")
print(f"Clasificado a agente: {agent_id}")

db.close()
