"""
Comando de gestión Django para sembrar un catálogo base determinista en desarrollo y pruebas.
Genera libros, autores y portadas SVG/WebP ligeras en memoria sin ensuciar el control de versiones Git.
"""

import io

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from PIL import Image, ImageDraw

from books.models import Author, Book, Category


class Command(BaseCommand):
    help = "Siembra un catálogo literario determinista con portadas sintéticas para desarrollo local."

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=5,
            help="Cantidad de libros a sembrar (por defecto: 5).",
        )
        parser.add_argument(
            '--clean',
            action='store_true',
            help="Limpia los libros y autores de muestra antes de sembrar.",
        )

    def _generate_synthetic_cover(self, title: str, author_name: str, color: tuple[int, int, int]) -> ContentFile:
        """Genera una portada WebP sintética de 600x900 px en memoria."""
        width, height = 600, 900
        image = Image.new("RGB", (width, height), color=color)
        draw = ImageDraw.Draw(image)

        # Dibujar un marco interior elegante
        border_margin = 30
        draw.rectangle(
            [border_margin, border_margin, width - border_margin, height - border_margin],
            outline=(255, 255, 255),
            width=4,
        )

        buffer = io.BytesIO()
        image.save(buffer, format="WEBP", quality=80)
        filename = f"{slugify(title)[:40]}-cover.webp"
        return ContentFile(buffer.getvalue(), name=filename)

    def handle(self, *args, **options):
        count = options['count']
        clean = options['clean']

        if clean:
            self.stdout.write(self.style.WARNING("Eliminando obras de muestra anteriores..."))
            Book.objects.filter(title__startswith="[DEV] ").delete()
            Author.objects.filter(name__startswith="[DEV]").delete()

        sample_data = [
            {
                "title": "Don Quijote de la Mancha",
                "author": "Miguel de Cervantes",
                "isbn": "9789999000001",
                "category": "Clásicos",
                "color": (44, 62, 80),
                "synopsis": "Las aventuras del ingenioso hidalgo don Quijote de la Mancha y su fiel escudero Sancho Panza.",
                "page_count": 863,
            },
            {
                "title": "Cien años de soledad",
                "author": "Gabriel García Márquez",
                "isbn": "9789999000002",
                "category": "Realismo Mágico",
                "color": (230, 126, 34),
                "synopsis": "La épica historia de la familia Buendía en el mítico pueblo de Macondo.",
                "page_count": 471,
            },
            {
                "title": "Orgullo y Prejuicio",
                "author": "Jane Austen",
                "isbn": "9789999000003",
                "category": "Romántica",
                "color": (142, 68, 173),
                "synopsis": "La relación tempestuosa entre la vivaz Elizabeth Bennet y el aristocrático señor Darcy.",
                "page_count": 432,
            },
            {
                "title": "1984",
                "author": "George Orwell",
                "isbn": "9789999000004",
                "category": "Ciencia Ficción",
                "color": (39, 174, 96),
                "synopsis": "Una visión distópica y profética de un estado totalitario vigilado por el Gran Hermano.",
                "page_count": 328,
            },
            {
                "title": "El principito",
                "author": "Antoine de Saint-Exupéry",
                "isbn": "9789999000005",
                "category": "Fábula",
                "color": (41, 128, 185),
                "synopsis": "Un piloto perdido en el desierto conoce a un pequeño príncipe de otro planeta.",
                "page_count": 96,
            },
            {
                "title": "Ficciones",
                "author": "Jorge Luis Borges",
                "isbn": "9789999000006",
                "category": "Fantasía",
                "color": (192, 57, 43),
                "synopsis": "Cuentos laberínticos sobre espejos, bibliotecas infinitas y senderos que se bifurcan.",
                "page_count": 216,
            },
        ]

        items_to_seed = sample_data[:count]
        created_books = 0

        for item in items_to_seed:
            author, _ = Author.objects.get_or_create(
                name=f"[DEV] {item['author']}",
                defaults={
                    "biography": f"Biografía de muestra para {item['author']}.",
                    "is_verified": True,
                },
            )

            category, _ = Category.objects.get_or_create(
                name=item['category'],
                defaults={"slug": slugify(item['category'])},
            )

            dev_title = f"[DEV] {item['title']}"
            book, created = Book.objects.get_or_create(
                title=dev_title,
                defaults={
                    "isbn": item['isbn'],
                    "author": author,
                    "description": item['synopsis'],
                    "page_count": item['page_count'],
                },
            )

            if created:
                book.categories.add(category)
                cover_content = self._generate_synthetic_cover(item['title'], item['author'], item['color'])
                book.cover.save(cover_content.name, cover_content, save=True)
                created_books += 1

        self.stdout.write(
            self.style.SUCCESS(f"Siembra completada con éxito. {created_books} obras creadas sin binarios rastreados en Git.")
        )
