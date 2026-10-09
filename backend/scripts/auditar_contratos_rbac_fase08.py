"""FASE 08-G.5 — Inventario de contratos y evidencia RBAC.

Ejecución: python -m scripts.auditar_contratos_rbac_fase08
Solo lee código fuente y esquema FastAPI; escribe reportes locales.
La presencia de un literal de permiso NO demuestra autorización efectiva.
"""
from __future__ import annotations

import ast
import csv
import json
from collections import Counter
from pathlib import Path

from app.main import app

METODOS = {"get", "post", "put", "patch", "delete"}


def literales_python(ruta: Path) -> set[str]:
    try:
        arbol = ast.parse(ruta.read_text(encoding="utf-8-sig"), filename=str(ruta))
    except (SyntaxError, UnicodeError, OSError):
        return set()
    return {n.value for n in ast.walk(arbol) if isinstance(n, ast.Constant) and isinstance(n.value, str)}


def main():
    raiz = Path(__file__).resolve().parents[1]
    salida = raiz / "reports" / "fase08"
    salida.mkdir(parents=True, exist_ok=True)
    esquema = app.openapi()
    modulos = sorted((raiz / "app").rglob("*.py"))
    evidencias = {p.relative_to(raiz).as_posix(): literales_python(p) for p in modulos}
    catalogo = set()
    try:
        from scripts.seed_roles_permisos import TODOS_LOS_PERMISOS
        catalogo = set(TODOS_LOS_PERMISOS)
    except ImportError:
        pass

    filas = []
    for ruta, definicion in sorted(esquema.get("paths", {}).items()):
        for metodo, op in sorted(definicion.items()):
            if metodo not in METODOS:
                continue
            permiso = op.get("x-required-permission")
            protegido = bool(op.get("security") or esquema.get("security"))
            ocurrencias = [archivo for archivo, textos in evidencias.items() if permiso and permiso in textos and archivo != "app/core/openapi_contracts.py"]
            if not protegido:
                estado = "PUBLICO_SIN_RBAC"
            elif not permiso:
                estado = "REVISAR_SIN_METADATO_RBAC"
            elif catalogo and permiso not in catalogo:
                estado = "PERMISO_FUERA_DE_CATALOGO"
            elif ocurrencias:
                estado = "EVIDENCIA_LITERAL_REVISAR_FLUJO"
            else:
                estado = "SIN_EVIDENCIA_LITERAL_REVISAR_MANUAL"
            filas.append({
                "metodo": metodo.upper(), "ruta": ruta, "operation_id": op.get("operationId", ""),
                "bearer_documentado": protegido, "permiso_documentado": permiso or "",
                "permiso_en_catalogo": (permiso in catalogo) if permiso else "",
                "archivos_con_literal": "; ".join(ocurrencias), "estado": estado,
                "errores_documentados": ",".join(sorted(k for k in op.get("responses", {}) if k in {"401", "403", "404", "409"})),
            })

    csv_path = salida / "auditoria_rbac_openapi.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(filas[0]))
        writer.writeheader()
        writer.writerows(filas)
    resumen = {
        "total_operaciones": len(filas),
        "por_estado": dict(Counter(f["estado"] for f in filas)),
        "nota": "La búsqueda de literales es una pista, no un análisis de flujo de datos ni prueba de seguridad.",
        "reporte": str(csv_path),
    }
    json_path = salida / "resumen_rbac_openapi.json"
    json_path.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SALESIA — FASE 08-G.5 / CONTRATOS + RBAC")
    print("Operaciones:", len(filas))
    for clave, cantidad in sorted(resumen["por_estado"].items()):
        print(f"  {clave}: {cantidad}")
    print("CSV:", csv_path.relative_to(raiz))
    print("JSON:", json_path.relative_to(raiz))
    print("IMPORTANTE: verificar manualmente autorización real en rutas y servicios.")


if __name__ == "__main__":
    main()
