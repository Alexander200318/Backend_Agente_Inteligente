# scripts/test_redis.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.redis_config import get_redis_client

def test_redis():
    print("🧪 Probando conexión a Redis...")
    
    try:
        redis_client = get_redis_client()
        
        # Test 1: Ping
        response = redis_client.ping()
        print(f"✅ Ping: {response}")
        
        # Test 2: Set/Get
        redis_client.set("test_key", "test_value", ex=10)
        value = redis_client.get("test_key")
        print(f"✅ Set/Get: {value}")
        
        # Test 3: Info
        info = redis_client.info("server")
        print(f"✅ Redis version: {info.get('redis_version')}")
        
        print("\n🎉 Redis funciona correctamente!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Asegúrate de que Redis esté corriendo:")
        print("   - WSL: sudo service redis-server start")
        print("   - Docker: docker start redis")
        print("   - Memurai: Revisar servicios de Windows")

if __name__ == "__main__":
    test_redis()