from database.database import Base, engine, SessionLocal
from sqlalchemy import text
from core.config import settings
from core.security import get_password_hash
from models import Persona, Usuario, Rol, UsuarioRol
from datetime import date
from sqlalchemy.exc import IntegrityError

def init_db():
    """
    Inicializar base de datos:
    - Crea todas las tablas si no existen
    - Verifica conexión
    - Crea roles por defecto
    - Crea superadmin si no existe
    """
    try:
        # Verificar conexión
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(f"✅ Conexión a MySQL exitosa: {settings.DB_NAME}")
        
        # Importar todos los modelos para que SQLAlchemy los registre
        import models
        # Esto importa todos los modelos del __init__.py
        
        # Crear tablas
        print("⏳ Creando tablas...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tablas creadas correctamente!")
        
        # Crear roles y superadmin
        print("⏳ Inicializando roles y superadmin...")
        _init_roles_and_superadmin()
        print("✅ Inicialización completada!")
        
    except Exception as e:
        print(f"❌ Error al inicializar base de datos: {e}")
        raise e

def _init_roles_and_superadmin():
    """
    Crea los roles por defecto y el superadmin si no existen.
    Si ya existen, no genera errores (ignora).
    """
    db = SessionLocal()
    try:
        # ========== CREAR ROLES ==========
        roles_default = [
            {
                "id_rol": 1,
                "nombre_rol": "SuperAdmin",
                "descripcion": "Acceso total al sistema",
                "nivel_jerarquia": 1,
                "puede_gestionar_usuarios": True,
                "puede_gestionar_departamentos": True,
                "puede_gestionar_roles": True,
                "puede_ver_todas_metricas": True,
                "puede_exportar_datos_globales": True,
                "puede_configurar_sistema": True,
                "puede_gestionar_api_keys": True,
            },
            {
                "id_rol": 2,
                "nombre_rol": "Administrador",
                "descripcion": "Acceso administrativo del sistema",
                "nivel_jerarquia": 2,
                "puede_gestionar_usuarios": True,
                "puede_ver_todas_metricas": True,
                "puede_exportar_datos_globales": True,
            },
            {
                "id_rol": 3,
                "nombre_rol": "Funcionario",
                "descripcion": "Acceso de funcionario",
                "nivel_jerarquia": 3,
                "puede_ver_todas_metricas": False,
            }
        ]
        
        for rol_data in roles_default:
            rol_id = rol_data.pop("id_rol")
            # Verificar si el rol ya existe por ID o por nombre
            rol_existente = db.query(Rol).filter((Rol.id_rol == rol_id) | (Rol.nombre_rol == rol_data["nombre_rol"])).first()
            
            if not rol_existente:
                rol = Rol(id_rol=rol_id, **rol_data, activo=True)
                db.add(rol)
                db.flush()
                print(f"  ✅ Rol creado: {rol_data['nombre_rol']} (ID: {rol_id})")
            else:
                print(f"  ℹ️  Rol ya existe: {rol_data['nombre_rol']}")
        
        db.commit()
        
        # ========== CREAR SUPERADMIN ==========
        usuario_existente = db.query(Usuario).filter(Usuario.username == "superadmin").first()
        if usuario_existente:
            print(f"  ℹ️  Superadmin ya existe")
            db.close()
            return
        
        # Crear persona para el superadmin
        persona = Persona(
            cedula="9999999999",
            nombre="super",
            apellido="admin",
            tipo_persona="administrativo",
            email_personal="superadmin@inst.edu.ec",
            cargo="Super Administrador del Sistema",
            estado="activo"
        )
        db.add(persona)
        db.flush()  # Para obtener el id_persona
        
        # Crear usuario superadmin
        usuario = Usuario(
            id_persona=persona.id_persona,
            username="superadmin",
            email="superadmin@inst.edu.ec",
            password=get_password_hash("Admin123!"),
            estado="activo"
        )
        db.add(usuario)
        db.flush()  # Para obtener el id_usuario
        
        # Obtener el rol SuperAdmin (ID: 1)
        rol_superadmin = db.query(Rol).filter(Rol.id_rol == 1).first()
        
        if rol_superadmin:
            # Asignar rol SuperAdmin al superadmin
            usuario_rol = UsuarioRol(
                id_usuario=usuario.id_usuario,
                id_rol=rol_superadmin.id_rol,
                activo=True,
                motivo="Asignación automática en inicialización del sistema"
            )
            db.add(usuario_rol)
        
        # Confirmar cambios
        db.commit()
        print("  ✅ Superadmin creado exitosamente")
        print(f"     Username: superadmin")
        print(f"     Password: Admin123!")
        print(f"     Rol: SuperAdmin (ID: 1)")
        
    except IntegrityError as e:
        db.rollback()
        print(f"  ⚠️  Integridad de datos (registro puede que ya exista): {str(e)[:100]}")
    except Exception as e:
        db.rollback()
        print(f"  ❌ Error: {e}")
    finally:
        db.close()

def drop_all_tables():
    """
    CUIDADO: Elimina todas las tablas.
    Solo usar en desarrollo.
    """
    if not settings.DEBUG:
        raise Exception("drop_all_tables solo puede ejecutarse en modo DEBUG")
    
    print("⚠️  ELIMINANDO TODAS LAS TABLAS...")
    Base.metadata.drop_all(bind=engine)
    print("✅ Tablas eliminadas")

if __name__ == "__main__":
    init_db()