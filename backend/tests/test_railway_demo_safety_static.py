from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_verificacion_supabase_demo():
    conf=(ROOT/'app/core/config.py').read_text(encoding='utf8')
    assert 'DEMO_EXPECTED_SUPABASE_REF' in conf
    assert 'DATABASE_URL no pertenece al proyecto Supabase autorizado' in conf

def test_ready_comprueba_postgres():
    main=(ROOT/'app/main.py').read_text(encoding='utf8')
    assert '@app.get("/ready"' in main
    assert 'SELECT 1' in main
    assert 'status_code=503' in main

def test_alembic_proteccion_conservada():
    text=(ROOT/'alembic/env.py').read_text(encoding='utf8')
    assert 'destino != "testing"' in text
