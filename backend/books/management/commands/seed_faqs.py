from django.core.management.base import BaseCommand
from books.models import FAQ


class Command(BaseCommand):
    help = "Siembra preguntas frecuentes (FAQs) iniciales de la plataforma."

    def handle(self, *args, **options):
        initial_faqs = [
            # General
            {
                "question": "¿Qué es MyBookConnect?",
                "answer": "MyBookConnect es una red social y plataforma integral para lectores y autores. Te permite gestionar tu biblioteca personal, registrar tu progreso de lectura, escribir reseñas, conectar con amigos y descubrir nuevas obras mediante recomendaciones comunitarias y semánticas.",
                "category": FAQ.Category.GENERAL,
                "order": 1,
            },
            {
                "question": "¿Es gratuito utilizar MyBookConnect?",
                "answer": "Sí, el registro y todas las funcionalidades principales (gestión de biblioteca, reseñas, listas de lectura, mensajería y red social) son 100% gratuitas para todos los lectores.",
                "category": FAQ.Category.GENERAL,
                "order": 2,
            },

            # Autores
            {
                "question": "¿Cómo puedo reclamar mi página de autor?",
                "answer": "Si eres un escritor con libros en nuestro catálogo, visita tu ficha pública de autor y haz clic en '¿Eres este autor? Reclamar página'. Completa el formulario indicando tu email profesional y un enlace o prueba de tu autoría (web oficial, perfil editorial, etc.). Nuestro equipo de moderación revisará la solicitud y te asignará la insignia oficial.",
                "category": FAQ.Category.AUTHORS,
                "order": 1,
            },
            {
                "question": "¿Qué beneficios tiene estar verificado como autor?",
                "answer": "Los autores verificados obtienen la insignia oficial en su perfil y obras, acceso a un panel de control exclusivo con analítica de lectores, la posibilidad de actualizar su biografía y enlaces oficiales, y la capacidad de publicar comunicados y novedades directamente a sus seguidores.",
                "category": FAQ.Category.AUTHORS,
                "order": 2,
            },
            {
                "question": "¿Cuánto tarda la verificación de una página de autor?",
                "answer": "Normalmente nuestro equipo de moderación evalúa y responde a las solicitudes de reclamación en un plazo de 24 a 48 horas laborables.",
                "category": FAQ.Category.AUTHORS,
                "order": 3,
            },

            # Libros y Catálogo
            {
                "question": "¿Cómo añado libros a mi biblioteca?",
                "answer": "Utiliza el buscador superior para encontrar cualquier obra por título, autor o ISBN. En la ficha del libro, selecciona el estado de lectura deseado: 'Leyendo', 'Leído', 'Quiero leer' o 'Abandonado'. También puedes importar tu historial desde Goodreads mediante archivo CSV.",
                "category": FAQ.Category.BOOKS,
                "order": 1,
            },
            {
                "question": "¿Cómo se calculan las calificaciones de los libros?",
                "answer": "Las calificaciones de las obras se basan en el promedio ponderado de las reseñas comunitarias (en escala unificada de 1 a 5 estrellas) redactadas por los usuarios de la plataforma.",
                "category": FAQ.Category.BOOKS,
                "order": 2,
            },

            # Cuenta y Privacidad
            {
                "question": "¿Cómo controlo la privacidad de mi perfil?",
                "answer": "En la sección de Ajustes de tu perfil puedes configurar la visibilidad general (Pública, Solo Seguidores o Privada), así como la visibilidad granular de tu correo, estadísticas y actividad de lectura.",
                "category": FAQ.Category.ACCOUNT,
                "order": 1,
            },
            {
                "question": "¿Puedo exportar o eliminar mis datos?",
                "answer": "Cumpliendo estrictamente con el RGPD (Artículos 17 y 20), desde la pestaña de Privacidad de tu cuenta puedes descargar una copia íntegra de tus datos en formato JSON o solicitar la eliminación atómica y anonimización de tu cuenta en cualquier momento.",
                "category": FAQ.Category.ACCOUNT,
                "order": 2,
            },

            # Comunidad
            {
                "question": "¿Cómo reporto un comportamiento abusivo o contenido inapropiado?",
                "answer": "En cada reseña, comentario o perfil de usuario encontrarás un botón de reporte. Selecciona el motivo y describe la incidencia; nuestro equipo de moderación actuará de forma confidencial y prioritaria.",
                "category": FAQ.Category.COMMUNITY,
                "order": 1,
            },
        ]

        created_count = 0
        for faq_data in initial_faqs:
            _, created = FAQ.objects.update_or_create(
                question=faq_data["question"],
                defaults=faq_data,
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Siembra de FAQs completada: {created_count} creadas o actualizadas exitosamente."
            )
        )
