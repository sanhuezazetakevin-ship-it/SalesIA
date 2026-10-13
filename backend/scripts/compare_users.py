"""Compara roles y permisos de dos usuarios."""
from app.database.connection import SessionLocal
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.permiso import Permiso
from app.models.asociaciones import usuarios_roles, roles_permisos

db = SessionLocal()

for email in ["sanhuezazetakevin@gmail.com", "maxgab2527@gmail.com"]:
    u = db.query(Usuario).filter(Usuario.email == email).first()
    if not u:
        print(f"\n[{email}] NO ENCONTRADO")
        continue
    print(f"\n[{email}] ID={u.id}, empresa_id={u.empresa_id}, activo={u.activo}")
    print("  Roles:")
    for rol in u.roles:
        print(f"    - {rol.nombre} (ID={rol.id}, empresa_id={rol.empresa_id})")
        permisos = (
            db.query(Permiso)
            .join(roles_permisos, roles_permisos.c.permiso_id == Permiso.id)
            .filter(roles_permisos.c.rol_id == rol.id)
            .all()
        )
        if permisos:
            for p in permisos:
                print(f"        permiso: {p.codigo} (ID={p.id})")
        else:
            print("        (sin permisos asignados)")

db.close()
