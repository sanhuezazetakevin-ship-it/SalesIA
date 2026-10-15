from app.core.config import Settings


def test_pool_pequeno_por_defecto(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
    monkeypatch.setenv("JWT_SECRET_KEY", "a" * 40)
    monkeypatch.delenv("DB_POOL_SIZE", raising=False)
    monkeypatch.delenv("DB_MAX_OVERFLOW", raising=False)
    conf = Settings(_env_file=None)
    assert conf.DB_POOL_SIZE == 2
    assert conf.DB_MAX_OVERFLOW == 1


def test_gzip_instalado():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / "app/main.py").read_text(encoding="utf-8")
    assert "GZipMiddleware" in source
    assert "minimum_size=1200" in source
