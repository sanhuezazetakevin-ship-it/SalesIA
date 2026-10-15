
from getpass import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.database.connection import SessionLocal, engine
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.rol import Rol

EMPRESA_ID = 3170
EMAIL = "admin@salesia.test"
PROYECTO_TESTING = "dotqtobseniupdycsohb"


def main():
    proyecto = (engine.url.username or "").split(".")[-1]

    if proyecto != PROYECTO_TESTING:
        raise RuntimeError(
            "SEGURIDAD: conexión distinta a Supabase TESTING."
        )

    with SessionLocal() as db:
        empresa = db.get(Empresa, EMPRESA_ID)

        if not empresa or not empresa.activo:
            raise RuntimeError("Empresa testing inexistente o inactiva.")

        existente = db.scalar(
            select(Usuario).where(Usuario.email == EMAIL)
        )

        if existente:
            raise RuntimeError("El administrador ya existe.")

        rol = db.scalar(
            select(Rol).where(
                Rol.empresa_id == EMPRESA_ID,
                Rol.nombre == "ADMIN_EMPRESA"
            )
        )

        if rol is None:
            raise RuntimeError("No existe el rol ADMIN_EMPRESA.")

        password = getpass("Contraseña segura: ")
        confirmacion = getpass("Confirmar contraseña: ")

        if password != confirmacion:
            raise RuntimeError("Las contraseñas no coinciden.")

        if len(password) < 12:
            raise RuntimeError("La contraseña debe tener al menos 12 caracteres.")

        usuario = Usuario(
            empresa_id=EMPRESA_ID,
            nombre="Administrador Plataforma SalesIA",
            email=EMAIL,
            password_hash=hash_password(password),
            activo=True,
        )

        usuario.roles.append(rol)
        db.add(usuario)
        db.commit()

        print("Administrador creado correctamente.")
        print("Empresa:", EMPRESA_ID)
        print("Correo:", EMAIL)


if __name__ == "__main__":
    main()
