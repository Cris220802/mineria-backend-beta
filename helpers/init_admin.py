from sqlalchemy.orm import Session
from passlib.context import CryptContext
from models.Usuario import User
from models.Rol import Rol
from models.Elemento import Elemento
from db.database import db_dependency


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# inicializar el usuario administrador
def init_admin_user(db: Session):
    elementos = [
        "Au",
        "Ag",
        "Pb",
        "Zn",
        "Fe",
        "Cu",
        "Insoluble",
        "Cd",
        "Ar"
    ]
    
# Obtener elementos existentes en la base de datos
    existing_elementos = {e.name: e for e in db.query(Elemento).filter(Elemento.name.in_(elementos)).all()}

    nuevos_elementos = []
    for elemento in elementos:
        if elemento not in existing_elementos:
            nuevos_elementos.append(Elemento(name=elemento))

    # Agregar solo los nuevos elementos si hay alguno
    if nuevos_elementos:
        db.add_all(nuevos_elementos)
        db.commit()
        print(f"Elemento creado: {elemento}")
    
    roles = [
        "Supervisor General", 
        "Supervisor de Planta", 
        "Supervisor de Ensayista", 
        "Ensayista"
    ]
    
    existing_roles = {role.name: role for role in db.query(Rol).filter(Rol.name.in_(roles)).all()}
    
    for role_name in roles:
        if role_name not in existing_roles:
            new_role = Rol(name=role_name)
            db.add(new_role)
            db.commit()
            db.refresh(new_role)
            existing_roles[role_name] = new_role
            print(f"Rol creado: {role_name}")
    
    # Verificar si el usuario administrador ya existe
    admin_user = db.query(User).filter(User.email == "supervisor_general@example.com").first()
    if not admin_user:
        # Asignar el rol "Supervisor General" al usuario administrador
        admin_role = existing_roles.get("Supervisor General")
        
        if admin_role:
            admin_user = User(
                email="supervisor_general@example.com",
                name="Administrador General",
                hashed_password=pwd_context.hash("admin123"),
                rol_id=admin_role.id  # Asignar el rol a través del ID
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print("Usuario administrador creado: supervisor_general@example.com / admin123")
        else:
            print("Error: Rol 'Supervisor General' no encontrado.")
    else:
        print("Usuario administrador ya existe.")
    admin_role = db.query(Rol).filter(Rol.name == "Supervisor General").first()
    if not admin_role:
        admin_role = Rol(name="Supervisor General")
        db.add(admin_role)
        db.commit()
        db.refresh(admin_role)

    # Verificar si el usuario administrador ya existe
    admin_user = db.query(User).filter(User.email == "supervisor_general@example.com").first()
    if not admin_user:
        # Crear el usuario administrador
        admin_user = User(
            email="supervisor_general@example.com",
            name="Administrador General",
            hashed_password=pwd_context.hash("admin123"),
            rol=admin_role.id
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        print("Usuario administrador creado: admin@example.com / admin123")
    else:
        print("Usuario administrador ya existe.")