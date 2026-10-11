"""Revisión estática de configuración sin mostrar secretos ni contactar producción.
Uso: python -m scripts.railway_pdf_release_check
"""
from pathlib import Path
import ast
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def main():
    fallos = []
    precauciones = []
    config = tomllib.loads((ROOT / 'railway.toml').read_text(encoding='utf-8'))
    start = config.get('deploy', {}).get('startCommand', '')
    if 'uvicorn app.main:app' not in start or '--host 0.0.0.0' not in start or '$PORT' not in start:
        fallos.append('Railway debe iniciar FastAPI usando el puerto PORT')
    if config.get('deploy', {}).get('healthcheckPath') != '/health':
        fallos.append('Railway debe comprobar /health')
    route = (ROOT / 'app/api/routes/reportes.py').read_text(encoding='utf-8')
    service = (ROOT / 'app/services/reportes_pdf_directo.py').read_text(encoding='utf-8')
    main = (ROOT / 'app/main.py').read_text(encoding='utf-8')
    req = (ROOT / 'requirements.txt').read_text(encoding='utf-8').lower()
    for file, source in [('ruta', route), ('servicio', service), ('app', main)]:
        try:
            ast.parse(source)
        except SyntaxError as exc:
            fallos.append(f'Sintaxis inválida en {file}: {exc.msg}')
    if "'/pdf-directo'" not in route or 'generar_pdf_directo' not in route:
        fallos.append('Falta la ruta PDF bajo demanda')
    if 'application/pdf' not in route or 'no-store' not in route:
        fallos.append('Faltan cabeceras PDF privadas')
    if '_tenant(db, usuario_id' not in service:
        fallos.append('Verificar permiso y empresa en PDF')
    if 'reportlab' not in req:
        fallos.append('Falta ReportLab en requirements.txt')
    if 'include_router(reportes_router)' not in main:
        fallos.append('El router reportes no aparece en app/main.py')
    if 'workers 1' not in start:
        precauciones.append('Confirmar estrategia de workers según RAM y pool PostgreSQL')
    precauciones.extend([
        'Verificar CORS_ORIGINS HTTPS exacto para Vercel en Railway',
        'Configurar DATABASE_URL Supabase, JWT_SECRET_KEY segura y ENVIRONMENT=production',
        'No ejecutar migraciones automáticas de producción; revisar y ejecutar por separado',
        'Probar endpoint PDF con JWT y PostgreSQL testing; controlar concurrencia y tamaño del PDF',
        'Las rutas antiguas /generar y /descargar todavía usan archivos locales',
    ])
    for linea in fallos:
        print('ERROR:', linea)
    for linea in precauciones:
        print('PENDIENTE:', linea)
    if fallos:
        raise SystemExit(1)
    print('OK: preflight estático de PDF/Railway; no confirma despliegue ni acceso a Supabase')


if __name__ == '__main__':
    main()
