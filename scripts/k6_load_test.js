import http from 'k6/http';
import { check, sleep } from 'k6';

/**
 * Fase 43: Prueba de carga con k6 para MyBookConnect.
 * Valida de forma estricta los SLAs mediante umbrales (thresholds):
 * - Normal: p95 < 300 ms
 * - Complex: p95 < 800 ms
 * - Search: p95 < 500 ms
 *
 * Ejecución:
 *   k6 run scripts/k6_load_test.js
 */

export const options = {
  stages: [
    { duration: '10s', target: 10 }, // Ramp-up a 10 usuarios virtuales
    { duration: '20s', target: 20 }, // Carga sostenida a 20 VU
    { duration: '5s', target: 0 },   // Ramp-down
  ],
  thresholds: {
    // SLAs cuantitativos de la Fase 43
    'http_req_duration{endpoint_type:normal}': ['p(95)<300'],
    'http_req_duration{endpoint_type:complex}': ['p(95)<800'],
    'http_req_duration{endpoint_type:search}': ['p(95)<500'],
    // Tasa máxima admisible de fallos: inferior al 1%
    'http_req_failed': ['rate<0.01'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  // 1. Endpoint Normal: Catálogo paginado
  const catalogRes = http.get(`${BASE_URL}/api/v1/books/`, {
    tags: { endpoint_type: 'normal' },
  });
  check(catalogRes, {
    'catálogo status 200': (r) => r.status === 200,
  });

  sleep(0.5);

  // 2. Endpoint de Búsqueda: Búsqueda por texto / trigramas
  const searchRes = http.get(`${BASE_URL}/api/v1/books/?search=libro`, {
    tags: { endpoint_type: 'search' },
  });
  check(searchRes, {
    'búsqueda status 200': (r) => r.status === 200,
  });

  sleep(0.5);

  // 3. Endpoint Complejo: Libros en tendencia
  const trendingRes = http.get(`${BASE_URL}/api/v1/books/trending/`, {
    tags: { endpoint_type: 'complex' },
  });
  check(trendingRes, {
    'tendencias status 200': (r) => r.status === 200,
  });

  sleep(0.5);

  // 4. Endpoint Complejo: Recomendaciones híbridas
  const recoRes = http.get(`${BASE_URL}/api/v1/books/recommendations/`, {
    tags: { endpoint_type: 'complex' },
  });
  check(recoRes, {
    'recomendaciones status 200': (r) => r.status === 200,
  });

  sleep(1);
}
