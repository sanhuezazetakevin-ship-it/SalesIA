"""Benchmark HTTP no destructivo: endpoints GET, con JWT opcional en variable de entorno.
Ejemplo: set SALESIA_BENCH_TOKEN=<JWT> (solo en terminal privada)
python -m scripts.benchmark_http_demo --base-url https://example.up.railway.app --path /ready
No imprime el JWT. No realiza escrituras ni sigue redirecciones.
"""
import argparse
import json
import os
import statistics
import time
from urllib.parse import urlsplit
import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--path", action="append", required=True)
    parser.add_argument("--requests", type=int, default=12)
    parser.add_argument("--timeout", type=float, default=15)
    args = parser.parse_args()
    url = urlsplit(args.base_url)
    if url.scheme not in ("https", "http") or not url.hostname or url.username or url.password:
        parser.error("La URL base debe ser HTTP(S) sin credenciales")
    if args.requests < 2 or args.requests > 100:
        parser.error("--requests debe estar entre 2 y 100")
    paths = args.path
    if any(not x.startswith("/") or x.startswith("//") or "#" in x for x in paths):
        parser.error("Las rutas deben empezar por /, no contener fragmentos ni ser URLs externas")
    token = os.getenv("SALESIA_BENCH_TOKEN", "").strip()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    with httpx.Client(timeout=args.timeout, follow_redirects=False, headers=headers) as client:
        for path in paths:
            samples = []
            statuses = {}
            for _ in range(args.requests):
                start = time.perf_counter()
                response = client.get(args.base_url.rstrip("/") + path)
                elapsed = (time.perf_counter() - start) * 1000
                samples.append(elapsed)
                statuses[str(response.status_code)] = statuses.get(str(response.status_code), 0) + 1
            sorted_samples = sorted(samples)
            p95 = sorted_samples[max(0, int(0.95 * len(samples) + 0.99999) - 1)]
            print(json.dumps({"path": path, "requests": len(samples), "statuses": statuses,
                              "median_ms": round(statistics.median(samples), 2),
                              "p95_ms": round(p95, 2), "max_ms": round(max(samples), 2)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
