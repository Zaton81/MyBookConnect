"""
Comando de gestión Django para poblar y actualizar los documentos legales de MyBookConnect (Fase 18).
Garantiza el cumplimiento normativo (RGPD, LOPDGDD, LSSI-CE, AI Act, DSA) para el lanzamiento en fase beta.
"""

from django.core.management.base import BaseCommand

from books.models import LegalDocument

LEGAL_DOCUMENTS_DATA = {
    'terms': {
        'title': 'Términos y Condiciones de Uso (Fase Beta)',
        'content': """# Términos y Condiciones de Uso — MyBookConnect

**Versión:** 1.0 (Fase Beta)
**Última actualización:** Septiembre 2026

Bienvenido a **MyBookConnect**, una plataforma social dedicada a la catalogación de lecturas, descubrimiento literario e intercambio comunitario entre lectores. Al acceder o registrarte en nuestra plataforma, aceptas quedar vinculado por las presentes condiciones de uso.

---

## 1. Naturaleza del Servicio en Fase Beta
MyBookConnect se encuentra actualmente en fase de pruebas públicas (**Beta Abierta**). Durante este período:
- El servicio se proporciona "tal cual" y "según disponibilidad".
- Podemos implementar mejoras, ajustes arquitectónicos o refinamiento de funcionalidades continuas.
- Nos esforzamos por garantizar la máxima estabilidad y custodia de tus datos, aplicando copias de seguridad redundantes y controles de integridad transaccional.

---

## 2. Registro y Seguridad de la Cuenta
- Para interactuar en la comunidad (publicar reseñas, crear listas, enviar mensajes), debes registrarte proporcionando una dirección de correo electrónico válida.
- Eres responsable de mantener la confidencialidad de tu contraseña y de toda la actividad que ocurra bajo tu cuenta.
- El usuario puede modificar sus credenciales y solicitar la baja o anonimización de su perfil en cualquier momento desde su panel de configuración.

---

## 3. Propiedad Intelectual y Licencia de Contenido
- **Tus contribuciones:** Conservas todos los derechos de propiedad intelectual sobre el texto original de tus reseñas y comentarios. Al publicarlos, concedes a MyBookConnect una licencia no exclusiva, gratuita y de ámbito mundial para mostrarlos, distribuirlos y adaptarlos técnicamente dentro de la plataforma social.
- **Datos bibliográficos:** Las sinopsis, portadas y metadatos de obras provienen de fuentes bibliográficas públicas abiertas (Google Books API, OpenLibrary) o editoriales con fines de catalogación e identificación.
- **Marca y software:** El código fuente, diseño, logotipos y elementos distintivos de MyBookConnect están protegidos por leyes de propiedad intelectual e industrial.

---

## 4. Conducta del Usuario y Uso Aceptable
Te comprometes a utilizar MyBookConnect de forma ética y respetuosa. Queda expresamente prohibido:
- Publicar contenido difamatorio, de odio, acoso o ilegal (conforme a nuestra Política de Contenido).
- Ejecutar técnicas de scraping masivo abusivo, ataques de denegación de servicio o vulnerar la API de la plataforma.
- Introducir enlaces fraudulentos, malware o esquemas de spam publicitario no autorizado.

---

## 5. Limitación de Responsabilidad
MyBookConnect no se hace responsable de las opiniones o valoraciones subjetivas vertidas por los usuarios en sus reseñas. Nos reservamos el derecho de moderar o suspender temporal o permanentemente aquellas cuentas o contenidos que infrinjan nuestras políticas comunitarias o la legislación aplicable.

---

## 6. Legislación y Jurisdicción
Los presentes términos se rigen por la legislación española y europea. Cualquier controversia se someterá a los juzgados y tribunales competentes de conformidad con la normativa de protección de los consumidores y usuarios.
""",
    },
    'privacy': {
        'title': 'Política de Privacidad y Protección de Datos (RGPD)',
        'content': """# Política de Privacidad — MyBookConnect

**Marco normativo:** Reglamento General de Protección de Datos (UE 2016/679) y LOPD-GDD (Ley Orgánica 3/2018).
**Última actualización:** Septiembre 2026

En **MyBookConnect**, la privacidad de nuestros usuarios y la transparencia en el tratamiento de la información son principios rectores fundamentales. No implementamos técnicas de rastreo innecesario ni comercializamos tus datos personales.

---

## 1. Responsable del Tratamiento
- **Denominación:** MyBookConnect
- **Canal de Privacidad y DPO:** `privacidad@mybookconnect.local` / `dpo@mybookconnect.local`
- **Finalidad principal:** Prestación del servicio social de lectura y gestión de la comunidad de lectores.

---

## 2. Datos Personales Recopilados
Tratamos únicamente las categorías de datos estrictamente necesarias para el funcionamiento del servicio:
1. **Datos de identidad y cuenta:** Nombre de usuario (`username`), correo electrónico, nombre/apellidos opcionales, contraseña (almacenada con hash criptográfico unidireccional PBKDF2/Argon2) y fecha de aceptación de términos y privacidad.
2. **Perfil y preferencias:** Biografía voluntaria, avatar, preferencias de visibilidad (público, amigos, privado).
3. **Actividad lectora:** Libros en biblioteca (`UserBook`), estados de lectura (Quiero leer, Leyendo, Leído, Abandonado), calificaciones numéricas, fechas de lectura, listas temáticas y comentarios/reseñas.
4. **Interacción social:** Relaciones de seguimiento, bloqueos y mensajes directos cifrados en tránsito.
5. **Datos técnicos y de seguridad:** Dirección IP, User-Agent y marcas de tiempo en registros de auditoría (`AuditLog`) para prevención de ciberataques, control de fuerza bruta y cumplimiento del deber de custodia.

---

## 3. Finalidades y Bases Jurídicas del Tratamiento
- **Ejecución del contrato (Art. 6.1.b RGPD):** Gestión del registro, autenticación mediante JWT, sincronización de lecturas y servicio de mensajería social.
- **Cumplimiento de obligaciones legales (Art. 6.1.c RGPD):** Atención de requerimientos judiciales y preservación de registros de seguridad.
- **Interés legítimo (Art. 6.1.f RGPD):** Detección de abusos, moderación contra fraudes y optimización técnica de la plataforma.
- **Consentimiento explícito (Art. 6.1.a RGPD):** Para funcionalidades adicionales opcionales o participación en encuestas de producto.

---

## 4. Proveedores y Encargados del Tratamiento
Tus datos se alojan y procesan en infraestructuras seguras bajo acuerdos de encargo de tratamiento (DPA):
- **Alojamiento y Computación:** Proveedores de servidores en la Unión Europea (cumplimiento RGPD).
- **Almacenamiento y Base de Datos:** PostgreSQL con extensión `pgvector` y caché en memoria Redis.
- **Proveedores de APIs Bibliográficas:** Google Books API y OpenLibrary para metadatos públicos de libros (no transmitimos datos de usuario a estos servicios).
- **Servicios de Correo Transaccional:** Pasarelas seguras SMTP para confirmación de email y restablecimiento de contraseña.

---

## 5. Inteligencia Artificial y Algoritmos de Recomendación
MyBookConnect incorpora funcionalidades avanzadas de IA (búsqueda semántica y recomendaciones ponderadas v3):
- **Garantía estricta:** Tus datos personales y de lectura **NUNCA se utilizan para entrenar ni reentrenar modelos de lenguaje base o algoritmos de terceros**.
- Los embeddings de libros y preferencias de lectura se computan de manera anonimizada y aislada dentro de nuestra propia infraestructura mediante representaciones matemáticas vectoriales.

---

## 6. Política de Analytics y Ausencia de Tracking Invasivo
- **Filosofía Privacy-First:** No insertamos trackers de terceros, píxeles de publicidad comportamental entre sitios ni herramientas invasivas de fingerprinting.
- Las métricas de plataforma son estrictamente agregadas y anónimas (número de libros leídos, tiempos de respuesta de endpoints) sin perfilado publicitario.

---

## 7. Retención y Custodia de Datos
- Los datos se conservan mientras mantengas activa tu cuenta en MyBookConnect.
- Si ejerces tu derecho de supresión (**RGPD Art. 17**), se procede a la anonimización atómica e inmediata de tus datos personales, eliminando avatares, relaciones sociales y enlaces identificables.
- Los registros de seguridad y auditoría se conservan durante el plazo legal estrictamente indispensable para responsabilidades técnicas y jurídicas.

---

## 8. Tus Derechos (RGPD / LOPDGDD)
Puedes ejercer en cualquier momento tus derechos de:
- **Acceso y Rectificación:** Consultar y modificar tus datos desde tu perfil.
- **Portabilidad (Art. 20 RGPD):** Descargar un archivo estructurado en JSON con toda tu actividad desde *Ajustes > Privacidad*.
- **Supresión / Derecho al Olvido (Art. 17 RGPD):** Eliminar tu cuenta de forma permanente desde *Ajustes > Privacidad*.
- **Limitación y Oposición:** Contactando con `privacidad@mybookconnect.local`.
- **Reclamación:** Ante la Agencia Española de Protección de Datos (AEPD, www.aepd.es) si consideras que tus derechos han sido vulnerados.
""",
    },
    'cookies': {
        'title': 'Política de Cookies y Almacenamiento Local',
        'content': """# Política de Cookies — MyBookConnect

**Última actualización:** Septiembre 2026

En **MyBookConnect** creemos en una web limpia y respetuosa con el usuario. Nuestra política es clara: **no utilizamos cookies de rastreo publicitario entre dominios ni comerciamos con tu huella digital**.

---

## 1. ¿Qué son las cookies y tecnologías similares?
Las cookies y los elementos de almacenamiento local (como `localStorage` o `sessionStorage`) son pequeños ficheros que se guardan en tu dispositivo para recordar información sobre tu sesión, tus preferencias de interfaz y garantizar la seguridad de la navegación.

---

## 2. Tipos de Cookies y Almacenamiento que utilizamos

### 2.1. Técnicas y Estrictamente Necesarias (Exentas de consentimiento previo)
Son indispensables para que la plataforma funcione de forma segura:
- **Autenticación (JWT Tokens):** Identifican tu sesión segura para que no tengas que ingresar tus credenciales en cada página que visites.
- **Seguridad CSRF:** Protegen a los formularios de la plataforma contra ataques de falsificación de peticiones en sitios cruzados.
- **Equilibrio de carga y estado de conexión:** Facilitan la reconexión instantánea de los WebSockets de mensajería social.

### 2.2. Preferencias de Usuario (Almacenamiento Local)
- **Tema visual:** Guardamos localmente tu elección de Modo Claro / Modo Oscuro (`theme: dark | light`).
- **Configuración de lectura:** Preferencias locales de ordenamiento de estanterías y filtros de biblioteca.

### 2.3. Ausencia de Cookies de Rastreo Publicitario
MyBookConnect **no utiliza**:
- Cookies de redes publicitarias externas para perfilado comercial.
- Píxeles de seguimiento de terceros como Meta Pixel, TikTok o rastreadores biométricos.

---

## 3. Gestión y Configuración de Cookies
Al no emplear cookies de seguimiento invasivo, no requerimos molestos muros de cookies que entorpezcan tu lectura. Puedes en cualquier momento eliminar o bloquear las cookies y el almacenamiento local desde la configuración de tu navegador (Chrome, Firefox, Safari, Edge, Brave). Ten en cuenta que si bloqueas las cookies técnicas esenciales, no podrás iniciar sesión en tu cuenta.
""",
    },
    'legal_notice': {
        'title': 'Aviso Legal e Información Corporativa',
        'content': """# Aviso Legal — MyBookConnect

**Marco normativo:** Ley 34/2002 de Servicios de la Sociedad de la Información y de Comercio Electrónico (LSSI-CE).
**Última actualización:** Septiembre 2026

---

## 1. Identificación del Titular
En cumplimiento con el artículo 10 de la Ley 34/2002 (LSSI-CE), se informa de los datos identificativos de la entidad prestadora del servicio:
- **Denominación:** Proyecto MyBookConnect (Plataforma Social de Lectores)
- **Email de contacto general:** `contacto@mybookconnect.local`
- **Email de privacidad y legal:** `legal@mybookconnect.local`
- **Ámbito:** Plataforma digital comunitaria orientada a la difusión de la literatura y el fomento de la lectura.

---

## 2. Condiciones de Uso y Acceso
El acceso a este sitio web otorga la condición de usuario e implica la aceptación plena de las advertencias legales aquí contenidas. El usuario se compromete a no emplear los servicios para fines ilícitos o contrarios a la buena fe.

---

## 3. Exención de Responsabilidad por Enlaces y Terceros
MyBookConnect puede contener enlaces a sitios web de terceros (editoriales, bibliotecas digitales o plataformas externas como Google Books, OpenLibrary o plataformas de compra autorizadas). MyBookConnect no asume responsabilidad alguna sobre las políticas o contenidos de tales páginas externas.

---

## 4. Propiedad Intelectual
Todos los derechos reservados. El diseño de la interfaz, el logotipo identificativo y la arquitectura de software son propiedad de los titulares del proyecto MyBookConnect.
""",
    },
    'content_policy': {
        'title': 'Política de Contenido y Normas de la Comunidad',
        'content': """# Política de Contenido y Normas de la Comunidad — MyBookConnect

**Marco normativo:** Reglamento de Servicios Digitales (DSA, UE 2022/2065).
**Última actualización:** Septiembre 2026

MyBookConnect es un club de lectura y espacio de debate abierto. Creemos firmemente en la libertad de expresión, la crítica literaria rigurosa y la diversidad de opiniones, siempre bajo el respeto mutuo.

---

## 1. Reglas Comunitarias Fundamentales
1. **Reseñas auténticas y constructivas:** Las reseñas deben reflejar opiniones sinceras sobre obras o autores. Se permite la crítica severa hacia una obra, pero no el ataque personal denigrante hacia otros miembros de la comunidad o creadores.
2. **Aviso de Spoilers:** Si tu reseña o comentario desvela giros cruciales del argumento, utiliza las etiquetas de advertencia de spoiler para preservar la experiencia de otros lectores.
3. **Tolerancia Cero con el Acoso y el Odio:** Está estrictamente prohibido el contenido que promueva la violencia, discriminación, racismo, misoginia o denigración basada en orientación sexual, religión o discapacidad.
4. **Prohibición de Spam y Fraude:** No se tolerará la publicación masiva automatizada de enlaces publicitarios, venta no autorizada ni reseñas incentivadas de forma artificial para manipular valoraciones.
5. **Protección de Menores y Contenido Ilícito:** Se prohíbe de forma tajante cualquier contenido que atente contra la integridad de menores, derechos fundamentales o constituya una infracción legal penal.

---

## 2. Sistema de Reportes y Moderación (Fase 16)
Cualquier miembro de la comunidad puede denunciar perfiles, reseñas, comentarios en reseñas, mensajes directos o listas de lectura que infrinjan estas normas:
- Botón de reporte accesible con selección del motivo de infracción.
- Revisión por el equipo de moderación en la cola administrativa.
- Medidas disciplinarias escalonadas: advertencia, ocultación/moderación del contenido (`is_moderated=True`), silenciamiento temporal o suspensión definitiva de la cuenta.
- Registro auditable de todas las actuaciones en `AuditLog`.
""",
    },
    'deletion_policy': {
        'title': 'Política de Eliminación, Cancelación y Derecho al Olvido',
        'content': """# Política de Eliminación, Cancelación y Retención — MyBookConnect

**Marco normativo:** Artículo 17 del Reglamento General de Protección de Datos (RGPD) — Derecho al Olvido.
**Última actualización:** Septiembre 2026

---

## 1. Principio de Autodeterminación del Usuario
En MyBookConnect consideramos que el usuario es el único propietario de sus datos personales. Si decides dejar la plataforma, te proporcionamos mecanismos automáticos, directos y sin trabas para ejercer tu Derecho al Olvido.

---

## 2. Procedimiento de Eliminación de Cuenta (Fase 17)
Puedes solicitar la baja de tu cuenta en cualquier momento desde *Ajustes del Perfil > Privacidad & RGPD*:
1. **Reautenticación:** Se solicita tu contraseña actual para verificar que eres el legítimo titular.
2. **Confirmación consciente:** Se requiere teclear la palabra `"ELIMINAR"` para evitar bajas por pulsación involuntaria.
3. **Ejecución atómica e irreversible:**
   - Tu cuenta se desactiva inmediatamente (`is_active = False`) y se registra la fecha de supresión (`deleted_at`).
   - Se anonimizan tu nombre de usuario (`deleted_user_<id>`) y tu correo electrónico (`deleted_<id>_<timestamp>@deleted.local`).
   - Se destruye la contraseña (`set_unusable_password()`).
   - Se eliminan la biografía, ubicación, fecha de nacimiento y archivo de imagen de avatar.
   - Se disuelven todas las relaciones sociales (seguimientos, seguidores, bloqueos y mutes).
   - Tus listas de lectura pasan a ser privadas y ocultadas de los motores de recomendación.
   - Tus comentarios en reseñas comunitarias pasan a estado eliminado (*soft-delete*).
   - Se revocan y envían a lista negra todos los tokens de autenticación JWT pendientes en todos tus dispositivos.

---

## 3. Retención de Reseñas Públicas y Catalogación Colectiva
- Para preservar la coherencia del catálogo literario y las discusiones colectivas, las reseñas literarias no eliminadas previamente por el usuario permanecerán asociadas a la entidad disociada y anónima (`deleted_user_<id>`), sin ningún dato personal que permita identificar al autor original.
- Si antes de solicitar la baja deseas retirar tus reseñas, puedes eliminarlas individualmente desde tu perfil o solicitar su purgado previo.

---

## 4. Conservación de Registros de Seguridad
De conformidad con las directivas de seguridad informática y prevención de ciberdelitos, se conservarán los registros técnicos de auditoría (`AuditLog`) durante el tiempo estrictamente exigido por la legislación aplicable para la depuración de responsabilidades jurídicas.
""",
    },
    'contact': {
        'title': 'Canales Oficiales de Contacto y Atención al Usuario',
        'content': """# Contacto y Atención al Usuario — MyBookConnect

**Última actualización:** Septiembre 2026

Ponemos a disposición de los usuarios, autores, editoriales y autoridades los siguientes canales oficiales de comunicación:

---

## 1. Canales por Temática
- **Soporte General y Ayuda Técnica:**
  `soporte@mybookconnect.local`
  Para incidencias en el acceso, sincronización de lecturas o dudas de uso general.

- **Privacidad, Protección de Datos y DPO:**
  `privacidad@mybookconnect.local` / `dpo@mybookconnect.local`
  Para el ejercicio de derechos ARCO (Acceso, Rectificación, Cancelación, Oposición, Portabilidad y Olvido).

- **Moderación y Reportes de Contenido:**
  `moderacion@mybookconnect.local`
  Para apelaciones sobre medidas de moderación o notificaciones urgentes de contenido ilícito (DSA).

- **Propiedad Intelectual y Derechos de Autor (DMCA/LSSI):**
  `copyright@mybookconnect.local`
  Para notificaciones de infracción de propiedad intelectual relativas a portadas o extractos.

---

## 2. Plazos de Respuesta
- Consultas generales: respuesta estimada en un plazo de 24 a 48 horas laborables.
- Ejercicio de derechos RGPD: tramitación y respuesta en el plazo legal máximo de un mes establecido por el Reglamento General de Protección de Datos.
""",
    },
}


class Command(BaseCommand):
    help = 'Pobla o actualiza los documentos legales de MyBookConnect (Fase 18).'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Iniciando sembrado de documentos legales...'))
        created_count = 0
        updated_count = 0

        for slug, data in LEGAL_DOCUMENTS_DATA.items():
            doc, created = LegalDocument.objects.update_or_create(
                slug=slug,
                defaults={
                    'title': data['title'],
                    'content': data['content'].strip(),
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f' [+] Creado: {slug} - "{doc.title}"'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f' [~] Actualizado: {slug} - "{doc.title}"'))

        self.stdout.write(
            self.style.SUCCESS(
                f'Finalizado sembrado legal: {created_count} creados, {updated_count} actualizados. Total: {len(LEGAL_DOCUMENTS_DATA)} documentos vigentes.'
            )
        )
