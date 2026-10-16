import json
import logging
from typing import Any, Dict

import requests
from django.core.management.base import BaseCommand

from mybookconnect.observability import (
    ObservabilityMetricsService,
    ProductMetricsService,
    SystemAlertsEvaluator,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Evalúa en tiempo real las alertas de salud operativa de la plataforma (Fase B3 - Roadmap v2.0)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            help="Genera salida estructurada en formato JSON.",
        )
        parser.add_argument(
            "--webhook-url",
            type=str,
            default=None,
            help="URL de webhook opcional (Slack, Discord o Alertmanager) para notificar alertas activas.",
        )
        parser.add_argument(
            "--fail-on-warning",
            action="store_true",
            help="Genera código de salida 1 también ante alertas de severidad WARNING.",
        )

    def handle(self, *args, **options):
        is_json = options.get("json", False)
        webhook_url = options.get("webhook_url")
        fail_on_warning = options.get("fail_on_warning", False)

        # 1. Obtener métricas de sistema y producto
        backend_metrics = ObservabilityMetricsService.get_metrics()
        product_metrics = ProductMetricsService.get_product_metrics()

        # 2. Evaluar alertas
        evaluation = SystemAlertsEvaluator.evaluate_alerts(backend_metrics, product_metrics)

        status_code_exit = 0
        overall_status = evaluation.get("overall_status", "HEALTHY")
        alerts = evaluation.get("alerts", [])

        if overall_status == "CRITICAL" or (fail_on_warning and alerts):
            status_code_exit = 1

        payload: Dict[str, Any] = {
            "status": overall_status,
            "alerts_count": len(alerts),
            "active_alerts": alerts,
            "thresholds_evaluated": 7,
            "system_summary": {
                "db_status": backend_metrics.get("database", {}).get("status", "unknown"),
                "redis_status": backend_metrics.get("redis", {}).get("status", "unknown"),
                "p95_latency_ms": backend_metrics.get("latency_ms", {}).get("p95", 0.0),
                "total_users": product_metrics.get("total_users", 0),
            },
        }

        # 3. Notificación a webhook si está configurado y hay alertas
        if webhook_url and alerts:
            try:
                resp = requests.post(
                    webhook_url,
                    json=payload,
                    timeout=5,
                    headers={"Content-Type": "application/json"},
                )
                payload["webhook_delivered"] = resp.status_code in (200, 201, 204)
            except Exception as e:
                payload["webhook_delivered"] = False
                payload["webhook_error"] = str(e)
                logger.warning(f"No se pudo despachar la notificación al webhook de alertas: {e}")

        # 4. Salida
        if is_json:
            self.stdout.write(json.dumps(payload, indent=2))
        else:
            self.stdout.write("==============================================================================")
            self.stdout.write("EVALUACIÓN DE ALERTAS OPERATIVAS DEL SISTEMA (FASE B3)")
            self.stdout.write("==============================================================================")
            self.stdout.write(f"Estado consolidado: {overall_status}")
            self.stdout.write(f"Alertas activas:    {len(alerts)}")
            self.stdout.write(f"Estado PostgreSQL:  {payload['system_summary']['db_status']}")
            self.stdout.write(f"Estado Redis:       {payload['system_summary']['redis_status']}")
            self.stdout.write(f"Latencia p95:       {payload['system_summary']['p95_latency_ms']} ms")

            if alerts:
                self.stdout.write("\nALERTAS DETECTADAS:")
                for alert in alerts:
                    sev = alert.get("severity", "WARNING")
                    msg = alert.get("message", "")
                    if sev == "CRITICAL":
                        self.stdout.write(self.style.ERROR(f"  [CRITICAL] {msg}"))
                    else:
                        self.stdout.write(self.style.WARNING(f"  [WARNING]  {msg}"))
            else:
                self.stdout.write(self.style.SUCCESS("\n¡Todos los umbrales operativos se encuentran en rango óptimo!"))
            self.stdout.write("==============================================================================")

        if status_code_exit != 0:
            raise SystemExit(status_code_exit)
