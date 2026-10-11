"""Preflight sin red, sin imprimir credenciales: python -m scripts.railway_preflight"""
from pathlib import Path
import ast
import importlib.metadata as md

ROOT = Path(__file__).resolve().parents[1]


def verificar():
    errores = []
    for archivo in ("railway.toml", "requirements.txt", "app/main.py", "alembic/env.py", ".python-version"):
        if not (ROOT / archivo).is_file():
            errores.append(f"Falta {archivo}")
    for archivo in (ROOT / "app").rglob("*.py"):
        try:
            ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
        except (SyntaxError, UnicodeError) as exc:
            errores.append(f"Python invalido: {archivo.relative_to(ROOT)}: {exc}")
    requirements = (ROOT / "requirements.txt").read_text().lower()
    for dep in ("scipy", "openpyxl", "reportlab", "psycopg"):
        if dep not in requirements:
            errores.append(f"Dependencia no declarada: {dep}")
    if errores:
        for error in errores:
            print("ERROR:", error)
        raise SystemExit(1)
    print("OK: estructura Railway, dependencias y sintaxis de app verificadas")
    print("PENDIENTE: deploy real, BD, carga, migracion produccion y almacenamiento persistente")


if __name__ == "__main__":
    verificar()
