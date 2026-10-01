# Checklist Operativo y Despliegue de Beta Cerrada — MyBookConnect

## 1. Visión y Objetivos de la Beta Cerrada
El objetivo de la **Beta Cerrada** es validar la estabilidad, rendimiento y usabilidad de **MyBookConnect** con un grupo controlado de usuarios reales antes de abrir la plataforma al público general.

- **Cohorte Inicial**: 10–30 usuarios (lectores activos, autores independientes y perfiles técnicos).
- **Cohorte Secundaria**: 50–100 usuarios (tras superar los primeros 14 días sin incidencias críticas P0/P1).

---

## 2. Checklist de Validación Funcional Previa (17 Puntos del Roadmap)

| Módulo | Componente Validado | Estado | Notas Operativas |
| :--- | :--- | :--- | :--- |
| **01. Registro** | Creación de cuenta con email/password y Google OAuth | ✅ Validado | Verificación de email obligatoria activada. |
| **02. Login** | Autenticación JWT con rotación y blacklist | ✅ Validado | Token access TTL 15 min, refresh rotativo en Redis. |
| **03. Recuperación** | Password reset seguro con tokens de un solo uso | ✅ Validado | Plantilla de correo y límite de peticiones. |
| **04. Biblioteca** | Gestión de `UserBook` (Want to read, Reading, Read) | ✅ Validado | Calificaciones normalizadas 1–5 estrellas. |
| **05. Búsqueda** | Búsqueda unificada híbrida (Trigram + Vectorial) | ✅ Validado | Fallback automático si Ollama/embeddings no responden. |
| **06. Reseñas** | Creación, edición y comentarios en reseñas | ✅ Validado | `Review.rating` estrictamente de 1 a 5 estrellas. |
| **07. Follows** | Seguir usuarios, solicitudes y aceptación | ✅ Validado | Respeta perfiles privados con solicitud previa. |
| **08. Privacidad** | Niveles `public`, `friends`, `private` | ✅ Validado | `PrivacyService` con retorno 404 anti-enumeración. |
| **09. Bloqueos** | Bloqueo bidireccional y silenciado | ✅ Validado | Oculta bidireccionalmente perfil, feed, mensajes y comentarios. |
| **10. Feed** | Feed social cronológico ordenado | ✅ Validado | Soporta ocultar publicaciones individuales (`HiddenActivity`). |
| **11. Listas** | Colecciones temáticas y clonación atómica | ✅ Validado | Clonación atómica privada por defecto con contador de aperturas. |
| **12. Recomendaciones** | Motor híbrido ponderado v3 | ✅ Validado | Cold start integrado con categorías favoritas del onboarding. |
| **13. Mensajería** | Chat en tiempo real vía WebSockets | ✅ Validado | Handshake seguro mediante tickets de vida corta `/ws-ticket/`. |
| **14. Moderación** | Cola de reportes y acciones de castigo | ✅ Validado | 5 throttles resilientes contra spam de reportes o interacciones. |
| **15. Cuenta RGPD** | Supresión atómica Art. 17 y exportación Art. 20 | ✅ Validado | Anonimización completa disociando telemetría histórica. |
| **16. Backups** | Copias PostgreSQL cifradas AES-256 | ✅ Validado | Scripts `backup_db.sh` y prueba de restore documentada. |
| **17. Observabilidad** | Logs estructurados JSON y sondas `/health/` | ✅ Validado | Sondas `/health/live` y `/health/ready` aisladas sin secretos. |

---

## 3. Control de Acceso e Invitaciones (`BetaInvitation`)

Para salvaguardar la experiencia de la cohorte, el acceso a la beta se gestiona mediante códigos de invitación:

- **Generación Administrativa**:
  `POST /api/v1/beta/admin/invitations/` (requiere permisos `IsAdminUser`).
  ```json
  {
    "code": "BETA-LECTOR-01",
    "invited_email": "lector1@example.com",
    "max_uses": 1,
    "expires_at": "2026-10-31T23:59:59Z"
  }
  ```
- **Verificación Pública**:
  `POST /api/v1/beta/invitations/verify/` (disponible antes del registro).
  Comprueba vigencia temporal, estado activo y cupo restante (`uses_remaining`).

---

## 4. Circuito de Feedback In-App (`BetaFeedback`)

Los usuarios beta disponen de un disparador flotante persistente en la interfaz (`BetaFeedbackModal`) para enviar observaciones en tiempo real sin salir de su sesión de lectura o navegación.

### 4.1 Categorías Obligatorias de Feedback
1. **`bug` (🐛 Error técnico)**: Comportamientos erróneos, fallos de API o botones inoperativos.
2. **`confusing_ux` (❓ Experiencia confusa)**: Diseños ambiguos, flujos difíciles de entender o falta de claridad.
3. **`missing_feature` (💡 Funcionalidad ausente)**: Sugerencias de valor o herramientas esperadas por los lectores.
4. **`performance` (⚡ Rendimiento)**: Lentitud, tiempos de carga elevados o problemas de fluidez.
5. **`privacy_concern` (🔒 Privacidad)**: Inquietudes sobre visibilidad de lecturas, datos o actividad.
6. **`recommendation_quality` (🎯 Calidad de recomendaciones)**: Pertinencia o incongruencias en libros sugeridos.
7. **`general_feedback` (💬 Opinión general)**: Impresiones globales sobre la propuesta de MyBookConnect.

### 4.2 Flujo de Triaje de Incidencias
- Todo nuevo envío entra en estado **`new`**.
- El equipo de administración revisa y clasifica a **`in_review`** en `GET /api/v1/beta/admin/feedback/`.
- Al resolver o aplicar una corrección, se actualiza a **`resolved`** con notas técnicas (`admin_notes`).
- En caso de reportes duplicados o no aplicables, se marca como **`dismissed`**.

### 4.3 Acuerdos de Nivel de Servicio (SLA) para la Beta
- **Incidencias P0 (bloqueo de acceso o fallo de datos)**: Respuesta e investigación en menos de 4 horas.
- **Bugs P1 / UX confusa**: Clasificación y triaje en menos de 24 horas.
- **Sugerencias y Feedback General**: Revisión semanal de tendencias y propuestas de producto.
