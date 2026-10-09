"""SalesIA Enterprise - prepara RBAC en Supabase TESTING exclusivamente.

Simulacion (reversion total):
    python -m scripts.preparar_rbac_testing --ruc 20999999999 --razon-social "SalesIA Testing"
Aplicacion explicita:
    python -m scripts.preparar_rbac_testing --ruc 20999999999 --razon-social "SalesIA Testing" --apply

Nunca utiliza SessionLocal, DATABASE_URL ni escribe en la base principal.
"""
import argparse
from functools import partial

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.models  # registra los modelos
from app.core.config import settings
from app.models.empresa import Empresa
from scripts.seed_roles_permisos import ejecutar_seed, TODOS_LOS_PERMISOS, ROLES
from scripts.verificar_aislamiento_real import obtener_referencia_supabase


def _verificar_destino():
    principal_url = settings.DATABASE_URL
    testing_url = settings.TEST_DATABASE_URL
    principal = obtener_referencia_supabase(principal_url) if principal_url else None
    testing = obtener_referencia_supabase(testing_url) if testing_url else None
    if not principal or not testing or principal == testing:
        raise RuntimeError("SEGURIDAD: aislamiento Supabase no verificado. Operacion bloqueada.")
    return testing_url


def _obtener_o_crear_empresa(conn, ruc: str, razon_social: str) -> int:
    tabla = Empresa.__table__
    existente = conn.execute(select(Empresa.id).where(Empresa.ruc == ruc)).scalar_one_or_none()
    if existente is not None:
        activa = conn.execute(select(Empresa.activo).where(Empresa.id == existente)).scalar_one()
        if not activa:
            raise RuntimeError("La empresa de testing con ese RUC esta inactiva; no se modificara.")
        print(f"Empresa de testing existente: ID {existente}")
        return existente

    # Registrar solo campos conocidos. Ante campos obligatorios adicionales,
    # fallar de forma explicita en lugar de inventar datos.
    valores = {"ruc": ruc, "razon_social": razon_social}
    nombres = set(tabla.columns.keys())
    if "moneda_base" in nombres:
        valores["moneda_base"] = "PEN"
    if "activo" in nombres:
        valores["activo"] = True
    faltantes = [
        col.name for col in tabla.columns
        if col.name not in valores and not col.nullable and col.default is None
        and col.server_default is None and not col.primary_key and not col.autoincrement
        and not col.computed
    ]
    if faltantes:
        raise RuntimeError(
            "Empresa requiere columnas adicionales sin valor por defecto: "
            + ", ".join(faltantes)
            + ". No se crearon registros."
        )
    empresa_id = conn.execute(
        tabla.insert().values(**valores).returning(tabla.c.id)
    ).scalar_one()
    print(f"Empresa ficticia preparada: ID {empresa_id}")
    return empresa_id


def main():
    parser = argparse.ArgumentParser(description="Prepara roles y permisos SOLO en Supabase Testing")
    parser.add_argument("--ruc", required=True, help="RUC ficticio exclusivo de testing (11 digitos)")
    parser.add_argument("--razon-social", default="SalesIA Empresa Testing")
    parser.add_argument("--apply", action="store_true", help="Autoriza COMMIT SOLO EN TESTING")
    args = parser.parse_args()
    if not args.ruc.isascii() or not args.ruc.isdigit() or len(args.ruc) != 11:
        parser.error("--ruc debe contener exactamente 11 digitos ASCII")
    if not args.razon_social.strip():
        parser.error("--razon-social no puede estar vacia")

    url = _verificar_destino()
    print("=" * 55)
    print("SALESIA - PREPARACION RBAC - SOLO SUPABASE TESTING")
    print("Aislamiento Supabase: OK")
    print("Base principal: BLOQUEADA")
    print("Modo:", "APLICACION" if args.apply else "SIMULACION (ROLLBACK)")
    print("Permisos esperados:", len(TODOS_LOS_PERMISOS), "Roles:", len(ROLES))

    engine = create_engine(url, pool_pre_ping=True)
    try:
        # Transaccion exterior: solo se confirma tras crear empresa y completar el seed.
        # Sesiones del seed usan SAVEPOINT para que su commit/rollback interno no
        # comprometa la transaccion exterior ni impida el modo simulacion.
        with engine.connect() as conn:
            tx = conn.begin()
            try:
                empresa_id = _obtener_o_crear_empresa(conn, args.ruc, args.razon_social.strip())
                fabricar_sesion = partial(Session, bind=conn, join_transaction_mode="create_savepoint")
                ejecutar_seed(
                    empresa_id=empresa_id,
                    aplicar=args.apply,
                    session_factory=fabricar_sesion,
                )
                if args.apply:
                    tx.commit()
                    print("\nTESTING: empresa y seed confirmados atomica y correctamente.")
                else:
                    tx.rollback()
                    print("\nTESTING: simulacion revertida. Ningun dato guardado.")
            except BaseException:
                if tx.is_active:
                    tx.rollback()
                raise
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
