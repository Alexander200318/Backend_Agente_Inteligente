"""
Script para verificar todas las tablas creadas en la base de datos
"""
from sqlalchemy import inspect, text
from database.database import engine
from core.config import settings
import models  # Importar todos los modelos

def verificar_tablas():
    """Verifica todas las tablas creadas en MySQL"""
    
    print("=" * 80)
    print(f"VERIFICACIÓN DE BASE DE DATOS: {settings.DB_NAME}")
    print("=" * 80)
    
    try:
        # Crear inspector
        inspector = inspect(engine)
        
        # Obtener todas las tablas
        tablas = inspector.get_table_names()
        
        print(f"\n✅ Conexión exitosa a MySQL")
        print(f"📊 Total de tablas encontradas: {len(tablas)}\n")
        
        # Lista de tablas esperadas
        tablas_esperadas = [
            'Departamento',
            'Persona',
            'Usuario',
            'Rol',
            'Usuario_Rol',
            'Agente_Virtual',
            'Usuario_Agente',
            'Departamento_Agente',
            'Categoria',
            'Unidad_Contenido',
            'Visitante_Anonimo',
            'Conversacion_Sync',
            'Metrica_Diaria_Agente',
            'Metrica_Contenido',
            'Notificacion_Usuario',
            'API_Key',
            'Widget_Config',
            'Configuracion_Sistema'
        ]
        
        print("📋 TABLAS CREADAS:")
        print("-" * 80)
        
        for i, tabla in enumerate(sorted(tablas), 1):
            # Obtener columnas
            columnas = inspector.get_columns(tabla)
            num_columnas = len(columnas)
            
            # Verificar si está en esperadas
            estado = "✅" if tabla in tablas_esperadas else "⚠️"
            
            print(f"{estado} {i:2d}. {tabla:<30} ({num_columnas} columnas)")
            
        print("-" * 80)
        
        # Verificar tablas faltantes
        tablas_faltantes = set(tablas_esperadas) - set(tablas)
        if tablas_faltantes:
            print(f"\n❌ TABLAS FALTANTES ({len(tablas_faltantes)}):")
            for tabla in sorted(tablas_faltantes):
                print(f"   - {tabla}")
        else:
            print("\n✅ Todas las tablas esperadas están presentes!")
        
        # Verificar tablas extras
        tablas_extras = set(tablas) - set(tablas_esperadas)
        if tablas_extras:
            print(f"\n⚠️  TABLAS NO ESPERADAS ({len(tablas_extras)}):")
            for tabla in sorted(tablas_extras):
                print(f"   - {tabla}")
        
        # Mostrar detalles de una tabla específica
        print("\n" + "=" * 80)
        print("DETALLE DE TABLA: Usuario")
        print("=" * 80)
        
        columnas_usuario = inspector.get_columns('Usuario')
        for col in columnas_usuario:
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            tipo = str(col['type'])
            print(f"  {col['name']:<30} {tipo:<20} {nullable}")
        
        # Verificar foreign keys
        print("\n" + "=" * 80)
        print("FOREIGN KEYS EN Usuario:")
        print("=" * 80)
        
        fks = inspector.get_foreign_keys('Usuario')
        for fk in fks:
            print(f"  {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
        
        # Estadísticas generales
        print("\n" + "=" * 80)
        print("ESTADÍSTICAS GENERALES:")
        print("=" * 80)
        
        with engine.connect() as conn:
            for tabla in sorted(tablas):
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) as total FROM `{tabla}`"))
                    count = result.scalar()
                    print(f"  {tabla:<30} {count:>5} registros")
                except Exception as e:
                    print(f"  {tabla:<30} Error: {e}")
        
        print("\n" + "=" * 80)
        print("✅ VERIFICACIÓN COMPLETADA")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verificar_tablas()