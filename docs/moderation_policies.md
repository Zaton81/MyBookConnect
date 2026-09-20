# Políticas de Moderación de Contenido y Normas de la Comunidad

> **Versión:** 1.0.0  
> **Fecha de entrada en vigor:** Septiembre 2026  
> **Estado:** Aprobado — Marco vinculante para moderación humana y preparación para automatización IA (Fase 58).

---

## 1. Misión y Principios Fundamentales

**MyBookConnect** es una plataforma orientada a fomentar el intercambio cultural, la lectura crítica y el descubrimiento literario en un ambiente respetuoso, constructivo y seguro para toda la comunidad lectora.

### Principios Rectores:
1. **Libertad de Expresión y Crítica Constructiva**: Fomentamos la diversidad de opiniones y análisis literarios, incluso cuando discrepen fuertemente sobre obras o estilos.
2. **Respeto y Dignidad Humana**: Ningún desacuerdo justifica la agresión, el hostigamiento, el lenguaje denigrante ni la incitación al odio contra personas o colectivos.
3. **Protección del Lector**: Salvaguardamos la experiencia de lectura mediante la obligación de señalizar adecuadamente los destripes argumentales (*spoilers*) y el filtrado riguroso de publicidad abusiva (*spam*).
4. **Proporcionalidad y Trazabilidad**: Toda sanción disciplinaria debe responder a una infracción tipificada, aplicarse de forma gradual y quedar registrada de forma inmutable en el registro de auditoría (`AuditLog`).

---

## 2. Tipología y Clasificación de Infracciones

Las conductas contrarias a las directrices de la comunidad se clasifican en tres niveles de gravedad:

### Nivel 1 — Infracciones Leves o Técnicas
- **Spam o Publicidad No Deseada (`SPAM`)**:
  - Enlaces de afiliados engañosos, venta no autorizada de servicios o repetición masiva de mensajes/reseñas idénticas.
- **Spoilers No Advertidos (`SPOILER`)**:
  - Revelación de giros de trama o finales de libros en reseñas, títulos o comentarios públicos sin activar la etiqueta correspondiente.
- **Contenido Desubicado u Off-Topic Continuado**:
  - Uso de secciones de reseñas como foro de disputas personales ajenas a la lectura o literatura.

### Nivel 2 — Infracciones Moderadas o Tóxicas
- **Acoso e Intimidación (`HARASSMENT`)**:
  - Comentarios despectivos sistemáticos dirigidos a un usuario o autor, provocación deliberada (*flaming*) o acoso a través de mensajes directos.
- **Contenido Inapropiado o Explícito (`INAPPROPRIATE`)**:
  - Lenguaje obsceno desmedido, contenido sexualmente explícito o imágenes inadecuadas en avatares y descripciones.
- **Violación de Derechos de Autor (`COPYRIGHT`)**:
  - Difusión no autorizada de textos completos, enlaces de descarga pirata de libros protegidos o apropiación de reseñas ajenas (plagio).

### Nivel 3 — Infracciones Graves o Críticas
- **Discurso de Odio o Violencia (`HATE_SPEECH`)**:
  - Ataques, discriminación o amenazas basadas en raza, origen étnico, nacionalidad, religión, orientación sexual, identidad de género, discapacidad o edad.
- **Doxxing y Revelación de Datos Sensibles**:
  - Publicación no consentida de información privada (nombres reales, direcciones físicas, números de teléfono, correos personales).
- **Abuso Sistémico o Evasión de Sanciones**:
  - Creación de cuentas secundarias (*sockpuppets*) para evadir bloqueos, silenciamientos o suspensiones previas.

---

## 3. Matriz de Herramientas de Moderación

El sistema dispone de 7 herramientas complementarias distribuidas entre la autonomía del usuario y la intervención disciplinaria de moderadores:

| Herramienta | Ámbito | Ejecutante | Descripción y Alcance |
| :--- | :--- | :--- | :--- |
| **`report`** | Preventivo | Cualquier usuario autenticado | Envía un expediente motivado a la cola de moderación sobre usuarios, reseñas, comentarios o mensajes directos. |
| **`review`** | Administrativo | Moderador / Administrador | Gestión de la cola de denuncias: análisis de evidencias, cambio de estado (`OPEN`, `UNDER_REVIEW`, `RESOLVED`, `REJECTED`) y aplicación de sanciones. |
| **`hide`** | Disciplinario | Moderador / Administrador | Ocultación inmediata de contenido infractor (`is_moderated=True` o `deleted_at`). Deja de ser visible para la comunidad. |
| **`restore`** | Correctivo | Moderador / Administrador | Reactivación y visibilización de contenido previamente ocultado tras resolver una apelación favorable o corregir un falso positivo. |
| **`mute` (Social)** | Preventivo | Cualquier usuario | Silencia discretamente a otro usuario. Sus reseñas, comentarios y notificaciones quedan ocultos para quien lo silencia, sin alertar al usuario silenciado. |
| **`mute` (Disciplinario)**| Disciplinario | Moderador / Administrador | Restricción temporal de escritura impuesta por moderación (`muted_until`). Impide crear reseñas, comentarios y enviar mensajes directos durante 24h, 7 días o duración personalizada. |
| **`block`** | Defensivo | Cualquier usuario | Bloqueo bidireccional severo entre dos usuarios. Impide seguimiento, mensajería directa e interacción recíproca. |
| **`ban`** | Sancionador | Moderador / Administrador | Suspensión total de la cuenta (`is_active=False`). Impide el acceso y la autenticación en la plataforma. Protegido frente a auto-baneo y baneo de administradores. |

---

## 4. Escala Progresiva de Sanciones Disciplinarias

Salvo en casos de extrema gravedad (Nivel 3 con riesgo inminente), la moderación aplica el siguiente protocolo progresivo:

```text
[Infracción detectada]
         │
         ▼
 1. Apercibimiento (Warning) + Ocultación del contenido (Hide)
         │  (Reincidencia en 30 días)
         ▼
 2. Silenciamiento Temporal (Mute 24 Horas)
         │  (Nueva reincidencia)
         ▼
 3. Silenciamiento Extendido (Mute 7 Días)
         │  (Tercera reincidencia o Nivel 2 agravado)
         ▼
 4. Suspensión Temporal de Cuenta (Ban 30 Días)
         │  (Infracción de Nivel 3 o reincidencia tras suspensión)
         ▼
 5. Expulsión Definitiva de la Plataforma (Ban Permanente)
```

---

## 5. Protocolo de Apelaciones y Trazabilidad

1. **Notificación al Usuario Sancionado**:
   - Todo usuario que reciba una sanción disciplinaria (`mute` disciplinario o `ban`) es informado del motivo tipificado y la fecha de expiración de la medida.
2. **Canal de Apelación**:
   - El usuario puede solicitar la revisión de la medida contactando al equipo a través de los canales de soporte establecidos o respondiendo a la notificación disciplinaria.
3. **Registro Inmutable (`AuditLog`)**:
   - Toda acción de moderación (`MODERATION_RESOLVE`, `CONTENT_HIDE`, `CONTENT_RESTORE`, `USER_BAN`, `USER_UNBAN`, `MODERATOR_MUTE`, `MODERATOR_UNMUTE`) registra:
     - Identificador del moderador actuante (`actor`).
     - Objeto o usuario afectado (`content_object`, `target_repr`).
     - Dirección IP y User-Agent de la solicitud.
     - Metadatos con justificación textual y marca temporal precisa.

---

## 6. Salvaguardas y Requerimientos para Futura Automatización IA

Antes de activar modelos o agentes automáticos de moderación basada en inteligencia artificial (ej. LLMs o clasificadores semánticos en fases posteriores del roadmap), deben cumplirse obligatoriamente las siguientes salvaguardas:

1. **Principio *Human-in-the-Loop***:
   - La IA **nunca** ejecutará suspensiones definitivas (`ban`) de forma autónoma. Las sanciones severas requerirán siempre confirmación humana expresa.
2. **Umbrales de Confianza Calibrados**:
   - Solo se permitirá ocultación automática preventiva (`hide`) cuando la confianza del clasificador supere el **95%** en categorías de odio explícito o spam evidente, generando de inmediato un reporte prioritario en la cola para validación de un moderador humano en menos de 24 horas.
3. **Mitigación de Sesgos Culturales y Literarios**:
   - El modelo de IA debe estar ajustado para diferenciar citas literarias ficticias (ej. fragmentos de novelas clásicas o de misterio) de ataques reales entre usuarios de la plataforma.
4. **Auditoría de Falsos Positivos**:
   - Revisión periódica semanal de expedientes resueltos para calcular la tasa de falsos positivos y reentrenar o ajustar los umbrales de los prompts de inferencia.
