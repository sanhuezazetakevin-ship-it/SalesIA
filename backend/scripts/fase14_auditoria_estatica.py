"""Verificación estática FASE 14 (no requiere DB ni dependencias externas)."""
from __future__ import annotations
import ast
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCAN = ('app', 'scripts', 'tests', 'alembic')
errors = []
count = 0
for folder in SCAN:
    for file in (ROOT / folder).rglob('*.py'):
        if any(part.startswith('.') or part == '__pycache__' for part in file.relative_to(ROOT).parts):
            continue
        try:
            tree = ast.parse(file.read_text(encoding='utf-8-sig'), filename=str(file))
            compile(tree, str(file), 'exec')
            count += 1
        except (SyntaxError, UnicodeError, ValueError) as exc:
            errors.append(f'{file.relative_to(ROOT)}: {exc}')
print(f'FASE14: {count} archivos Python verificados')
if errors:
    print('\n'.join(errors))
    sys.exit(1)
print('OK: parseo y compilación de fuentes sin errores')
