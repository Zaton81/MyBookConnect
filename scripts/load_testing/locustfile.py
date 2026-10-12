"""
Pruebas de Carga Concurrente con Locust para My Book Social (Fase C1)
Evalúa el rendimiento de la plataforma bajo concurrencia simulada sobre endpoints críticos:
1. Catálogo y Listados (/api/v1/books/)
2. Búsqueda unificada (/api/v1/search/)
3. Feed social de actividades (/api/v1/users/feed/)
4. Muro social de usuarios (/api/v1/users/<id>/posts/)
5. WebSockets Ticket de Chat (/api/v1/auth/ws-ticket/)
6. Sondas de Liveness y Readiness (/health/live, /health/ready)

SLAs objetivo:
- p95 < 250 ms en listados y sondas
- p95 < 400 ms en feed y búsquedas híbridas
- Error rate < 1.0 %
"""

import os

from locust import HttpUser, between, task


class MyBookSocialUser(HttpUser):
    wait_time = between(0.5, 2.0)

    def on_start(self):
        """Inicializa cabeceras comunes de autenticación si se provee token o ticket."""
        self.auth_token = os.environ.get("LOCUST_AUTH_TOKEN", "")
        self.headers = {"Accept": "application/json"}
        if self.auth_token:
            self.headers["Authorization"] = f"Bearer {self.auth_token}"

    @task(6)
    def test_catalog_listing(self):
        """Lectura intensiva: listado paginado del catálogo general."""
        self.client.get("/api/v1/books/", headers=self.headers, name="[Catalog] GET /api/v1/books/")

    @task(4)
    def test_unified_search(self):
        """Búsqueda: búsqueda global unificada (libros, autores, lectores)."""
        self.client.get(
            "/api/v1/search/?q=soledad",
            headers=self.headers,
            name="[Search] GET /api/v1/search/?q=",
        )

    @task(3)
    def test_discover_facet(self):
        """Descubrimiento: exploración facetada pública."""
        self.client.get(
            "/api/v1/books/discover/",
            headers=self.headers,
            name="[Discover] GET /api/v1/books/discover/",
        )

    @task(3)
    def test_social_feed(self):
        """Feed social de actividades (si autenticado o sonda pública)."""
        self.client.get(
            "/api/v1/users/feed/",
            headers=self.headers,
            name="[Social] GET /api/v1/users/feed/",
        )

    @task(2)
    def test_chat_websocket_ticket(self):
        """Chat en tiempo real: obtención de ticket efímero de WebSocket."""
        self.client.post(
            "/api/v1/auth/ws-ticket/",
            headers=self.headers,
            name="[Chat] POST /api/v1/auth/ws-ticket/",
        )

    @task(1)
    def test_health_live(self):
        """Sonda de liveness del backend."""
        self.client.get("/health/live", name="[Health] GET /health/live")

    @task(1)
    def test_health_ready(self):
        """Sonda de readiness (PostgreSQL + Redis)."""
        self.client.get("/health/ready", name="[Health] GET /health/ready")
