#!/usr/bin/env python3
"""
MyBookConnect - Smoke Testing Automatizado para Staging / Pre-producción
Fase 35 - Despliegue y Validación en Staging (Beta Cerrada)

Verifica la disponibilidad, tiempos de respuesta y contratos de los endpoints
críticos de la plataforma en un entorno desplegado de staging o local.

Uso:
    python scripts/staging/smoke_test_staging.py --host http://localhost:8000
    python scripts/staging/smoke_test_staging.py --host https://staging.mybookconnect.com --timeout 10
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
    """
    Ejecuta una petición HTTP sintética contra el endpoint indicado
    y valida el código de respuesta y contenido esperado.
    """
    start = time.perf_counter()
    headers = {"User-Agent": "MyBookConnect-StagingSmokeTest/1.0", "Accept": "application/json"}
    data_bytes = None

    if payload is not None:
        headers["Content-Type"] = "application/json"
        data_bytes = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            latency_ms = (time.perf_counter() - start) * 1000
            status_code = response.status
            body = response.read().decode("utf-8", errors="replace")

            if status_code != expected_status:
                return False, latency_ms, f"Status code esperado {expected_status}, recibido {status_code}"

            if validator:
                try:
                    data = json.loads(body) if body else {}
                    valid, err_msg = validator(data)
                    if not valid:
                        return False, latency_ms, f"Validación de payload fallida: {err_msg}"
                except Exception as exc:
                    return False, latency_ms, f"Error parseando JSON: {exc}"

            return True, latency_ms, "OK"

    except urllib.error.HTTPError as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        if exc.code == expected_status:
            body = exc.read().decode("utf-8", errors="replace")
            if validator:
                try:
                    data = json.loads(body) if body else {}
                    valid, err_msg = validator(data)
                    if not valid:
                        return False, latency_ms, f"Validación de payload fallida: {err_msg}"
                except Exception as parse_exc:
                    return False, latency_ms, f"Error parseando JSON en error esperado: {parse_exc}"
            return True, latency_ms, f"OK (HTTP {exc.code} esperado)"
        return False, latency_ms, f"HTTPError {exc.code} (esperado {expected_status})"

    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        return False, latency_ms, f"Error de conexión: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke Testing Automatizado de Staging - MyBookConnect")
    parser.add_argument("--host", default="http://localhost:8000", help="URL base del servidor (ej. http://localhost:8000)")
    parser.add_argument("--timeout", type=float, default=5.0, help="Timeout en segundos por petición")
    parser.add_argument("--verbose", action="store_true", help="Salida detallada")
    args = parser.parse_args()

    base_url = args.host.rstrip("/")

    print("=================================================================")
    print(f"MyBookConnect -- Smoke Testing de Staging ({base_url})")
    print("=================================================================")

    checks = [
        {
            "name": "1. Sonda de Liveness (/health/live)",
            "url": f"{base_url}/health/live",
            "method": "GET",
            "expected_status": 200,
            "validator": lambda d: (d.get("status") == "healthy" and d.get("process") == "alive", f"Estado no saludable: {d}"),
        },
        {
            "name": "2. Sonda de Readiness (/health/ready)",
            "url": f"{base_url}/health/ready",
            "method": "GET",
            "expected_status": 200,
            "validator": lambda d: (
                d.get("status") == "ready" and d.get("services", {}).get("database") == "ready",
                f"Servicios dependientes no listos: {d}",
            ),
        },
        {
            "name": "3. Metadatos de Versión SemVer (/api/v1/version/)",
            "url": f"{base_url}/api/v1/version/",
            "method": "GET",
            "expected_status": 200,
            "validator": lambda d: (d.get("semver") is True and "1.0.0" in d.get("version", ""), f"Versión inválida: {d}"),
        },
        {
            "name": "4. Catálogo Público de Libros (/api/v1/books/)",
            "url": f"{base_url}/api/v1/books/",
            "method": "GET",
            "expected_status": 200,
            "validator": lambda d: (isinstance(d, dict) and ("results" in d or "count" in d), f"Estructura inesperada: {type(d)}"),
        },
        {
            "name": "5. Tendencias y Descubrimiento (/api/v1/books/trending/)",
            "url": f"{base_url}/api/v1/books/trending/",
            "method": "GET",
            "expected_status": 200,
            "validator": lambda d: (isinstance(d, (list, dict)), f"Estructura de tendencias inesperada: {type(d)}"),
        },
        {
            "name": "6. Endpoint de Invitaciones Beta (/api/v1/beta/invitations/verify/)",
            "url": f"{base_url}/api/v1/beta/invitations/verify/",
            "method": "POST",
            "payload": {"code": "SMOKE_TEST_NON_EXISTENT_CODE_123"},
            "expected_status": 400,  # Debe responder 400 Bad Request por código no encontrado
            "validator": lambda d: (isinstance(d, dict), f"Respuesta de validación inesperada: {d}"),
        },
    ]

    total = len(checks)
    passed = 0
    latencies = []

    for item in checks:
        success, latency_ms, message = check_endpoint(
            name=item["name"],
            url=item["url"],
            method=item.get("method", "GET"),
            payload=item.get("payload"),
            expected_status=item.get("expected_status", 200),
            validator=item.get("validator"),
            timeout=args.timeout,
            verbose=args.verbose,
        )

        latencies.append(latency_ms)
        status_icon = "[OK]  " if success else "[FAIL]"
        print(f" {status_icon} {item['name']:<60} [{latency_ms:6.1f} ms] -> {message}")

        if success:
            passed += 1

    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    print("-----------------------------------------------------------------")
    print(f"Resultados: {passed}/{total} endpoints superados.")
    print(f"Latencia media de respuesta: {avg_latency:.1f} ms.")

    if passed == total:
        print("Smoke Test de Staging superado con éxito. El entorno está listo para evaluadores.")
        return 0
    else:
        print(f"El Smoke Test ha fallado en {total - passed} comprobaciones.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
