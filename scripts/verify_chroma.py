# scripts/verify_chroma.py
from rag.chroma_config import ChromaDBConfig

def verificar_chroma():
    chroma = ChromaDBConfig()
    
    print("=" * 60)
    print("🔍 VERIFICACIÓN DE CHROMADB")
    print("=" * 60)
    
    # 1. Listar todas las colecciones
    collections = chroma.list_collections()
    print(f"\n📦 Total de colecciones: {len(collections)}")
    
    if not collections:
        print("❌ No hay colecciones creadas en ChromaDB")
        return
    
    # 2. Mostrar detalles de cada colección
    for col in collections:
        print(f"\n{'='*60}")
        print(f"📁 Colección: {col.name}")
        print(f"{'='*60}")
        
        # Obtener metadata
        try:
            metadata = col.metadata
            print(f"Metadata: {metadata}")
        except:
            print("Metadata: No disponible")
        
        # Contar documentos
        try:
            count = col.count()
            print(f"📊 Total documentos: {count}")
        except Exception as e:
            print(f"❌ Error al contar: {e}")
            continue
        
        if count == 0:
            print("⚠️  Colección vacía")
            continue
        
        # 3. Obtener algunos documentos de muestra
        try:
            results = col.get(limit=5)
            
            print(f"\n📄 Documentos indexados (primeros 5):")
            print("-" * 60)
            
            if results and 'ids' in results:
                for i, doc_id in enumerate(results['ids']):
                    print(f"\n{i+1}. ID: {doc_id}")
                    
                    if 'metadatas' in results and i < len(results['metadatas']):
                        meta = results['metadatas'][i]
                        print(f"   Tipo: {meta.get('tipo', 'N/A')}")
                        
                        if meta.get('tipo') == 'unidad_contenido':
                            print(f"   Título: {meta.get('titulo', 'N/A')}")
                            print(f"   ID Contenido: {meta.get('id_contenido', 'N/A')}")
                            print(f"   ID Categoría: {meta.get('id_categoria', 'N/A')}")
                        elif meta.get('tipo') == 'categoria':
                            print(f"   ID Categoría: {meta.get('id_categoria', 'N/A')}")
                    
                    if 'documents' in results and i < len(results['documents']):
                        doc = results['documents'][i]
                        preview = doc[:150] + "..." if len(doc) > 150 else doc
                        print(f"   Preview: {preview}")
            else:
                print("⚠️  No se pudieron obtener documentos")
                
        except Exception as e:
            print(f"❌ Error al obtener documentos: {e}")
    
    print(f"\n{'='*60}")
    print("✅ Verificación completada")
    print(f"{'='*60}")

if __name__ == "__main__":
    verificar_chroma()