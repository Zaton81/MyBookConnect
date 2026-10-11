# Política de Gestión y Rotación de Secrets — MyBookConnect

> **Fase del Roadmap:** BLOQUE A — Fase A1 (Congelación y Baseline de Seguridad)  
> **Fecha:** Octubre 2026  
> **Estado:** Vigente y Obligatorio  

---

## 1. Principio Fundamental: Cero Secrets en Control de Versiones

Ninguna credencial real, clave simétrica, token de acceso, contraseña de base de datos o certificado puede residir en el árbol de Git bajo ninguna circunstancia.

### Reglas de Gitignore:
- El archivo `.env` y cualquier variación `.env.*` (salvo plantillas explícitas `.env.example` y `.env.production.example`) están estrictamente bloqueados por `.gitignore`.
- Las plantillas `.example` solo contienen valores ficticios explicativos, nunca valores válidos de producción ni desarrollo compartido.
- Las copias de seguridad (`backups/`) y volcados SQL (`*.sql`, `*.sql.gz`) están ignorados por Git.

---

## 2. Inventario de Secrets Críticos

| Secret | Propósito | Entorno | Método de Inyección |
| :--- | :--- | :--- | :--- |
| `SECRET_KEY` | Firma criptográfica de tokens JWT, sesiones Django y CSRF | Backend | Variable de entorno / Docker secret |
| `POSTGRES_PASSWORD` | Autenticación del usuario de base de datos PostgreSQL | DB / Backend | Variable de entorno / Docker secret |
| `BACKUP_ENCRYPTION_KEY` | Clave de cifrado simétrico AES-256-CBC para volcados de DB | Scripts / Host | Variable en ejecución o inyección de vault |
| `AI_API_KEY` | Clave de acceso a proveedores externos de LLM/Embeddings | Backend | Variable de entorno |
| `AMAZON_PAAPI_SECRET_KEY` | Clave secreta para firma canónica AWS SigV4 de afiliados | Backend | Variable de entorno |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Secreto OAuth 2.0 para federación de identidades Google | Backend | Variable de entorno |

---

## 3. Procedimiento de Rotación de Secrets

### 3.1 Rotación de `SECRET_KEY` (Django):
1. **Consecuencia:** Invalida inmediatamente todas las sesiones activas y tokens JWT en vuelo.
2. **Procedimiento:**
   - Generar nueva clave pseudoaleatoria criptográficamente segura (mínimo 64 caracteres):
     ```bash
     python -c "import secrets; print(secrets.token_urlsafe(64))"
     ```
   - Actualizar la variable `SECRET_KEY` en el entorno o gestor de secrets.
   - Reiniciar el contenedor `booksocial-backend` (`docker compose restart backend`).

### 3.2 Rotación de Contraseña de Base de Datos (`POSTGRES_PASSWORD`):
1. Ejecutar backup previo de la base de datos (según Fase A1 / B2).
2. Modificar la contraseña del usuario `booksocial` en PostgreSQL:
   ```sql
   ALTER USER booksocial WITH PASSWORD 'nuevo_password_robusto';
   ```
3. Actualizar `POSTGRES_PASSWORD` y `DATABASE_URL` en el entorno de backend.
4. Reiniciar servicios para aplicar la nueva conexión sin downtime prolongado.

### 3.3 Rotación de Claves de Proveedores Externos (IA / Amazon PA-API):
1. Generar nuevo par de claves en la consola del proveedor (Amazon Associates / OpenAI / OpenRouter).
2. Actualizar las variables en el host/contenedor.
3. Verificar operatividad con las pruebas de integración (`pytest tests/test_amazon_books_provider.py`).
4. Revocar las credenciales antiguas en la consola del proveedor.

---

## 4. Auditoría Continua y Prevención de Fugas

- Todo commit debe pasar por la inspección de pre-commit (`validate_commit_msg.py` y linters).
- Las herramientas de observabilidad (`observability.py`) ofuscan activamente cabeceras de autorización (`Authorization`, `Cookie`, `Set-Cookie`, `password`, `secret_key`) en todos los logs JSON estructurados.
