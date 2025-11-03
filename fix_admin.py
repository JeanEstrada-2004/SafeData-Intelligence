"""Script temporal para arreglar el usuario admin."""
import bcrypt
from app.database import SessionLocal
from app.models import User

db = SessionLocal()
try:
    # Buscar usuario existente
    user = db.query(User).filter(User.email == 'admin@demo.local').first()
    
    # Contraseña simple
    new_password = "Admin123!"
    
    # Hash directo con bcrypt (sin passlib)
    password_bytes = new_password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
    
    print(f"Contraseña: {new_password}")
    print(f"Hash generado (longitud: {len(hashed)})")
    
    if user:
        # Actualizar contraseña existente
        user.hashed_password = hashed
        db.commit()
        print("✅ Contraseña actualizada correctamente")
    else:
        # Crear nuevo usuario
        new_user = User(
            email="admin@demo.local",
            full_name="Administrador",
            role="Gerente",
            is_active=True,
            hashed_password=hashed
        )
        db.add(new_user)
        db.commit()
        print("✅ Usuario admin creado correctamente")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
