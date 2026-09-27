# Política de Moderación de Contenido y Seguridad Social

**Documento Normativo de la Plataforma MyBookConnect**  
**Versión:** 1.0.0  
**Fecha de Entrada en Vigor:** Septiembre 2026  
**Ámbito:** Usuarios, Reseñas, Comentarios, Mensajes de Chat y Listas de Lectura (Roadmap Fase 16 - Sección 21)

---

## 1. Declaración de Principios

MyBookConnect es una comunidad literaria orientada al descubrimiento, el diálogo constructivo y el intercambio de lecturas. Para salvaguardar la integridad de los miembros y la calidad de la experiencia social, se definen las siguientes políticas de conducta y moderación de cumplimiento obligatorio.

---

## 2. Tipologías de Infracción y Criterios Operativos

### 2.1. Spam y Publicidad no Deseada (`SPAM`)
- **Definición:** Publicación repetitiva, no solicitada o masiva de enlaces comerciales, promociones externas, venta de servicios, esquemas piramidales o generación automatizada de reseñas/comentarios mediante bots o scripts.
- **Acción Inmediata:** Ocultación instantánea del contenido infractor (`HIDE_CONTENT`) y evaluación para suspensión temporal o definitiva de la cuenta en caso de reincidencia o actividad automatizada.

### 2.2. Acoso, Intimidación y Hostigamiento (`HARASSMENT`)
- **Definición:** Ataques personales sistemáticos, insultos denigrantes, persecución en reseñas o mensajes privados, doxxing (divulgación de datos privados de terceros sin consentimiento) o incitación al linchamiento digital.
- **Acción Inmediata:** Silenciamiento disciplinario preventivo (`MUTE_USER_24H` / `MUTE_USER_7D`) u ocultación de mensajes/comentarios, escalable a baneo permanente (`BAN_USER`).

### 2.3. Contenido Ilegal o Perjudicial (`ILLEGAL_CONTENT`)
- **Definición:** Material que vulnere la legislación vigente, incluyendo pornografía infantil, apología del terrorismo, amenazas creíbles de daño físico a personas o bienes, estafas financieras o difusión de sustancias ilícitas.
- **Acción Inmediata:** Ocultación y purgado inmediato, suspensión permanente irrevocable de la cuenta (`BAN_USER`), preservación de evidencias con cadena de custodia en `AuditLog` y reporte a las autoridades competentes si procede.

### 2.4. Suplantación de Identidad (`IMPERSONATION`)
- **Definición:** Creación de perfiles destinados a engañar a la comunidad haciéndose pasar por autores reales, figuras públicas, moderadores o administradores de MyBookConnect.
- **Acción Inmediata:** Bloqueo y baneo preventivo de la cuenta infractora (`BAN_USER`) y solicitud de verificación oficial de identidad en caso de reclamaciones legítimas.

### 2.5. Infracción de Propiedad Intelectual y Derechos de Autor (`COPYRIGHT`)
- **Definición:** Publicación no autorizada de obras completas, capítulos inéditos sujetos a copyright, transcripciones piratas o enlaces directos a sitios de descarga ilegal.
- **Acción Inmediata:** Retirada cautelar del contenido bajo procedimiento formal de Notificación y Retirada (DMCA o normativa europea equivalente).

### 2.6. Spoilers sin Advertencia (`SPOILER`)
- **Definición:** Revelación no señalizada de giros argumentales clave o finales de libros en reseñas públicas, comentarios o títulos de listas de lectura accesibles a terceros.
- **Acción Inmediata:** Ocultación de la reseña o marcado de advertencia para que el autor rectifique y aplique el formato de spoiler.

---

## 3. Matriz de Estados de Tramitación de Denuncias

El ciclo de vida de un expediente de denuncia sigue una máquina de estados determinista (Roadmap 21.3):

| Estado Canónico | Alias Aceptado | Descripción Operativa |
|---|---|---|
| `OPEN` | `open` | Denuncia registrada por un usuario autenticado y pendiente de triaje. |
| `UNDER_REVIEW` | `investigating` | Expediente asignado y bajo análisis activo por un moderador o administrador. |
| `RESOLVED` | `resolved` | Dictamen emitido y medidas disciplinarias ejecutadas (ocultación, silenciamiento, baneo). |
| `REJECTED` | `dismissed` | Denuncia infundada o desestimada formalmente con notas justificativas. |

---

## 4. Acciones Disciplinarias y Registro de Auditoría

Toda decisión disciplinaria tomada por el equipo de moderación debe registrar de forma inmutable los siguientes datos en `AuditLog`:
1. `actor`: Moderador que ejecutó la acción.
2. `action`: Tipo de acción (`MODERATION_RESOLVE`, `MODERATION_REJECT`, `CONTENT_HIDE`, `CONTENT_RESTORE`, `MODERATOR_MUTE`, `MODERATOR_UNMUTE`, `USER_BAN`, `USER_UNBAN`).
3. `target`: Entidad sancionada (`User`, `Review`, `ReviewComment`, `Message`, `ReadingList`).
4. `metadata`: Justificación, identificadores, marcas temporales y duración de penalizaciones temporales.

---

## 5. Prevención de Abuso y Limitación de Tasa (Rate Limiting)

Para proteger a la comunidad y a la plataforma contra ataques de denegación de servicio o campañas de acoso coordinadas, se aplican los siguientes límites estrictos por usuario (Roadmap 21.4):

- **Denuncias (`reports`):** Máximo 10 solicitudes por hora.
- **Seguimiento (`follows`):** Máximo 60 operaciones de follow/unfollow por hora.
- **Comentarios (`comments`):** Máximo 30 comentarios publicados por minuto.
- **Interacciones (`likes`):** Máximo 60 likes/unlikes por minuto.
- **Mensajería (`messages`):** Máximo 60 mensajes directos por minuto.

Las solicitudes que excedan estas tasas reciben una respuesta HTTP `429 Too Many Requests` (Throttled) con la cabecera `Retry-After`.
