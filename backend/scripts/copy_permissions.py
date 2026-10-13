"""Copia todos los permisos del rol ADMIN_EMPRESA al rol admin del nuevo usuario."""
from app.database.connection import SessionLocal
from app.models.rol import Rol
from app.models.asociaciones import roles_permisos
from sqlalchemy import select

db = SessionLocal()

# Rol origen: ADMIN_EMPRESA (ID=2894)
# Rol destino: admin (ID=7928)
ROL_ORIGEN = 2894
ROL_DESTINO = 7928

# Obtener permisos del rol origen
permisos_origen = db.execute(
    select(roles_permisos.c.permiso_id).where(roles_permisos.c.rol_id == ROL_ORIGEN)
).scalars().all()

# Obtener permisos ya existentes en destino
permisos_destino = db.execute(
    select(roles_permisos.c.permiso_id).where(roles_permisos.c.rol_id == ROL_DESTINO)
).scalars().all()

faltantes = set(permisos_origen) - set(permisos_destino)

if not faltantes:
    print("[OK] El rol destino ya tiene todos los permisos.")
else:
    for pid in faltantes:
        db.execute(
            roles_permisos.insert().values(rol_id=ROL_DESTINO, permiso_id=pid)
        )
    db.commit()
    print(f"[+] Se asignaron {len(faltantes)} permisos al rol admin (ID={ROL_DESTINO}).")

db.close()
print("[LISTO] maxgab2527@gmail.com ahora tiene los mismos permisos que sanhuezazetakevin@gmail.com")
