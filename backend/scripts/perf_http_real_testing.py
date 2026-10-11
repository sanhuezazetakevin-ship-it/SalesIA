"""Ejecutar como: python -m scripts.perf_http_real_testing"""
from scripts.perf_modulos_testing import verificar_testing


def main():
    verificar_testing()
    import pytest
    return int(pytest.main([
        'tests/test_railway_perfil_http_real.py', '-q', '-s', '--tb=short', '-rs'
    ]))


if __name__ == '__main__':
    raise SystemExit(main())
