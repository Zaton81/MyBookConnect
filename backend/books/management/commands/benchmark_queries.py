"""
Fase 43: Comando de consola para perfilado y benchmarking de consultas en PostgreSQL.
Ejecuta EXPLAIN (ANALYZE, BUFFERS) en las consultas críticas del dominio y reporta
tiempos de planificación, ejecución y uso de índices.
"""
from django.core.management.base import BaseCommand
from django.db import connection

from mybookconnect.query_profiler import QueryProfiler
from books.models import Author, Book, Category, Review, UserBook
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Ejecuta EXPLAIN ANALYZE sobre las consultas principales del sistema y valida tiempos de ejecución frente a los SLAs definidos.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--samples',
            type=int,
            default=3,
            help='Número de repeticiones para calcular promedio de ejecución.',
        )

    def handle(self, *args, **options):
        samples = options['samples']
        self.stdout.write(self.style.NOTICE(f"Iniciando perfilado de consultas críticas con {samples} muestras por consulta..."))

        # Asegurar datos mínimos para que el planificador de PostgreSQL tenga filas que evaluar
        author, _ = Author.objects.get_or_create(name='Autor Benchmark')
        category, _ = Category.objects.get_or_create(name='Benchmark')
        book, _ = Book.objects.get_or_create(title='Libro Benchmark de Prueba', defaults={'author': author})
        book.categories.add(category)
        user, _ = User.objects.get_or_create(username='benchmark_user', defaults={'email': 'bench@test.com'})
        UserBook.objects.get_or_create(user=user, book=book, defaults={'is_read': True})
        Review.objects.get_or_create(user=user, book=book, defaults={'rating': 5, 'text': 'Excelente lectura.'})

        queries_to_benchmark = [
            (
                'Búsqueda de Libros (Título/Trigrama)',
                Book.objects.filter(title__icontains='Benchmark').select_related('author'),
                500.0,  # SLA: < 500 ms
            ),
            (
                'Catálogo Principal (Paginación + Prefetch)',
                Book.objects.select_related('author').prefetch_related('categories').order_by('-created_at')[:20],
                300.0,  # SLA: < 300 ms
            ),
            (
                'Biblioteca de Usuario (UserBook)',
                UserBook.objects.filter(user_id=user.id).select_related('book', 'book__author').order_by('-updated_at'),
                300.0,  # SLA: < 300 ms
            ),
            (
                'Reseñas de Libro con Autores',
                Review.objects.filter(book_id=book.id).select_related('user', 'book', 'book__author').order_by('-created_at'),
                300.0,  # SLA: < 300 ms
            ),
        ]

        self.stdout.write("=" * 95)
        self.stdout.write(f"{'Consulta':<40} | {'Exec (ms)':<10} | {'Plan (ms)':<10} | {'SLA (ms)':<9} | {'Estado':<6}")
        self.stdout.write("=" * 95)

        all_passed = True

        for name, qs, sla_limit in queries_to_benchmark:
            exec_times = []
            plan_times = []
            last_profile = None

            for _ in range(samples):
                profile = QueryProfiler.explain_analyze(qs)
                exec_times.append(profile['execution_time_ms'])
                plan_times.append(profile['planning_time_ms'])
                last_profile = profile

            avg_exec = round(sum(exec_times) / len(exec_times), 2)
            avg_plan = round(sum(plan_times) / len(plan_times), 2)
            passed = avg_exec < sla_limit
            if not passed:
                all_passed = False

            status_text = self.style.SUCCESS('PASS') if passed else self.style.ERROR('FAIL')
            self.stdout.write(
                f"{name:<40} | {avg_exec:<10.2f} | {avg_plan:<10.2f} | {sla_limit:<9.1f} | {status_text}"
            )
            if last_profile.get('index_scans_used'):
                self.stdout.write(
                    self.style.MIGRATE_HEADING(f"   -> Índices usados: {', '.join(last_profile['index_scans_used'])}")
                )

        self.stdout.write("=" * 95)

        if all_passed:
            self.stdout.write(self.style.SUCCESS("✓ Todas las consultas evaluadas cumplen estrictamente con los SLAs de rendimiento."))
        else:
            self.stdout.write(self.style.WARNING("⚠ Algunas consultas superaron el umbral fijado de SLA."))
