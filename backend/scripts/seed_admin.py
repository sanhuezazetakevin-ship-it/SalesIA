"""
Script de semilla: crea empresa demo, rol admin y usuario administrador.

Uso:
    cd backend
    python scripts/seed_admin.py
"""

import sys
import os

# Asegurar que el directorio raíz del backend esté en sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database.connection import engine, SessionLocal
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.asociaciones import usuarios_roles
from app.core.security import hash_password


def seed():
    db = SessionLocal()
    try:
        # 1. Verificar si ya existe el usuario
        existente = db.query(Usuario).filter(Usuario.email == "maxgab2527@gmail.com").first()
        if existente:
            print(f"[OK] El usuario ya existe (ID={existente.id}). No se creó duplicado.")
            return

        # 2. Crear empresa si no existe ninguna
        empresa = db.query(Empresa).first()
        if not empresa:
            empresa = Empresa(
                razon_social="SalesIA Enterprise Demo",
                ruc="00000000001",
                moneda_base="PEN",
                activo=True,
            )
            db.add(empresa)
            db.flush()
            print(f"[+] Empresa creada: '{empresa.razon_social}' (ID={empresa.id})")
        else:
            print(f"[OK] Empresa existente: '{empresa.razon_social}' (ID={empresa.id})")

        # 3. Crear rol admin si no existe para esa empresa
        rol_admin = (
            db.query(Rol)
            .filter(Rol.empresa_id == empresa.id, Rol.nombre == "admin")
            .first()
        )
        if not rol_admin:
            rol_admin = Rol(
                empresa_id=empresa.id,
                nombre="admin",
                descripcion="Administrador con todos los permisos",
            )
            db.add(rol_admin)
            db.flush()
            print(f"[+] Rol 'admin' creado (ID={rol_admin.id})")
        else:
            print(f"[OK] Rol 'admin' existente (ID={rol_admin.id})")

        # 4. Crear usuario administrador
        password_hash = hash_password("minimodocecaracteres")
        usuario = Usuario(
            empresa_id=empresa.id,
            nombre="Admin",
            email="maxgab2527@gmail.com",
            password_hash=password_hash,
            activo=True,
        )
        db.add(usuario)
        db.flush()
        print(f"[+] Usuario admin creado (ID={usuario.id}, email=maxgab2527@gmail.com)")

        # 5. Asignar rol admin al usuario
        db.execute(
            usuarios_roles.insert().values(
                usuario_id=usuario.id,
                rol_id=rol_admin.id,
                empresa_id=empresa.id,
            )
        )
        print(f"[+] Rol 'admin' asignado al usuario ID={usuario.id}")

        db.commit()
        print("\n[LISTO] Semilla completada exitosamente.")
        print("  Email:      maxgab2527@gmail.com")
        print("  Contraseña: minimodocecaracteres")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
