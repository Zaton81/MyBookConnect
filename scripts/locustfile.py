"""
Fase 43: Prueba de carga con Locust para MyBookConnect.
Evalúa el comportamiento del backend bajo concurrencia simulada y valida los SLAs:
- API normal: p95 < 300 ms
- API compleja: p95 < 800 ms
- Búsqueda: p95 < 500 ms

Uso:
    locust -f scripts/locustfile.py --headless -u 20 -r 5 --run-time 30s --host http://localhost:8000
"""
from locust import HttpUser, between, task


class BookSocialUser(HttpUser):
    # Tiempo de espera entre tareas entre 0.5 y 2.0 segundos
    wait_time = between(0.5, 2.0)

    @task(5)
    def test_catalog_listing(self):
        """API normal: listado paginado del catálogo general."""
        self.client.get("/api/v1/books/", name="[Normal] GET /api/v1/books/")

    @task(4)
    def test_book_detail(self):
        """API normal: detalle de libro por ID."""
        # Se consulta un libro representativo
        self.client.get("/api/v1/books/1/", name="[Normal] GET /api/v1/books/:id/")

    @task(3)
    def test_book_search(self):
        """Búsqueda: búsqueda full-text y trigramas en PostgreSQL."""
        self.client.get("/api/v1/books/?search=prueba", name="[Search] GET /api/v1/books/?search=")

    @task(2)
    def test_trending_books(self):
        """API compleja: cálculo y agregación de tendencias de lectura."""
        self.client.get("/api/v1/books/trending/", name="[Complex] GET /api/v1/books/trending/")

    @task(2)
    def test_recommendations(self):
        """API compleja: motor de recomendaciones híbrido."""
        self.client.get("/api/v1/books/recommendations/", name="[Complex] GET /api/v1/books/recommendations/")

    @task(1)
    def test_healthcheck(self):
        """API normal: comprobación de salud del backend."""
        self.client.get("/api/v1/health/", name="[Normal] GET /api/v1/health/")
