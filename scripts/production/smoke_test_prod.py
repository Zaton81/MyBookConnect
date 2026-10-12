#!/usr/bin/env python3
"""
MyBookConnect - Smoke Testing Automatizado para Producción (Fase B1)

Verifica que el entorno de producción responda correctamente a través de Nginx (puertos 80/443)
y que las sondas de salud, catálogos públicos y controles perimetrales estén operativos.

Uso:
    python scripts/production/smoke_test_prod.py --host http://localhost
    python scripts/production/smoke_test_prod.py --host https://mybookconnect.com --timeout 10
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def check_endpoint(
    name: str,
    url: str,
    method: str = "GET",
    payload: dict | None = None,
    expected_status: int = 200,
    validator=None,
    timeout: float = 5.0,
    verbose: bool = False,
) -> tuple[bool, float, str]:
    start = time.perf_counter()
    headers = {"User-Agent": "MyBookConnect-ProductionSmokeTest/1.0", "Accept": "application/json"}
    data_bytes = None

    if payload is not None:
        headers["Content-Type"] = "application/json"
        data_bytes = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:  # nosec B310
            latency_ms = (time.perf_counter() - start) * 1000
            status_code = response.status
            body = response.read().decode("utf-8", errors="replace")

            if status_code != expected_status:
                return False, latency_ms, f"Status esperado {expected_status}, recibido {status_code}"

            if validator:
                try:
                    parsed = json.loads(body) if body.strip() else {}
                    valid, err_msg = validator(parsed)
                    if not valid:
                        return False, latency_ms, f"Validación de payload fallida: {err_msg}"
                except json.JSONDecodeError:
                    valid, err_msg = validator(body)
                    if not valid:
                        return False, latency_ms, f"Validación de cuerpo plano fallida: {err_msg}"

            return True, latency_ms, "OK"
    except urllib.error.HTTPError as http_err:
        latency_ms = (time.perf_counter() - start) * 1000
        if http_err.code == expected_status:
            return True, latency_ms, f"Status esperado {expected_status} recibido (HTTPError controlado)"
        return False, latency_ms, f"HTTPError {http_err.code}: {http_err.reason}"
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        return False, latency_ms, f"Error de conexión: {str(exc)}"


def run_production_smoke_tests(base_url: str, timeout: float = 5.0, verbose: bool = False) -> bool:
    print("\n=================================================================")
    print("🚀 MyBookConnect — Smoke Tests de Producción")
    print(f"🎯 Host objetivo: {base_url}")
    print("=================================================================\n")

    endpoints = [
        {
            "name": "1. SPA Frontend (Index HTML)",
            "url": f"{base_url}/",
            "method": "GET",
            "expected_status": 200,
            "validator": lambda body: (
                ("<div id=\"root\"" in str(body) or "<html" in str(body).lower(), "No contiene contenedor SPA"),
            )[0],
        },
        {
            "name": "2. Sonda Liveness (/health/live)",
            "url": f"{base_url}/health/live",
            "method": "GET",
            "expected_status": 200,
            "validator": lambda d: (isinstance(d, dict) and d.get("status") == "healthy", "status != healthy"),
        },
        {
            "name": "3. Sonda Readiness (/health/ready)",
            "url": f"{base_url}/health/ready",
            "method": "GET",
            "expected_status": 200,
            "validator": lambda d: (
                isinstance(d, dict) and d.get("status") == "ready" and d.get("services", {}).get("database") == "ready",
                "DB o caché no preparados",
            ),
        },
        {
            "name": "4. Versión de API (/api/v1/version/)",
            "url": f"{base_url}/api/v1/version/",
            "method": "GET",
            "expected_status": 200,
            "validator": lambda d: ("version" in d, "No incluye clave version"),
        },
        {
            "name": "5. Catálogo Descubrimiento (/api/v1/books/discover/)",
            "url": f"{base_url}/api/v1/books/discover/",
            "method": "GET",
            "expected_status": 200,
            "validator": lambda d: (isinstance(d, dict), "No devuelve objeto JSON"),
        },
        {
            "name": "6. FAQs Públicas (/api/v1/faqs/)",
            "url": f"{base_url}/api/v1/faqs/",
            "method": "GET",
            "expected_status": 200,
            "validator": lambda d: (isinstance(d, list), "No devuelve lista de FAQs"),
        },
        {
            "name": "7. Control de Acceso: Métricas Protegidas",
            "url": f"{base_url}/api/v1/observability/metrics/",
            "method": "GET",
            "expected_status": 401,
        },
        {
            "name": "8. Perímetro: Trampa Admin /admin/ Honeypot",
            "url": f"{base_url}/admin/",
            "method": "GET",
            "expected_status": 404,
        },
    ]

    all_passed = True
    total_time = 0.0

    for ep in endpoints:
        passed, lat, detail = check_endpoint(
            name=ep["name"],
            url=ep["url"],
            method=ep["method"],
            expected_status=ep["expected_status"],
            validator=ep.get("validator"),
            timeout=timeout,
            verbose=verbose,
        )
        total_time += lat
        icon = "✅" if passed else "❌"
        print(f"{icon} {ep['name']} — {lat:.1f}ms [{detail}]")
        if not passed:
            all_passed = False

    print("\n─────────────────────────────────────────────────────────────────")
    print(f"Tiempo acumulado: {total_time:.1f}ms")
    if all_passed:
        print("🎉 Todos los smoke tests de producción han PASADO con éxito.")
    else:
        print("⚠️ Al menos una verificación crítica de producción ha FALLADO.")
    print("=================================================================\n")

    return all_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smoke testing para producción de MyBookConnect")
    parser.add_argument("--host", default="http://localhost", help="Host base a evaluar (por defecto: http://localhost)")
    parser.add_argument("--timeout", type=float, default=5.0, help="Timeout por petición en segundos")
    parser.add_argument("--verbose", action="store_true", help="Salida detallada de depuración")

    args = parser.parse_args()
    success = run_production_smoke_tests(base_url=args.host.rstrip("/"), timeout=args.timeout, verbose=args.verbose)
    sys.exit(0 if success else 1)
