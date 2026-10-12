#!/usr/bin/env python3
"""
Runner Headless Automatizado de Pruebas de Carga con Locust — My Book Social (Fase C1)
Ejecuta la suite de carga de forma autónoma y verifica que el ratio de fallos
y la latencia p95 cumplan los SLAs del Roadmap v2.0.

Uso:
    python scripts/load_testing/run_locust_headless.py --host http://localhost:8000 --users 15 --spawn-rate 5 --run-time 20s
"""

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Runner de Carga Headless con Locust - My Book Social")
    parser.add_argument("--host", default="http://localhost:8000", help="Host base de destino")
    parser.add_argument("--users", type=int, default=10, help="Número máximo de usuarios concurrentes")
    parser.add_argument("--spawn-rate", type=int, default=5, help="Tasa de aparición de usuarios por segundo")
    parser.add_argument("--run-time", default="15s", help="Duración de la prueba (ej: 15s, 1m)")
    parser.add_argument("--csv-prefix", default=None, help="Prefijo para exportar métricas en formato CSV")

    args = parser.parse_args()

    locustfile_path = Path(__file__).resolve().parent / "locustfile.py"
    if not locustfile_path.exists():
        print(f"Error: No se encontró locustfile en {locustfile_path}")
        return 1

    cmd = [
        sys.executable,
        "-m",
        "locust",
        "-f",
        str(locustfile_path),
        "--headless",
        "--host",
        args.host,
        "-u",
        str(args.users),
        "-r",
        str(args.spawn_rate),
        "--run-time",
        args.run_time,
    ]

    if args.csv_prefix:
        cmd.extend(["--csv", args.csv_prefix])

    print("=================================================================")
    print("🚀 My Book Social — Ejecución de Carga Headless con Locust")
    print(f"🎯 Host: {args.host} | Usuarios: {args.users} | Duración: {args.run_time}")
    print("=================================================================\n")

    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
