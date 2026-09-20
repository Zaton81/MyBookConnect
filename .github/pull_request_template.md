## Descripción del Cambio
<!-- Explica de forma concisa qué problema resuelve este PR o qué funcionalidad añade. -->

## Tipo de Cambio (Conventional Commits)
- [ ] `feat`: Nueva característica o funcionalidad
- [ ] `fix`: Corrección de un error o bug
- [ ] `refactor`: Mejora interna de código sin impacto funcional
- [ ] `perf`: Optimización de rendimiento
- [ ] `security`: Parche o endurecimiento de seguridad
- [ ] `test`: Añadido o actualización de pruebas
- [ ] `docs`: Modificación o creación de documentación
- [ ] `chore`: Tareas de mantenimiento o dependencias

---

## Checklist de Definition of Done (DoD)
Todo PR debe cumplir los siguientes 13 criterios antes de ser aprobado y fusionado en `develop` o `main`:

- [ ] **1. Modelo:** Diseño sin duplicidad, restricciones (`UniqueConstraint`), índices adecuados y tipos correctos.
- [ ] **2. Migración:** Generada limpiamente (`makemigrations`), reversible y sin operaciones bloqueantes.
- [ ] **3. Serializer:** Validación estricta, sanitización XSS (`nh3`) y prevención de consultas N+1.
- [ ] **4. API:** URLs canónicas con barra final, códigos de estado HTTP semánticos y contrato de error RFC 7807.
- [ ] **5. Permisos:** Autorización granular, permisos por objeto (`HasObjectPermission`) y respeto a la privacidad.
- [ ] **6. Tests backend:** Coberura con `pytest-django`, casos límite, errores y servicios externos aislados con mocks.
- [ ] **7. Cliente frontend:** Tipos TypeScript sincronizados con OpenAPI, manejo de estados en TanStack Query.
- [ ] **8. UI:** Diseño responsivo con TailwindCSS, estados de carga, estados vacíos y accesibilidad básica.
- [ ] **9. Tests frontend:** Componentes y flujos testeados con Vitest y React Testing Library.
- [ ] **10. Documentación:** Docstrings, documentación en `docs/` actualizada y entrada en `CHANGELOG.md` si aplica.
- [ ] **11. OpenAPI:** Anotaciones `@extend_schema`, validación con `drf-spectacular` y tipos regenerados.
- [ ] **12. CI:** Pipelines de integración continua en verde (`ruff check`, `tsc --noEmit`, tests).
- [ ] **13. Logs si son necesarios:** Logging estructurado con niveles adecuados y sin exposición de datos sensibles.

---

## Verificación Local Realizada
<!-- Comandos ejecutados para validar el cambio antes de abrir el PR -->
- [ ] `bash scripts/verify_dod.sh`
- [ ] `bash scripts/verify_release.sh`
- [ ] `npm --prefix frontend run typecheck`
