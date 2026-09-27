from unittest.mock import patch

import pytest
from django.core.management import call_command

from books.models import Author, Book, BookEmbedding, Category, EmbeddingStatus
from books.services.embedding_service import (
    compute_book_content_hash,
    generate_book_embedding,
    mark_stale_embeddings,
)
from books.services.unified_search_service import UnifiedSearchEngine


@pytest.mark.django_db
class TestPhase06SearchRanking:
    def setup_method(self):
        self.author_cervantes = Author.objects.create(name='Miguel de Cervantes')
        self.author_garcia = Author.objects.create(name='Gabriel García Márquez')
        self.author_borges = Author.objects.create(name='Jorge Luis Borges')

        self.cat_clasica = Category.objects.create(name='Literatura Clásica', slug='literatura-clasica')
        self.cat_magico = Category.objects.create(name='Realismo Mágico', slug='realismo-magico')
        self.cat_filo = Category.objects.create(name='Ficción Filosófica', slug='ficcion-filosofica')

        # 1. Libro con título exacto y rating normal
        self.b_exact = Book.objects.create(
            title='Don Quijote de la Mancha',
            author=self.author_cervantes,
            description='Aventuras del hidalgo caballero Don Quijote y Sancho Panza.',
            average_rating=4.5,
        )
        self.b_exact.categories.add(self.cat_clasica)

        # 2. Libro con prefijo coincidente pero título más largo
        self.b_prefix = Book.objects.create(
            title='Don Quijote de la Mancha: Segunda Parte',
            author=self.author_cervantes,
            description='Continuación de las andanzas del ingenioso caballero.',
            average_rating=4.4,
        )
        self.b_prefix.categories.add(self.cat_clasica)

        # 3. Libro muy popular con rating máximo pero sin relación con Quijote
        self.b_popular = Book.objects.create(
            title='Cien años de soledad',
            author=self.author_garcia,
            description='Historia épica de la familia Buendía en Macondo.',
            average_rating=5.0,
        )
        self.b_popular.categories.add(self.cat_magico)

        # 4. Libro filosófico para búsqueda semántica
        self.b_borges = Book.objects.create(
            title='Ficciones',
            author=self.author_borges,
            description='Laberintos, espejos, bibliotecas infinitas y la naturaleza del tiempo.',
            average_rating=4.9,
        )
        self.b_borges.categories.add(self.cat_filo)

        self.engine = UnifiedSearchEngine(mode='hybrid')

    # ─── 1. Búsqueda Textual y Jerarquía de Ranking (11.1 & 11.2) ───
    def test_ranking_hierarchy_exact_beats_prefix_and_unrelated_popular(self):
        """
        Jerarquía estricta:
        Una coincidencia exacta ('Don Quijote de la Mancha') debe tener mayor ranking que
        el prefijo ('Segunda Parte'), y la popularidad de un libro no relevante ('Cien años de soledad')
        NUNCA debe adelantar a las coincidencias temáticas.
        """
        items, count = self.engine.search(query='Don Quijote de la Mancha', auto_import=False)
        assert count >= 2
        titles = [item.book.title for item in items]

        # El primero debe ser la coincidencia exacta
        assert titles[0] == 'Don Quijote de la Mancha'
        assert items[0].match_type == 'exact'

        # El segundo debe ser el prefijo
        assert titles[1] == 'Don Quijote de la Mancha: Segunda Parte'

        # El libro popular no coincidente no debe superar a las coincidencias
        if 'Cien años de soledad' in titles:
            popular_idx = titles.index('Cien años de soledad')
            assert popular_idx > 1

    def test_fuzzy_trigram_tolerance_to_typos(self):
        """Verifica que pg_trgm recupere obras con erratas tipográficas (ej. 'Quijotte')."""
        items, count = self.engine.search(query='Quijotte mancha', auto_import=False)
        assert count >= 1
        found_titles = [item.book.title for item in items]
        assert any('Don Quijote' in t for t in found_titles)

    # ─── 2. Paginación Estable y Determinista (11.3) ───
    def test_deterministic_stable_pagination(self):
        """Verifica que paginar con limit/offset no produzca duplicados ni omisiones."""
        # Creamos varios libros homogéneos para probar empates de score
        for i in range(6):
            b = Book.objects.create(
                title=f"Antología de Ensayos Tomo {i+1}",
                author=self.author_borges,
                description="Ensayos filosóficos y literarios breves.",
                average_rating=4.0,
            )
            b.categories.add(self.cat_filo)

        page1, total1 = self.engine.search(query='Antología de Ensayos', limit=3, offset=0, auto_import=False)
        page2, total2 = self.engine.search(query='Antología de Ensayos', limit=3, offset=3, auto_import=False)

        assert total1 == total2
        ids_p1 = [it.book.id for it in page1]
        ids_p2 = [it.book.id for it in page2]

        # No debe haber solapamiento entre la página 1 y la página 2
        assert len(set(ids_p1).intersection(set(ids_p2))) == 0
        assert len(ids_p1) == 3
        assert len(ids_p2) == 3

    # ─── 3. Vector Embeddings y Búsqueda Semántica Real (11.4 & 11.5) ───
    @patch('books.services.embedding_service.get_embedding_for_text')
    def test_generate_book_embedding_lifecycle(self, mock_get_emb):
        """Verifica la creación del modelo BookEmbedding con hash y estado COMPLETED."""
        mock_get_emb.return_value = [0.1, 0.2, 0.3, 0.4]

        rec = generate_book_embedding(self.b_borges, force=True)
        assert rec.embedding_status == EmbeddingStatus.COMPLETED
        assert rec.dimension == 4
        assert rec.vector == [0.1, 0.2, 0.3, 0.4]
        assert len(rec.content_hash) == 64
        assert rec.embedded_at is not None

    @patch('books.services.unified_search_service.get_embedding_for_text')
    def test_semantic_search_with_vector_similarity(self, mock_get_emb):
        """Verifica la recuperación semántica mediante similitud coseno de vectores en BookEmbedding."""
        # Vector para 'laberinto infinito': muy afín al vector de Borges
        mock_get_emb.return_value = [0.9, 0.1, 0.0]

        # Asignamos embedding vectorial a Borges
        BookEmbedding.objects.update_or_create(
            book=self.b_borges,
            defaults={
                'vector': [0.85, 0.15, 0.0],
                'dimension': 3,
                'embedding_status': EmbeddingStatus.COMPLETED,
                'content_hash': compute_book_content_hash(self.b_borges),
            },
        )

        semantic_engine = UnifiedSearchEngine(mode='semantic')
        items, count = semantic_engine.search(query='laberinto infinito', auto_import=False)

        assert count >= 1
        assert items[0].book.id == self.b_borges.id
        assert items[0].semantic_score > 0.8
        assert items[0].match_type in ('semantic', 'hybrid')

    # ─── 4. Detección de Cambios y Re-embedding (11.6) ───
    def test_mark_stale_embeddings_on_book_content_change(self):
        """Si la sinopsis de un libro cambia, mark_stale_embeddings transita su estado a STALE."""
        initial_hash = compute_book_content_hash(self.b_exact)
        BookEmbedding.objects.create(
            book=self.b_exact,
            vector=[0.1, 0.2],
            dimension=2,
            embedding_status=EmbeddingStatus.COMPLETED,
            content_hash=initial_hash,
        )

        # Modificamos la sinopsis del libro
        self.b_exact.description = "Nueva sinopsis modificada con detalles inéditos."
        self.b_exact.save()

        stale_count = mark_stale_embeddings()
        assert stale_count >= 1

        rec = BookEmbedding.objects.get(book=self.b_exact)
        assert rec.embedding_status == EmbeddingStatus.STALE

    @patch('books.services.embedding_service.get_embedding_for_text')
    def test_reindex_embeddings_management_command(self, mock_get_emb):
        """Verifica que el comando python manage.py reindex_embeddings procese los libros."""
        mock_get_emb.return_value = [0.5, 0.5, 0.5]

        # Ejecutamos el comando de gestión
        call_command('reindex_embeddings', force=True, batch_size=10)

        # Todos los libros principales deben tener su BookEmbedding en COMPLETED
        assert BookEmbedding.objects.filter(book=self.b_exact, embedding_status=EmbeddingStatus.COMPLETED).exists()
        assert BookEmbedding.objects.filter(book=self.b_borges, embedding_status=EmbeddingStatus.COMPLETED).exists()
