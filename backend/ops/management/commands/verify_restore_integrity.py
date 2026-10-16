import json
import logging
import os
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from books.models import Author, Book, Review, UserBook
from messages_app.models import Conversation, Message

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = "Verifica la integridad referencial y de dominio de la base de datos y archivos de media tras una restauración."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            help="Genera salida estructurada en formato JSON.",
        )
        parser.add_argument(
            "--check-media",
            action="store_true",
            help="Comprueba la existencia física de archivos multimedia (portadas y avatares) en MEDIA_ROOT.",
        )
        parser.add_argument(
            "--min-users",
            type=int,
            default=0,
            help="Número mínimo esperado de usuarios para considerar la restauración exitosa (por defecto 0).",
        )

    def handle(self, *args, **options):
        is_json = options.get("json", False)
        check_media = options.get("check_media", False)
        min_users = options.get("min_users", 0)

        report = {
            "status": "PASS",
            "errors": [],
            "warnings": [],
            "subsystems": {},
        }

        # 1. Usuarios y Perfiles
        try:
            total_users = User.objects.count()
            active_users = User.objects.filter(is_active=True).count()
            superusers = User.objects.filter(is_superuser=True).count()

            # Comprobar unicidad y campos vacíos
            empty_emails = User.objects.filter(email__isnull=True).count() + User.objects.filter(email="").count()

            user_subsystem = {
                "total_users": total_users,
                "active_users": active_users,
                "superusers": superusers,
                "empty_emails": empty_emails,
            }

            if total_users < min_users:
                report["errors"].append(
                    f"Conteo de usuarios ({total_users}) inferior al umbral mínimo requerido ({min_users})."
                )

            # Comprobar perfiles si existe UserProfile
            try:
                from users.models import UserProfile
                profiles_count = UserProfile.objects.count()
                user_subsystem["profiles_count"] = profiles_count
            except ImportError:
                pass

            report["subsystems"]["users"] = user_subsystem
        except Exception as e:
            report["errors"].append(f"Fallo en subsistema de usuarios: {e}")

        # 2. Catálogo (Libros y Autores)
        try:
            total_books = Book.objects.count()
            total_authors = Author.objects.count()

            empty_title_books = Book.objects.filter(title="").count()
            if empty_title_books > 0:
                report["errors"].append(f"Existen {empty_title_books} libros con título vacío.")

            # Coherencia de average_rating (0.0 a 5.0)
            invalid_ratings = Book.objects.filter(average_rating__lt=0.0).count() + Book.objects.filter(average_rating__gt=5.0).count()
            if invalid_ratings > 0:
                report["errors"].append(f"Existen {invalid_ratings} libros con average_rating fuera del rango [0.0, 5.0].")

            report["subsystems"]["catalog"] = {
                "total_books": total_books,
                "total_authors": total_authors,
                "invalid_rating_books": invalid_ratings,
            }
        except Exception as e:
            report["errors"].append(f"Fallo en subsistema de catálogo: {e}")

        # 3. Interacciones y Reseñas
        try:
            total_reviews = Review.objects.count()
            active_reviews = Review.objects.filter(deleted_at__isnull=True).count()
            total_userbooks = UserBook.objects.count()

            # Reseñas con rating fuera de 1..5
            invalid_review_ratings = Review.objects.filter(rating__lt=1).count() + Review.objects.filter(rating__gt=5).count()
            if invalid_review_ratings > 0:
                report["errors"].append(f"Existen {invalid_review_ratings} reseñas con rating fuera de [1, 5].")

            # Reseñas huérfanas
            orphaned_reviews = Review.objects.filter(user__isnull=True).count() + Review.objects.filter(book__isnull=True).count()
            if orphaned_reviews > 0:
                report["errors"].append(f"Existen {orphaned_reviews} reseñas huérfanas sin usuario o libro.")

            report["subsystems"]["interactions"] = {
                "total_reviews": total_reviews,
                "active_reviews": active_reviews,
                "total_userbooks": total_userbooks,
                "invalid_review_ratings": invalid_review_ratings,
                "orphaned_reviews": orphaned_reviews,
            }
        except Exception as e:
            report["errors"].append(f"Fallo en subsistema de interacciones: {e}")

        # 4. Mensajería
        try:
            total_conversations = Conversation.objects.count()
            total_messages = Message.objects.count()

            orphaned_messages = Message.objects.filter(conversation__isnull=True).count() + Message.objects.filter(sender__isnull=True).count()
            if orphaned_messages > 0:
                report["errors"].append(f"Existen {orphaned_messages} mensajes huérfanos sin conversación o remitente.")

            report["subsystems"]["messaging"] = {
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "orphaned_messages": orphaned_messages,
            }
        except Exception as e:
            report["errors"].append(f"Fallo en subsistema de mensajería: {e}")

        # 5. Verificación física de Media (Opcional)
        if check_media:
            try:
                media_root = Path(settings.MEDIA_ROOT)
                missing_covers = 0
                total_checked_covers = 0

                books_with_covers = Book.objects.exclude(cover_image="").exclude(cover_image__isnull=True)
                for b in books_with_covers:
                    total_checked_covers += 1
                    try:
                        file_path = media_root / str(b.cover_image)
                        if not file_path.is_file() and not (settings.MEDIA_ROOT in str(b.cover_image) and os.path.isfile(str(b.cover_image))):
                            missing_covers += 1
                    except Exception:
                        missing_covers += 1

                if missing_covers > 0:
                    report["warnings"].append(
                        f"Archivos de portadas ausentes en MEDIA_ROOT: {missing_covers}/{total_checked_covers}."
                    )

                report["subsystems"]["media"] = {
                    "total_checked_covers": total_checked_covers,
                    "missing_covers": missing_covers,
                }
            except Exception as e:
                report["warnings"].append(f"No se pudo auditar el sistema de ficheros de media: {e}")

        if report["errors"]:
            report["status"] = "FAIL"

        if is_json:
            self.stdout.write(json.dumps(report, indent=2))
        else:
            self.stdout.write("==============================================================================")
            self.stdout.write("REPORTE DE INTEGRIDAD POST-RESTAURACIÓN DE BASE DE DATOS")
            self.stdout.write("==============================================================================")
            self.stdout.write(f"Estado general: {'EXITOSO' if report['status'] == 'PASS' else 'FALLIDO'}")
            for subsys, data in report["subsystems"].items():
                self.stdout.write(f"-> Subsistema [{subsys.upper()}]: {json.dumps(data)}")

            if report["warnings"]:
                self.stdout.write("\nADVERTENCIAS:")
                for w in report["warnings"]:
                    self.stdout.write(self.style.WARNING(f"  [!] {w}"))

            if report["errors"]:
                self.stdout.write("\nERRORES CRÍTICOS:")
                for err in report["errors"]:
                    self.stdout.write(self.style.ERROR(f"  [X] {err}"))
            self.stdout.write("==============================================================================")

        if report["status"] == "FAIL":
            raise SystemExit(1)
