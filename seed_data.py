"""
Script para poblar la base de datos con datos mínimos de prueba
"""
from database.database import SessionLocal
from services.usuario_service import UsuarioService
from schemas.usuario_schemas import UsuarioCreate
from schemas.persona_schemas import PersonaCreate
from models import *
from datetime import date

def seed_completo():
    """Ejecutar seed mínimo: usuario superadmin"""
    db = SessionLocal()
    print("=" * 80)
    print("SEED MÍNIMO - CallCenterAI")
    print("=" * 80)
    
    try:
        # 1. USUARIO SUPERADMIN
        print("\n👥 [1/2] Creando Usuario SuperAdmin...")
        service = UsuarioService(db)
        
        # Verificar si ya existe
        from models import Usuario
        usuario_existente = db.query(Usuario).filter(Usuario.username == "superadmin").first()
        if usuario_existente:
            print(f"  ⏭️  superadmin (ya existe)")
            usuario = usuario_existente
        else:
            persona_schema = PersonaCreate(
                cedula="0999999999",
                nombre="super",
                apellido="admin",
                tipo_persona="administrativo",
                email_personal="superadmin@gmail.com",
                fecha_nacimiento=date(1990, 1, 1),
                cargo="Administrador",
                id_departamento=None
            )
            usuario_schema = UsuarioCreate(
                username="superadmin",
                email="admin@inst.edu.ec",
                password="Admin123!",
                persona=persona_schema
            )
            usuario = service.crear_usuario(usuario_schema)
            print(f"  ✅ {usuario.username}")
        
        # 2. ROLES
        print("\n🔐 [2/2] Creando Roles...")
        roles = []
        roles_data = [
            {
                "nombre_rol": "SuperAdmin",
                "nivel_jerarquia": 1,
                "puede_gestionar_usuarios": True,
                "puede_gestionar_departamentos": True,
                "puede_gestionar_roles": True,
                "puede_configurar_sistema": True,
                "creado_por": usuario.id_usuario
            },
            {
                "nombre_rol": "Admin",
                "nivel_jerarquia": 2,
                "puede_gestionar_usuarios": True,
                "puede_ver_todas_metricas": True,
                "creado_por": usuario.id_usuario
            },
            {
                "nombre_rol": "Funcionario",
                "nivel_jerarquia": 3,
                "puede_crear_contenido": True,
                "puede_editar_contenido": True,
                "creado_por": usuario.id_usuario
            },
        ]
        
        for r in roles_data:
            # Verificar si el rol ya existe
            rol_existente = db.query(Rol).filter(Rol.nombre_rol == r["nombre_rol"]).first()
            if rol_existente:
                print(f"  ⏭️  {rol_existente.nombre_rol} (ya existe)")
                roles.append(rol_existente)
            else:
                rol = Rol(**r)
                db.add(rol)
                db.commit()
                db.refresh(rol)
                roles.append(rol)
                print(f"  ✅ {rol.nombre_rol}")
        
        # ASIGNAR SUPERADMIN Y ADMIN AL USUARIO
        # Verificar si ya existen las asignaciones
        asignacion_super = db.query(UsuarioRol).filter(
            UsuarioRol.id_usuario == usuario.id_usuario,
            UsuarioRol.id_rol == roles[0].id_rol
        ).first()
        
        if not asignacion_super:
            UsuarioRol(
                id_usuario=usuario.id_usuario,
                id_rol=roles[0].id_rol,  # SuperAdmin
                asignado_por=usuario.id_usuario
            ).save(db)
        
        asignacion_admin = db.query(UsuarioRol).filter(
            UsuarioRol.id_usuario == usuario.id_usuario,
            UsuarioRol.id_rol == roles[1].id_rol
        ).first()
        
        if not asignacion_admin:
            UsuarioRol(
                id_usuario=usuario.id_usuario,
                id_rol=roles[1].id_rol,  # Admin
                asignado_por=usuario.id_usuario
            ).save(db)
        
        # ESTADÍSTICAS FINALES
        print("\n" + "=" * 80)
        print("✅ SEED COMPLETADO EXITOSAMENTE")
        print("=" * 80)
        print(f"👤 Usuario:          superadmin")
        print(f"🔐 Roles asignados:  SuperAdmin, Admin")
        print(f"📋 Total Roles:      {len(roles)}")
        print("=" * 80)
        
        db.close()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        db.close()

# Helper para guardar modelos
def save_model(model, db):
    db.add(model)
    db.commit()
    db.refresh(model)
    return model

# Agregar método save a todos los modelos
from database.database import Base
Base.save = lambda self, db: save_model(self, db)

if __name__ == "__main__":
    seed_completo()