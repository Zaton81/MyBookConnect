# Marco Legal, Privacidad y Gobernanza de Datos para Fase Beta (Fase 18)

## 1. Resumen Ejecutivo
Este documento formaliza la política legal, el modelo de tratamiento de datos y los compromisos de transparencia de **MyBookConnect** con carácter previo a la apertura a usuarios reales (Fase Beta).

La arquitectura jurídica y técnica se ha diseñado bajo los principios de **Privacy by Design** y **Privacy by Default**, cumpliendo con:
- **RGPD (Reglamento UE 2016/679):** Protección de personas físicas en el tratamiento de datos personales.
- **LOPD-GDD (Ley Orgánica 3/2018):** Protección de datos y garantía de derechos digitales en España.
- **LSSI-CE (Ley 34/2002):** Servicios de la sociedad de la información y comercio electrónico.
- **DSA (Reglamento UE 2022/2065):** Ley de Servicios Digitales y régimen de responsabilidad de intermediarios.
- **AI Act (Reglamento de Inteligencia Artificial de la UE):** Transparencia algorítmica y prohibición de uso de datos personales para entrenamiento no consentido de modelos fundacionales.

---

## 2. Inventario de Datos Personales Recogidos y Finalidades

| Categoría | Campos de Datos | Finalidad Principal | Base Jurídica (RGPD) |
| :--- | :--- | :--- | :--- |
| **Cuenta e Identidad** | `username`, `email`, contraseña (hash PBKDF2), `date_joined`, marcas de aceptación de términos y privacidad. | Registro, autenticación mediante JWT, verificación y contacto de seguridad. | Art. 6.1.b (Ejecución contractual) |
| **Perfil Voluntario** | `first_name`, `last_name`, `bio`, `avatar`, enlaces web y redes sociales. | Personalización de la experiencia de usuario y visibilidad comunitaria. | Art. 6.1.a (Consentimiento del titular) |
| **Actividad Lectora** | Libros en biblioteca (`UserBook`), estados de lectura (`status`), progreso de páginas, fechas, calificaciones (1 a 5 estrellas), notas personales. | Gestión de la estantería personal, estadísticas de lectura y cálculo de retos anuales. | Art. 6.1.b (Ejecución contractual) |
| **Interacción Social** | Listas de lectura (`ReadingList`), reseñas públicas (`Review`), comentarios (`ReviewComment`), follows, bloqueos y mensajería en vivo. | Comunicación comunitaria entre lectores y debates literarios. | Art. 6.1.b (Ejecución contractual) |
| **Seguridad y Auditoría** | Dirección IP, User-Agent, tipo de acción en `AuditLog`. | Detección de intrusiones, prevención de fuerza bruta, custodia técnica y auditoría legal. | Art. 6.1.f (Interés legítimo) y Art. 6.1.c (Obligación legal) |

---

## 3. Proveedores y Encargados del Tratamiento (Terceros)

Todos los proveedores externos de infraestructura han sido seleccionados bajo la premisa de soberanía de datos y estricto cumplimiento del RGPD:

1. **Infraestructura de Alojamiento y Servidores:** Centros de datos ubicados en el Espacio Económico Europeo (Alemania/Finlandia) o proveedores conformes con Data Privacy Framework (DPF).
2. **Bases de Datos y Caché:** Instancias de PostgreSQL y Redis operadas en redes privadas aisladas (`internal: true`) sin exposición directa a redes públicas.
3. **Servicios de Inteligencia Artificial (Búsqueda Semántica y Recomendación):**
   - **Garantía Incondicional:** Los datos personales de los usuarios **NO se transmiten ni se emplean para entrenar modelos de Inteligencia Artificial de terceros**.
   - Los embeddings vectoriales se computan sobre metadatos literarios de dominio público (título, autor, sinopsis) y se almacenan de forma matemática abstracta en la extensión `pgvector`.
4. **Fuentes Bibliográficas Públicas:** Google Books API y OpenLibrary. Se emplean exclusivamente para enriquecer metadatos editoriales (ISBN, portadas, fechas de publicación). No se comparte ninguna información identificativa del usuario con estas APIs.
5. **Servicios de Correo Transaccional:** Pasarela SMTP para entrega de confirmaciones de email y restablecimiento de contraseña.

---

## 4. Filosofía de Analytics y Ausencia de Tracking Invasivo

En estricta observancia del principio rector: **"No introducir tracking innecesario"**:
- **Cero trackers entre sitios:** No se integran librerías invasivas como Google Analytics con User ID persistente, Meta Pixel, TikTok for Business ni herramientas de fingerprinting biométrico o de hardware.
- **Métricas anónimas:** Las métricas operativas (volumen de lecturas diarias, peticiones por minuto, tiempos de respuesta p95) se agregan a nivel de servidor sin crear perfiles comerciales ni vender información a brokers de datos.

---

## 5. Política de Cookies y Almacenamiento Local

- **Cookies Técnicas Estrictamente Necesarias:**
  - Token JWT de autenticación y refresco (permite mantener la sesión activa con rotación segura).
  - Token CSRF defensivo contra ataques cross-site.
  - Cookies de balanceo de carga para el canal WebSocket de mensajería (Daphne).
- **Almacenamiento Local (`localStorage`):**
  - Preferencia de tema visual claro/oscuro (`theme`).
  - Filtros locales temporales de estantería.
- **Exención de consentimiento previo:** Al carecer de rastreadores comerciales de terceros, el usuario no sufre la fricción de muros de consentimiento obstructivos, disponiendo no obstante de un panel de configuración accesible en el pie de página.

---

## 6. Plazos de Retención y Ejercicio de Derechos

### 6.1 Ciclo de Retención
- **Cuentas activas:** Los datos se conservan mientras el usuario mantenga su cuenta abierta en la plataforma.
- **Inactividad prolongada:** Transcurridos 24 meses sin inicio de sesión, se remitirá un aviso de reactivación antes de proceder a la disociación.

### 6.2 Derecho a la Supresión / Olvido (RGPD Art. 17)
Implementado mediante el mecanismo atómico de la Fase 17:
- Reautenticación por contraseña y confirmación explícita `"ELIMINAR"`.
- Anonimización inmediata e irreversible: conversión a `deleted_user_<id>`, email a `deleted_<id>_<timestamp>@deleted.local`, destrucción de contraseña, supresión de biografía y avatar.
- Desvinculación de relaciones sociales (`following`, `followers`, bloqueos) y ocultación de listas.
- Soft-delete de comentarios y revocación global de sesiones JWT en lista negra.
- Preservación exclusivamente disociada de reseñas públicas para mantener la integridad del catálogo colectivo.

### 6.3 Derecho a la Portabilidad (RGPD Art. 20)
- Generación de informe descargable en formato JSON estructurado conteniendo biblioteca, calificaciones, reseñas, comentarios y listas.

---

## 7. Canales Oficiales de Contacto
- **Soporte y Ayuda:** `soporte@mybookconnect.local`
- **Privacidad y DPO:** `privacidad@mybookconnect.local`
- **Moderación y Contenido (DSA):** `moderacion@mybookconnect.local`
- **Propiedad Intelectual:** `copyright@mybookconnect.local`
