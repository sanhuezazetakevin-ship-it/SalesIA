from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_requisitos_de_exportacion_y_estadistica_declarados():
    requirements = (ROOT / "requirements.txt").read_text().lower()
    for package in ("scipy", "openpyxl", "reportlab", "psycopg"):
        assert package in requirements


def test_railway_healthcheck_y_arranque():
    config = (ROOT / "railway.toml").read_text()
    assert 'healthcheckPath = "/health"' in config
    assert "uvicorn app.main:app" in config
    assert "--port $PORT" in config


def test_alembic_produccion_continua_bloqueada():
    codigo = (ROOT / "alembic/env.py").read_text()
    assert 'destino != "testing"' in codigo
    assert "TEST_DATABASE_URL" in codigo
