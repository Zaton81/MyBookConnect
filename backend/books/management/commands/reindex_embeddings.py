"""
Comando Django para indexar y regenerar embeddings vectoriales de libros (Fase 6 - 11.6).

Uso:
    python manage.py reindex_embeddings [--force] [--batch-size=50] [--check-stale]
"""

from django.core.management.base import BaseCommand

from books.services.embedding_service import mark_stale_embeddings, reindex_all_embeddings


class Command(BaseCommand):
    help = "Genera y actualiza los embeddings vectoriales de las obras literarias en la base de datos."

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Fuerza la regeneración de todos los embeddings ignorando los ya completados.',
        )
        parser.add_argument(
            '--check-stale',
            action='store_true',
            help='Identifica libros con contenido modificado y marca sus embeddings como STALE.',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Cantidad de libros a procesar por lote (por defecto: 50).',
        )
        parser.add_argument(
            '--model',
            type=str,
            default=None,
            help='Nombre del modelo de embedding a utilizar (por defecto: configuración activa).',
        )

    def handle(self, *args, **options):
        force = options['force']
        check_stale = options['check_stale']
        batch_size = options['batch_size']
        model_name = options['model']

        self.stdout.write(self.style.NOTICE("Iniciando tarea de gobernanza de embeddings..."))

        if check_stale:
            stale_count = mark_stale_embeddings()
            self.stdout.write(
                self.style.SUCCESS(f"Revisión completada: {stale_count} registros marcados como STALE.")
            )

        self.stdout.write(f"Indexando libros (force={force}, batch_size={batch_size})...")
        stats = reindex_all_embeddings(
            batch_size=batch_size,
            force=force,
            model_name=model_name,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Proceso finalizado: {stats['indexed']} indexados con éxito, "
                f"{stats['failed']} fallidos de un total de {stats['candidates']} candidatos."
            )
        )
