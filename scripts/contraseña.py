# generar_hash.py
# Ejecutar: python generar_hash.py

import sys
import os

# Agregar el directorio padre al path para importar desde core
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("=" * 70)
print("Generador de Hash para CallCenterAI")
print("=" * 70)

try:
    # Importar directamente desde tu core/security.py
    print("\nImportando get_password_hash desde core.security...")
    from core.security import get_password_hash
    print("✅ Importación exitosa")
    
    # Contraseña a hashear
    PASSWORD = "Admin123!"
    
    print(f"\n🔑 Generando hash para: {PASSWORD}")
    
    # Generar hash usando TU MISMA FUNCIÓN
    hash_generado = get_password_hash(PASSWORD)
    
    print("\n" + "=" * 70)
    print("✅ HASH GENERADO:")
    print("=" * 70)
    print(hash_generado)
    print("=" * 70)
    
    print("\n📋 SQL para copiar y pegar:")
    print("-" * 70)
    print(f"UPDATE Usuario SET password = '{hash_generado}' WHERE username = 'superadmin';")
    print("-" * 70)
    
    # También generar el INSERT completo
    print("\n📋 O usa este INSERT completo:")
    print("-" * 70)
    print(f"""INSERT INTO Usuario (id_persona, username, email, password, estado, requiere_cambio_password) 
VALUES (1, 'superadmin', 'carlos.admin@institucion.edu.ec', '{hash_generado}', 'activo', 0);""")
    print("-" * 70)
    
    # Verificar
    from core.security import verify_password
    print("\n🔍 Verificando hash...")
    if verify_password(PASSWORD, hash_generado):
        print("✅ Hash verificado correctamente - Compatible con tu sistema\n")
    else:
        print("❌ Error en verificación\n")

except ImportError as e:
    print(f"\n❌ ERROR DE IMPORTACIÓN: {e}")
    print("\nAsegúrate de:")
    print("1. Estar en el directorio Backend_Agente_Inteligente")
    print("2. Tener activado el virtual environment")
    print("3. Tener instalado passlib: pip install passlib[bcrypt]")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

input("\nPresiona ENTER para salir...")