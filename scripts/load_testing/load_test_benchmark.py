#!/usr/bin/env python3
"""
Script de Prueba de Carga Concurrente y Verificación de SLAs — MyBookConnect
Fase B4: Escalabilidad Básica (Roadmap v2.0)

Evalúa el rendimiento bajo concurrencia simulada y valida los SLAs de la plataforma:
- Sonda de salud (/health/live): p95 < 100 ms
- Sonda de preparación (/health/ready): p95 < 150 ms
- Catálogo general (/api/v1/books/): p95 < 300 ms
- Descubrimiento / Búsqueda (/api/v1/books/discover/ o ?search=): p95 < 500 ms

Uso:
    python scripts/load_testing/load_test_benchmark.py --host http://localhost:8000 --concurrency 10 --requests 50 --output-json ./reports/sla_report.json
"""

import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import statistics
import sys
import time
import urllib.error
import urllib.request


def make_request(url: str, timeout: float = 5.0) -> tuple[bool, int, float]:
    start_time = time.perf_counter()
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MyBookConnect-Benchmark/2.0", "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:  # nosec B310
            latency = (time.perf_counter() - start_time) * 1000.0
            return (True, response.status, latency)
    except urllib.error.HTTPError as exc:
        latency = (time.perf_counter() - start_time) * 1000.0
        return (False, exc.code, latency)
    except Exception:
        latency = (time.perf_counter() - start_time) * 1000.0
        return (False, 500, latency)


def run_benchmark_for_endpoint(name: str, url: str, concurrency: int, total_requests: int, sla_p95_ms: float) -> dict:
    print(f"\n--- Probando: {name} ({url}) ---")
    print(f"Concurrencia: {concurrency} hilos | Peticiones totales: {total_requests}")

    latencies = []
    success_count = 0
    start_bench = time.perf_counter()

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(make_request, url) for _ in range(total_requests)]
        for future in concurrent.futures.as_completed(futures):
            success, status_code, latency = future.result()
            latencies.append(latency)
            if success and 200 <= status_code < 400:
                success_count += 1

    total_time = time.perf_counter() - start_bench
    rps = total_requests / total_time if total_time > 0 else 0

    sorted_lat = sorted(latencies)
    p50 = sorted_lat[int(len(sorted_lat) * 0.50)]
    p95 = sorted_lat[int(len(sorted_lat) * 0.95)] if len(sorted_lat) > 1 else sorted_lat[0]
    p99 = sorted_lat[int(len(sorted_lat) * 0.99)] if len(sorted_lat) > 1 else sorted_lat[0]
    mean_lat = statistics.mean(sorted_lat)

    sla_passed = p95 <= sla_p95_ms

    result = {
        "endpoint": name,
        "url": url,
        "total_requests": total_requests,
        "success_rate": (success_count / total_requests) * 100.0,
        "rps": round(rps, 2),
        "mean_ms": round(mean_lat, 2),
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "p99_ms": round(p99, 2),
        "sla_target_p95_ms": sla_p95_ms,
        "sla_passed": sla_passed,
    }

    print(f"RPS: {result['rps']} | Éxito: {result['success_rate']:.1f}%")
    print(f"Media: {result['mean_ms']}ms | p50: {result['p50_ms']}ms | p95: {result['p95_ms']}ms | p99: {result['p99_ms']}ms")
    print(f"SLA p95 objetivo: <= {sla_p95_ms}ms -> {'[PASÓ]' if sla_passed else '[AVISO]'}")

    return result


def main():
    parser = argparse.ArgumentParser(description="MyBookConnect Concurrency Benchmark Runner")
    parser.add_argument("--host", default="http://localhost:8000", help="Host base de la API")
    parser.add_argument("--concurrency", type=int, default=10, help="Número de hilos concurrentes")
    parser.add_argument("--requests", type=int, default=50, help="Número total de peticiones por endpoint")
    parser.add_argument("--strict", action="store_true", help="Falla con código 1 si algún SLA no se cumple")
    parser.add_argument("--output-json", default=None, help="Ruta de archivo para guardar el resumen JSON")
    args = parser.parse_args()

    print("=================================================================")
    print("  MyBookConnect — Suite de Pruebas de Carga y SLAs (Fase B4)     ")
    print("=================================================================")
    print(f"Host destino: {args.host}")

    targets = [
        ("Sonda Live (/health/live)", f"{args.host}/health/live", 100.0),
        ("Sonda Ready (/health/ready)", f"{args.host}/health/ready", 150.0),
        ("Catálogo de Libros (/api/v1/books/)", f"{args.host}/api/v1/books/", 300.0),
        ("Búsqueda de Libros (/api/v1/books/?search=soledad)", f"{args.host}/api/v1/books/?search=soledad", 500.0),
    ]

    all_passed = True
    summary = []

    for name, url, sla_p95 in targets:
        res = run_benchmark_for_endpoint(name, url, args.concurrency, args.requests, sla_p95)
        summary.append(res)
        if not res["sla_passed"]:
            all_passed = False

    print("\n=================================================================")
    print("                      RESUMEN DE BENCHMARKS                      ")
    print("=================================================================")
    for item in summary:
        status_str = "DENTRO DE SLA" if item["sla_passed"] else "AVISO: SLA SUPERADO (ENTORNO DEV/VIRTUALIZADO)"
        print(f"- {item['endpoint']}: p95={item['p95_ms']}ms (Objetivo: <= {item['sla_target_p95_ms']}ms) -> {status_str}")

    print("=================================================================")

    if args.output_json:
        out_path = Path(args.output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        report_data = {
            "version": "2.0",
            "phase": "B4",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "host": args.host,
            "concurrency": args.concurrency,
            "requests_per_endpoint": args.requests,
            "all_slas_met": all_passed,
            "results": summary,
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        print(f"Reporte JSON guardado en: {out_path}")

    if all_passed:
        print("RESULTADO: Todos los SLAs de latencia concurrente se cumplen.")
        sys.exit(0)
    else:
        if args.strict:
            print("ERROR: Al menos un endpoint superó el SLA límite bajo modo estricto.")
            sys.exit(1)
        else:
            print("REPORTE COMPLETADO: Medición de benchmarks finalizada.")
            sys.exit(0)


if __name__ == "__main__":
    main()
