import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from books.cache_utils import user_recommendations_key
from books.models import Author, Book, Category, ReadingStatus, UserBook
from books.services.recommendation_service import (
    get_book_recommendations,
    get_user_recommendations,
)
from books.tasks import precompute_user_recommendations_task

User = get_user_model()


@pytest.mark.django_db
class TestPhase24Recommendations:
    def setup_method(self):
        cache.clear()

    def test_user_recommendations_rules_based(self):
        """Verifica que libros del mismo género y autor tengan mayor puntuación."""
        cat_scifi = Category.objects.create(name='Ciencia Ficción', slug='ciencia-ficcion')
        cat_cooking = Category.objects.create(name='Cocina', slug='cocina')

        author_asimov = Author.objects.create(name='Isaac Asimov')
        author_chef = Author.objects.create(name='Chef Gusteau')

        user = User.objects.create_user(username='lector_scifi', email='scifi@test.com', password='pwd')

        # Libro ya leído y altamente valorado por el usuario
        book_read = Book.objects.create(title='Fundación', author=author_asimov, average_rating=4.8)
        book_read.categories.add(cat_scifi)
        UserBook.objects.create(user=user, book=book_read, status=ReadingStatus.READ, rating=5)

        # Libros candidatos
        book_asimov2 = Book.objects.create(title='Yo, Robot', author=author_asimov, average_rating=4.5)
        book_asimov2.categories.add(cat_scifi)

        book_cooking = Book.objects.create(title='Recetas Rápidas', author=author_chef, average_rating=4.0)
        book_cooking.categories.add(cat_cooking)

        recommendations = get_user_recommendations(user=user, limit=5, strategy='rules')
        assert len(recommendations) >= 1

        rec_titles = [r['title'] for r in recommendations]
        # El libro leído no debe estar en recomendaciones
        assert 'Fundación' not in rec_titles
        # Yo, Robot debe ser el primero por coincidir autor y categoría
        assert rec_titles[0] == 'Yo, Robot'
        assert recommendations[0]['score'] > 0
        assert 'Asimov' in recommendations[0]['reason'] or 'Ciencia Ficción' in recommendations[0]['reason']

    def test_user_recommendations_social(self):
        """Verifica que las lecturas de los usuarios seguidos generen recomendaciones sociales."""
        user = User.objects.create_user(username='usuario_principal', email='principal@test.com', password='pwd')
        amigo = User.objects.create_user(username='amigo_lector', email='amigo@test.com', password='pwd')

        user.following.add(amigo)

        author = Author.objects.create(name='Ursula K. Le Guin')
        cat = Category.objects.create(name='Fantasía', slug='fantasia')
        book_social = Book.objects.create(title='Los desposeídos', author=author, average_rating=4.7)
        book_social.categories.add(cat)

        # El amigo lee y valora el libro
        UserBook.objects.create(user=amigo, book=book_social, status=ReadingStatus.READ, rating=5)

        recs = get_user_recommendations(user=user, limit=5, strategy='social')
        assert len(recs) >= 1
        rec = recs[0]
        assert rec['id'] == book_social.id
        assert 'amigo_lector' in rec['reason'] or 'personas que sigues' in rec['reason']

    def test_user_recommendations_strict_exclusion(self):
        """Los libros presentes en la biblioteca del usuario jamás deben ser recomendados."""
        user = User.objects.create_user(username='lector_exclusiones', email='excl@test.com', password='pwd')
        author = Author.objects.create(name='Autor Test')
        book1 = Book.objects.create(title='Libro Propio 1', author=author)
        book2 = Book.objects.create(title='Libro Candidato 2', author=author)

        UserBook.objects.create(user=user, book=book1, status=ReadingStatus.WANT_TO_READ)

        recs = get_user_recommendations(user=user, limit=5)
        rec_ids = [r['id'] for r in recs]
        assert book1.id not in rec_ids
        assert book2.id in rec_ids

    def test_user_recommendations_cold_start(self):
        """Un usuario nuevo sin historial recibe recomendaciones populares sin errores."""
        new_user = User.objects.create_user(username='novato', email='novato@test.com', password='pwd')
        author = Author.objects.create(name='Autor Popular')
        Book.objects.create(title='Superventas Clásico', author=author, average_rating=4.9)

        recs = get_user_recommendations(user=new_user, limit=5)
        assert len(recs) >= 1
        assert recs[0]['title'] == 'Superventas Clásico'
        assert 'comunidad' in recs[0]['reason'].lower() or 'viaje' in recs[0]['reason'].lower()

    def test_book_contextual_recommendations(self):
        """Verifica las recomendaciones contextuales de libro a libro (Item-to-Item)."""
        author = Author.objects.create(name='J.R.R. Tolkien')
        cat = Category.objects.create(name='Fantasía Épica', slug='fantasia-epica')

        book_source = Book.objects.create(title='El Hobbit', author=author, average_rating=4.8)
        book_source.categories.add(cat)

        book_related = Book.objects.create(title='El Señor de los Anillos', author=author, average_rating=4.9)
        book_related.categories.add(cat)

        book_other = Book.objects.create(title='Manual de Redes', average_rating=3.0)

        recs = get_book_recommendations(book_id=book_source.id, limit=5)
        assert len(recs) >= 1
        rec_titles = [r['title'] for r in recs]
        assert 'El Hobbit' not in rec_titles
        assert 'El Señor de los Anillos' in rec_titles
        assert 'Manual de Redes' not in rec_titles

    def test_recommendations_api_views(self):
        """Verifica los endpoints REST de recomendaciones de usuario y libro."""
        user = User.objects.create_user(username='api_lector', email='api@test.com', password='pwd')
        author = Author.objects.create(name='Autor API')
        book = Book.objects.create(title='Libro API', author=author, average_rating=4.5)

        client = APIClient()
        client.force_authenticate(user=user)

        # 1. Endpoint recomendaciones personalizadas
        res_user = client.get('/api/v1/books/recommendations/')
        assert res_user.status_code == 200
        data_user = res_user.json()
        assert 'results' in data_user
        assert 'strategy' in data_user
        assert len(data_user['results']) >= 1

        # 2. Endpoint recomendaciones contextuales de libro
        res_book = client.get(f'/api/v1/books/{book.id}/recommendations/')
        assert res_book.status_code == 200
        data_book = res_book.json()
        assert isinstance(data_book, list)

    def test_recommendations_cache_and_invalidation(self):
        """Verifica almacenamiento en Redis e invalidación reactiva."""
        user = User.objects.create_user(username='cache_lector', email='cache@test.com', password='pwd')
        author = Author.objects.create(name='Autor Cache')
        book1 = Book.objects.create(title='Libro Cache 1', author=author, average_rating=4.5)
        book2 = Book.objects.create(title='Libro Cache 2', author=author, average_rating=4.6)

        c_key = user_recommendations_key(user.id, 'hybrid')
        assert cache.get(c_key) is None

        # Primera llamada calienta la caché
        get_user_recommendations(user=user, strategy='hybrid')
        assert cache.get(c_key) is not None

        # Guardar un UserBook debe invalidar la caché
        UserBook.objects.create(user=user, book=book1, status=ReadingStatus.READ)
        assert cache.get(c_key) is None

    def test_precompute_recommendations_task(self):
        """Verifica la tarea Celery de precomputación en segundo plano."""
        user = User.objects.create_user(username='celery_lector', email='celery@test.com', password='pwd')
        author = Author.objects.create(name='Autor Celery')
        Book.objects.create(title='Libro Celery', author=author, average_rating=4.7)

        count = precompute_user_recommendations_task.apply(args=[user.id]).get()
        assert count >= 1
        c_key = user_recommendations_key(user.id, 'hybrid')
        assert cache.get(c_key) is not None
