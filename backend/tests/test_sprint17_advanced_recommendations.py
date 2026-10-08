import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

from books.models import (
    Author,
    Book,
    Category,
    ReadingStatus,
    RecommendationFeedback,
    RecommendationFeedbackAction,
    UserBook,
)

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def sample_data(db):
    cache.clear()
    user1 = User.objects.create_user(username='reader_alpha', email='alpha@test.com', password='password123')
    user2 = User.objects.create_user(username='reader_beta', email='beta@test.com', password='password123')

    author_garcia = Author.objects.create(name='Gabriel García Márquez')
    author_herbert = Author.objects.create(name='Frank Herbert')
    author_tolkien = Author.objects.create(name='J.R.R. Tolkien')

    cat_realismo = Category.objects.create(name='Realismo Mágico')
    cat_scifi = Category.objects.create(name='Ciencia Ficción')
    cat_fantasia = Category.objects.create(name='Fantasía Épica')

    # Libros de diferentes longitudes y géneros
    book_soledad = Book.objects.create(
        title='Cien Años de Soledad',
        author=author_garcia,
        average_rating=4.9,
    )
    book_soledad.categories.add(cat_realismo)

    book_amor = Book.objects.create(
        title='El Amor en los Tiempos del Cólera',
        author=author_garcia,
        average_rating=4.7,
    )
    book_amor.categories.add(cat_realismo)

    book_dune = Book.objects.create(
        title='Dune',
        author=author_herbert,
        average_rating=4.8,
    )
    book_dune.categories.add(cat_scifi)

    book_cronica = Book.objects.create(
        title='Crónica de una muerte anunciada',
        author=author_garcia,
        average_rating=4.5,
    )
    book_cronica.categories.add(cat_realismo)

    book_hobbit = Book.objects.create(
        title='El Hobbit',
        author=author_tolkien,
        average_rating=4.6,
    )
    book_hobbit.categories.add(cat_fantasia)

    # El usuario 1 leyó Cien Años de Soledad con 5 estrellas
    UserBook.objects.create(
        user=user1,
        book=book_soledad,
        current_page=420,
        status=ReadingStatus.READ,
        rating=5,
    )

    # El usuario 2 leyó varias obras asignando páginas comunitarias (lector afín)
    UserBook.objects.create(
        user=user2,
        book=book_soledad,
        current_page=420,
        status=ReadingStatus.READ,
        rating=5,
    )
    UserBook.objects.create(
        user=user2,
        book=book_hobbit,
        current_page=310,
        status=ReadingStatus.READ,
        rating=5,
    )
    UserBook.objects.create(
        user=user2,
        book=book_cronica,
        current_page=120,
        status=ReadingStatus.READ,
        rating=4,
    )
    UserBook.objects.create(
        user=user2,
        book=book_amor,
        current_page=350,
        status=ReadingStatus.READ,
        rating=4,
    )
    UserBook.objects.create(
        user=user2,
        book=book_dune,
        current_page=650,
        status=ReadingStatus.READ,
        rating=5,
    )

    return {
        'user1': user1,
        'user2': user2,
        'author_garcia': author_garcia,
        'author_herbert': author_herbert,
        'author_tolkien': author_tolkien,
        'cat_realismo': cat_realismo,
        'cat_scifi': cat_scifi,
        'cat_fantasia': cat_fantasia,
        'book_soledad': book_soledad,
        'book_amor': book_amor,
        'book_dune': book_dune,
        'book_cronica': book_cronica,
        'book_hobbit': book_hobbit,
    }


@pytest.mark.django_db
def test_user_recommendations_hybrid_with_affinity_percentage_and_categories(api_client, sample_data):
    """
    1. Verifica que las recomendaciones híbridas incluyan porcentaje de afinidad (affinity_percentage),
       listado de categorías, desglose y que excluyan los libros ya leídos.
    """
    user1 = sample_data['user1']
    api_client.force_authenticate(user=user1)

    res = api_client.get('/api/v1/books/recommendations/?strategy=hybrid')
    assert res.status_code == status.HTTP_200_OK

    data = res.json()
    assert 'results' in data
    assert data['count'] > 0

    # Cien Años de Soledad ya fue leído por user1, no debe estar en las recomendaciones
    book_ids = [b['id'] for b in data['results']]
    assert sample_data['book_soledad'].id not in book_ids

    # Verificar estructura enriquecida de cada libro recomendado
    first_rec = data['results'][0]
    assert 'affinity_percentage' in first_rec
    assert 60 <= first_rec['affinity_percentage'] <= 99
    assert 'categories' in first_rec
    assert isinstance(first_rec['categories'], list)
    assert 'reason' in first_rec
    assert len(first_rec['reason']) > 0


@pytest.mark.django_db
def test_user_recommendations_filter_by_category(api_client, sample_data):
    """
    2. Verifica el filtrado granular por categoría/género (?category_id=X).
    """
    user1 = sample_data['user1']
    cat_scifi = sample_data['cat_scifi']
    api_client.force_authenticate(user=user1)

    res = api_client.get(f'/api/v1/books/recommendations/?category_id={cat_scifi.id}')
    assert res.status_code == status.HTTP_200_OK

    data = res.json()
    assert data['count'] > 0
    # Todos los resultados deben tener la categoría Ciencia Ficción
    for b in data['results']:
        cat_ids = [c['id'] for c in b['categories']]
        assert cat_scifi.id in cat_ids


@pytest.mark.django_db
def test_user_recommendations_filter_by_length_tier(api_client, sample_data):
    """
    3. Verifica el filtrado de recomendaciones por tramo de longitud de lectura.
    """
    user1 = sample_data['user1']
    api_client.force_authenticate(user=user1)

    # Tramo corto: < 200 páginas (ej: Crónica de una muerte anunciada, 120p)
    res_short = api_client.get('/api/v1/books/recommendations/?length_tier=short')
    assert res_short.status_code == status.HTTP_200_OK
    data_short = res_short.json()
    assert any(b['id'] == sample_data['book_cronica'].id for b in data_short['results'])
    assert not any(b['id'] == sample_data['book_dune'].id for b in data_short['results'])

    # Tramo épico: >= 600 páginas (ej: Dune, 650p)
    res_epic = api_client.get('/api/v1/books/recommendations/?length_tier=epic')
    assert res_epic.status_code == status.HTTP_200_OK
    data_epic = res_epic.json()
    assert any(b['id'] == sample_data['book_dune'].id for b in data_epic['results'])
    assert not any(b['id'] == sample_data['book_cronica'].id for b in data_epic['results'])


@pytest.mark.django_db
def test_dismiss_recommendation_and_auto_exclusion(api_client, sample_data):
    """
    4. Verifica que descartar un libro con POST /recommendations/dismiss/ registre el feedback
       y excluya inmediatamente el libro de las siguientes recomendaciones.
    """
    user1 = sample_data['user1']
    book_dune = sample_data['book_dune']
    api_client.force_authenticate(user=user1)

    # 1. Descartar Dune
    dismiss_res = api_client.post('/api/v1/books/recommendations/dismiss/', {
        'book_id': book_dune.id,
        'reason': 'not_my_genre',
    })
    assert dismiss_res.status_code == status.HTTP_200_OK
    assert dismiss_res.json()['success'] is True
    assert dismiss_res.json()['dismissed_book_id'] == book_dune.id

    # Comprobar que existe el feedback en base de datos
    fb = RecommendationFeedback.objects.filter(
        user=user1,
        book=book_dune,
        action=RecommendationFeedbackAction.DISMISSED,
    ).first()
    assert fb is not None
    assert fb.metadata.get('reason') == 'not_my_genre'

    # 2. Solicitar recomendaciones: Dune no debe aparecer
    recs_res = api_client.get('/api/v1/books/recommendations/?exclude_dismissed=true')
    assert recs_res.status_code == status.HTTP_200_OK
    book_ids = [b['id'] for b in recs_res.json()['results']]
    assert book_dune.id not in book_ids


@pytest.mark.django_db
def test_recommendation_strategies_multimodal(api_client, sample_data):
    """
    5. Verifica que las distintas estrategias (v3/hybrid_v3, v2/collab, v1, serendipity)
       respondan con HTTP 200 y motivos acordes a su modelo.
    """
    user1 = sample_data['user1']
    api_client.force_authenticate(user=user1)

    for strat in ('hybrid', 'v3', 'v2', 'v1', 'serendipity'):
        res = api_client.get(f'/api/v1/books/recommendations/?strategy={strat}')
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data['count'] > 0
        assert 'results' in data


@pytest.mark.django_db
def test_similar_readers_endpoint(api_client, sample_data):
    """
    6. Verifica que el endpoint /recommendations/similar-readers/ identifique usuarios
       con alta afinidad de lecturas compartidas y calcule similarity_score y shared_books_count.
    """
    user1 = sample_data['user1']
    user2 = sample_data['user2']
    api_client.force_authenticate(user=user1)

    res = api_client.get('/api/v1/books/recommendations/similar-readers/')
    assert res.status_code == status.HTTP_200_OK

    data = res.json()
    assert 'results' in data
    assert data['count'] >= 1

    reader_beta = next((r for r in data['results'] if r['user_id'] == user2.id), None)
    assert reader_beta is not None
    assert reader_beta['username'] == 'reader_beta'
    assert reader_beta['shared_books_count'] >= 1
    assert reader_beta['similarity_score'] > 0.0


@pytest.mark.django_db
def test_recommendation_caching_and_invalidation(api_client, sample_data):
    """
    7. Verifica que las recomendaciones se guarden en caché con claves segregadas
       y se invaliden de forma limpia al descartar un libro.
    """
    user1 = sample_data['user1']
    book_amor = sample_data['book_amor']
    api_client.force_authenticate(user=user1)

    # 1. Petición inicial (puebla caché)
    res1 = api_client.get('/api/v1/books/recommendations/?strategy=hybrid')
    assert res1.status_code == status.HTTP_200_OK

    # 2. Descarte de un libro
    api_client.post('/api/v1/books/recommendations/dismiss/', {'book_id': book_amor.id})

    # 3. Petición posterior: comprueba que no viene de caché sucia y excluye el libro
    res2 = api_client.get('/api/v1/books/recommendations/?strategy=hybrid')
    assert res2.status_code == status.HTTP_200_OK
    recs_after = [b['id'] for b in res2.json()['results']]
    assert book_amor.id not in recs_after
