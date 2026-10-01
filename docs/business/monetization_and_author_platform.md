# Estrategia de Monetización Ética y Plataforma de Autores (Fase 31)

Este documento describe el modelo de sostenibilidad económica, el sistema de afiliación transparente y la plataforma para autores de **MyBookConnect**, en conformidad con la **Sección 36 del Roadmap**.

---

## 1. Principios Rectores de Monetización

> *"No priorizar hasta validar retención. La publicidad y afiliación solo si: no perjudica UX, no manipula recomendaciones y está claramente identificada."*

MyBookConnect sustenta su modelo de negocio en tres pilares éticos no negociables:

1. **Invarianza Algorítmica:** Los enlaces comerciales o comisiones **NUNCA** influyen en los algoritmos de recomendación, en los resultados de búsqueda híbrida ni en el orden del catálogo. Todas las sugerencias se basan estrictamente en afinidad literaria, similitud semántica y calidad de lectura.
2. **Transparencia Total (Disclosure Obligatorio):** Todo enlace que pueda generar una comisión comercial está identificado de forma explícita ante el lector mediante el distintivo *"Afiliado / Patrocinado"* y una declaración legal clara.
3. **Núcleo de Comunidad 100% Gratuito:** El registro, la gestión de estanterías, las listas de lectura, la interacción social, las reseñas y las búsquedas son y serán siempre libres y accesibles para todos los usuarios.

---

## 2. Sistema de Afiliación de Amazon (Multiformato)

### 2.1. Configuración Centralizada
El tag de asociado de Amazon está configurado canónicamente como **`mybooksocial-21`**, gestionado de manera desacoplada mediante variables de entorno para permitir su modificación inmediata sin alterar la lógica de negocio:

- **Backend:** `AMAZON_AFFILIATE_TAG=mybooksocial-21` (`backend/mybookconnect/settings.py`)
- **Frontend:** `VITE_AMAZON_AFFILIATE_TAG=mybooksocial-21` (`frontend/src/components/ui/AmazonAdSlot.tsx`)

### 2.2. Soporte Multiformato
El servicio `AffiliateService` entrega enlaces adaptados a los tres principales hábitos de consumo literario:

| Formato | Destino en Amazon | Parámetro de Búsqueda |
| :--- | :--- | :--- |
| **Libro Físico (Papel)** | Página directa de producto `/dp/{isbn}` o búsqueda en categoría libros | `i=stripbooks` |
| **Ebook (Kindle)** | Tienda Kindle / Kindle Unlimited | `i=digital-text` |
| **Audiolibro (Audible)** | Catálogo de audiolibros narrados en Audible | `i=audible` |

### 2.3. Endpoints de la API REST
- `GET /api/v1/books/<id>/affiliate-links/`: Retorna los enlaces formateados con el tag activo, el nombre de la obra, autor y el texto de disclosure legal:
  ```json
  {
    "book_id": 42,
    "book_title": "Cien años de soledad",
    "author_name": "Gabriel García Márquez",
    "affiliate_tag": "mybooksocial-21",
    "disclosure": "Enlace de afiliado: MyBookConnect puede recibir una comisión por compras cualificadas a través de estos enlaces, sin coste adicional para ti.",
    "links": {
      "paperback": { "label": "Libro Físico (Papel)", "url": "https://www.amazon.es/..." },
      "ebook": { "label": "Ebook (Kindle)", "url": "https://www.amazon.es/..." },
      "audiobook": { "label": "Audiolibro (Audible)", "url": "https://www.amazon.es/..." }
    }
  }
  ```
- `POST /api/v1/books/<id>/affiliate-click/`: Registra clics en el modelo `AffiliateClick` de forma totalmente anonimizada para evaluar el volumen de conversión sin almacenar PII (cumpliendo con el RGPD).

---

## 3. Plataforma de Autores y Editoriales (Author Hub)

La plataforma ofrece a los creadores literarios herramientas profesionales para conectar directamente con sus lectores y monitorizar la difusión de sus obras.

### 3.1. Modelo `AuthorProfile`
- **Vinculación con Cuenta de Usuario:** Cada autor dispone de un usuario regular enlazado 1-a-1 con su `AuthorProfile`.
- **Enlace con el Catálogo:** Puede reclamar una entidad `Author` del catálogo general de libros.
- **Identidad Verificada (`is_verified`):** Distintivo visual otorgado tras validar la autenticidad del autor o editorial.
- **Campos Profesionales:** Nombre de pluma (`pen_name`), biografía, sitio web oficial, perfiles en Twitter/X e Instagram.

### 3.2. Proceso de Reclamación (`/api/v1/authors/claim/`)
1. El usuario solicita la verificación indicando el `author_id` del catálogo y notas de acreditación (`verification_notes`).
2. Los administradores y editores revisan la solicitud o se verifica automáticamente en caso de perfiles institucionales.

### 3.3. Panel Analítico del Autor (`/api/v1/authors/dashboard/`)
Permite a los autores conocer el impacto real de su catálogo en la comunidad:
- **Total de obras vinculadas** en MyBookConnect.
- **Volumen consolidado de lectores** (`readers_total`).
- **Desglose de estados de lectura:** Cuántos lectores tienen sus libros en *«Leyendo actualmente»*, *«Leído»* o *«Por leer»*.
- **Valoración media global** calculada a partir de las reseñas de la comunidad.
- **Feed de reseñas recientes** recibidas por sus obras para facilitar la interacción con la comunidad.

### 3.4. Comunicados Oficiales (`AuthorAnnouncement`)
Los autores verificados pueden publicar actualizaciones, presentaciones o noticias que se muestran en su perfil público y en las fichas de los libros vinculados:
- `POST /api/v1/authors/announcements/`: Creación de comunicado (con opción de fijar `is_pinned`).
- `GET /api/v1/authors/<id>/announcements/`: Consulta pública de novedades del autor.

---

## 4. Base de Suscripción Premium y Mecenazgo

Para lectores entusiastas que deseen apoyar el sostenimiento técnico del proyecto:
- **Modelo `UserSubscription`:**
  - `tier`: `free` (predeterminado) o `premium`.
  - `is_active`: Estado de la suscripción.
- **Beneficios Premium:**
  - Insignia distintiva de *Lector Mecenas* en el perfil público.
  - Estadísticas de lectura avanzadas (desgloses de velocidad, predicciones y comparativas anuales).
  - Acceso prioritario a herramientas de autor y beta testing.
- **Endpoint:** `GET /api/v1/users/subscription/` y `POST /api/v1/users/subscription/`.

---

## 5. Matriz de Cumplimiento Normativo (RGPD, FTC y UE)

| Requisito Legal | Medida Implementada |
| :--- | :--- |
| **Identificación Comercial** | Badge *"Afiliado / Patrocinado"* y texto de disclosure en cada bloque de compra. |
| **Consentimiento de Cookies** | Componente `AmazonAdSlot` respeta las preferencias del `CookieBanner` (`hasAdConsent`). |
| **Privacidad de Clics (RGPD)** | `AffiliateClick` solo almacena `book_id`, `format` y `timestamp` (cero IPs, cero IDs de usuario). |
| **Neutralidad de Recomendaciones** | Los motores de recomendación y búsqueda híbrida no leen variables de afiliación ni clics comerciales. |
