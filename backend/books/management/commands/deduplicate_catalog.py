from django.core.management.base import BaseCommand

from books.services.deduplication_service import deduplicate_all_books, find_duplicate_books


class Command(BaseCommand):
    help = "Detecta y unifica libros duplicados del mismo autor y título (ediciones físicas, digitales, etc.)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Lista los duplicados detectados sin realizar cambios en la base de datos',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)

        duplicate_groups = find_duplicate_books()
        if not duplicate_groups:
            self.stdout.write(self.style.SUCCESS("El catálogo está 100% unificado. No se detectaron duplicados."))
            return

        total_dups = sum(len(g['duplicates']) for g in duplicate_groups)
        self.stdout.write(
            f"Se detectaron {len(duplicate_groups)} grupos con un total de {total_dups} libros duplicados."
        )

        for group in duplicate_groups:
            canon = group['canonical']
            author_name = canon.author.name if canon.author else "Sin autor"
            self.stdout.write(
                f"- Obra: '{canon.title}' | Autor: '{author_name}' | Canónico ID: {canon.id} (ISBN: {canon.isbn or 'N/A'})"
            )
            for dup in group['duplicates']:
                self.stdout.write(f"    * Duplicado a absorber: ID {dup.id} (ISBN: {dup.isbn or 'N/A'})")

        if dry_run:
            self.stdout.write(self.style.WARNING("Modo --dry-run activado: no se aplicaron fusiones."))
            return

        res = deduplicate_all_books()
        self.stdout.write(
            self.style.SUCCESS(
                f"Fusión completada con éxito: {res['groups_merged']} obras consolidadas, {res['duplicates_removed']} duplicados eliminados."
            )
        )
