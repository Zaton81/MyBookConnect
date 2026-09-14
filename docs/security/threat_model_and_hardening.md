# Modelo de Amenazas y Endurecimiento de Seguridad

## 1. Modelo de Amenazas Identificadas y Mitigaciones

### 1.1. Robo o Suplantación de Tokens JWT
- **Riesgo:** Un atacante intercepta un token de acceso y lo utiliza para suplantar la identidad de la víctima.
- **Mitigación:** 
  - Tiempo de expiración ultracorto del `access_token` (15 minutos).
  - Rotación obligatoria del `refresh_token` en cada uso (`ROTATE_REFRESH_TOKENS = True`).
  - Lista negra persistente en base de datos (`BlacklistedToken`) que invalida inmediatamente el token al hacer logout.
  - Almacenamiento preferente en cookies con flags `HttpOnly`, `Secure` y `SameSite=Lax`.

### 1.2. Ataques de Inyección SQL y XSS
- **Riesgo:** Inserción de código malicioso en campos de búsqueda, reseñas o biografías.
- **Mitigación:**
  - Consultas parametrizadas obligatorias a través de Django ORM.
  - Sanitización estricta del HTML en frontend con `DOMPurify 3.4.15` antes de renderizar campos enriquecidos de Tiptap.
  - Escapado contextual de cadenas en plantillas y respuestas JSON.

### 1.3. Inyección de Prompts en el Subsistema de IA
- **Riesgo:** Ataques de *jailbreaking* donde el usuario intenta forzar al LLM a ejecutar instrucciones no autorizadas o revelar información confidencial.
- **Mitigación:**
  - `PromptSecurityService`: Análisis de expresiones regulares y heurísticas para bloquear patrones de manipulación del sistema prompt.
  - Validación de esquemas estructurados de salida.

### 1.4. Denegación de Servicio y Escaneos Abusivos
- **Riesgo:** Ataques de fuerza bruta sobre login o peticiones masivas a endpoints costosos.
- **Mitigación:**
  - Rate limiting configurado en DRF con respaldos en Redis (`AnonRateThrottle: 100/day`, `UserRateThrottle: 1000/day`).
  - Throttles dedicados en autenticación y búsqueda.
