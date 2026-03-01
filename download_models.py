#!/usr/bin/env python
"""
Script para descargar modelos de HuggingFace al disco local.
Esto permite que el contenedor use los modelos offline.
"""
import os
import sys
from pathlib import Path
from sentence_transformers import SentenceTransformer, CrossEncoder

# Configurar ruta
BASE_DIR = Path(__file__).resolve().parent
HF_MODELS_DIR = BASE_DIR / "hf_models"
HF_MODELS_DIR.mkdir(parents=True, exist_ok=True)

print(f"📁 Descargando modelos en: {HF_MODELS_DIR}")

# Modelos a descargar
models_to_download = [
    {
        "type": "SentenceTransformer",
        "name": "all-MiniLM-L6-v2",
        "path": HF_MODELS_DIR / "all-MiniLM-L6-v2"
    },
    {
        "type": "CrossEncoder",
        "name": "cross-encoder/ms-marco-MiniLM-L-6-v2",
        "path": HF_MODELS_DIR / "ms-marco-MiniLM-L-6-v2"
    }
]

for model_info in models_to_download:
    model_name = model_info["name"]
    model_path = model_info["path"]
    model_type = model_info["type"]
    
    if model_path.exists():
        print(f"✅ {model_name} ya existe en {model_path}")
        continue
    
    try:
        print(f"\n📦 Descargando {model_type}: {model_name}...")
        
        if model_type == "SentenceTransformer":
            model = SentenceTransformer(model_name)
            model.save(str(model_path))
        elif model_type == "CrossEncoder":
            # CrossEncoder usa el mismo formato que SentenceTransformer
            # pero se descarga con una sintaxis similar
            model = CrossEncoder(model_name)
            model.save(str(model_path))
        
        print(f"✅ {model_name} descargado en {model_path}")
        
    except Exception as e:
        print(f"❌ Error descargando {model_name}: {e}")
        sys.exit(1)

print("\n✅ Todos los modelos descargados exitosamente!")
print("Ahora puedes construir el Docker con HF_HUB_OFFLINE=1")
