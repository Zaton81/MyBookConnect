# Moderación Comunitaria, Auditoría y Privacidad

## 1. Sistema de Moderación y Denuncias
Para preservar la integridad de la comunidad lectora, MyBookConnect cuenta con herramientas de moderación:

### Reportes de Contenido
- Cualquier usuario puede reportar reseñas, comentarios o perfiles por contenido inapropiado o spam.
- Cola de moderación administrativa con estados (`pending`, `reviewed`, `dismissed`, `action_taken`).
- Acciones de moderación: ocultación de reseña, aviso al usuario o suspensión de cuenta.

### Sistema de Erratas en Libros (`Errata`)
- Mecanismo comunitario donde los lectores reportan fallos tipográficos, discrepancias de ISBN o información errónea de portadas.
- Los administradores pueden aprobar y aplicar correcciones automáticamente al catálogo.

---

## 2. Niveles de Privacidad Granulares (`privacy_level`)

Cada lector controla quién tiene acceso a su biblioteca y actividad:
- **`public` (Público):** Cualquier usuario registrado o visitante puede ver la biblioteca y actividad del lector.
- **`followers_only` (Solo Seguidores):** Exclusivamente los usuarios aprobados que siguen al lector pueden acceder a su biblioteca.
- **`private` (Privado):** Únicamente el propio usuario puede visualizar su biblioteca, historial y estadísticas.

---

## 3. Registro de Auditoría y Trazabilidad
- `StructuredLoggingMiddleware` vincula cada acción con el `user_id` y `request_id`.
- Modificaciones críticas (cambio de contraseñas, edición de roles de administrador, baneos de cuentas) se registran en la tabla de auditoría con marca de tiempo UTC y dirección IP.
