# Guía de Testing y Validación

## 1. Filosofía de Pruebas
En MyBookConnect, ninguna funcionalidad se da por concluida sin pruebas automatizadas que cubran:
- Casos de éxito y flujos principales.
- Casos límite y validaciones de errores.
- Pruebas de regresión que impidan la reintroducción de fallos pasados.
- Pruebas de integración contra contenedores reales de PostgreSQL y Redis.

---

## 2. Pruebas de Backend con Pytest

El backend utiliza `pytest`, `pytest-django`, `pytest-asyncio` y `pytest-cov`:

### Ejecución de Pruebas
```bash
# Ejecutar toda la suite (307 tests)
docker compose exec -T backend pytest -q

# Ejecutar una suite específica con detalle
docker compose exec -T backend pytest -v tests/test_phase43_performance.py

# Ejecutar con reporte de cobertura de código
docker compose exec -T backend pytest --cov=. --cov-report=term-missing
```

### Principios de Testing en Backend
1. **Acceso a Base de Datos:** Usar el decorador `@pytest.mark.django_db`.
2. **Transacciones y Savepoints en Postgres:** Cuando una prueba espera una excepción de integridad (`IntegrityError`), envolver la sentencia con `with transaction.atomic(): with pytest.raises(IntegrityError):` para evitar que la transacción quede en estado abortado.
3. **Control de Consultas N+1:** Utilizar la fixture `django_assert_num_queries(N)` para fijar el número exacto de consultas esperadas.

---

## 3. Pruebas de Frontend con Vitest y Testing Library

El frontend utiliza `vitest`, `@testing-library/react` y `@testing-library/jest-dom/vitest`:

### Ejecución de Pruebas
```bash
cd frontend

# Ejecutar tests una sola vez
npx vitest run

# Modo interactivo con recarga en caliente
npm run test

# Verificación de tipado estricto sin emitir código
npm run typecheck
```

### Principios de Testing en Frontend
1. **Simulación de API:** Utilizar `globalThis.fetch = vi.fn()`.
2. **Consultas Semánticas:** Priorizar consultas accesibles por rol (`screen.getByRole`) o texto visible (`screen.getByText`).
3. **Desambiguación:** En caso de textos que se repitan en elementos complementarios, utilizar `screen.getAllByText(...)[0]` o selectores por `data-testid`.
