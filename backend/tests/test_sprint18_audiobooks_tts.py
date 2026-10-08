"""
Suite de Pruebas Automatizadas — Sprint 18: Audiolibros y Text-to-Speech (TTS).
Verifica modelos, capa de servicios, endpoints REST, sincronización de progreso,
catálogo y accesibilidad por voz (TTS).
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from books.models import Book, Author, Category, AudiobookTrack, UserAudiobookProgress
from books.services import (
    get_book_audiobook_details,
    save_audiobook_progress,
    get_user_listening_shelf,
    get_audiobook_catalog,
)

User = get_user_model()


@pytest.fixture
def auth_client():
    client = APIClient()
    user = User.objects.create_user(
        username='audioloader',
        email='audioloader@test.com',
        password='passWord123!',
    )
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def sample_audiobook_data():
    author = Author.objects.create(name='Gabriel García Márquez')
    cat_fic = Category.objects.create(name='Realismo Mágico')

    book = Book.objects.create(
        title='Cien años de soledad (Edición Sonora)',
        author=author,
        description='Muchos años después, frente al pelotón de fusilamiento...',
    )
    book.categories.add(cat_fic)

    track1 = AudiobookTrack.objects.create(
        book=book,
        title='Capítulo 1: Macondo',
        track_number=1,
        audio_url='https://cdn.mybookconnect.com/audio/soledad_ch1.mp3',
        duration_seconds=1800,  # 30 minutos
        narrator_name='Víctor Manuel',
        is_sample=True,
    )
    track2 = AudiobookTrack.objects.create(
        book=book,
        title='Capítulo 2: Los gitanos',
        track_number=2,
        audio_url='https://cdn.mybookconnect.com/audio/soledad_ch2.mp3',
        duration_seconds=2400,  # 40 minutos
        narrator_name='Víctor Manuel',
        is_sample=False,
    )

    # Libro sin pistas pero con descripción para validar TTS fallback
    book_tts_only = Book.objects.create(
        title='Crónica de una muerte anunciada',
        author=author,
        description='El día en que lo iban a matar, Santiago Nasar se levantó a las 5:30 de la mañana.',
    )

    return {
        'book': book,
        'book_tts_only': book_tts_only,
        'track1': track1,
        'track2': track2,
        'category': cat_fic,
    }


@pytest.mark.django_db
class TestSprint18AudiobooksAndTTS:

    def test_audiobook_track_creation_and_duration_format(self, sample_audiobook_data):
        track1 = sample_audiobook_data['track1']
        assert track1.formatted_duration == "30:00"
        assert track1.stream_url == 'https://cdn.mybookconnect.com/audio/soledad_ch1.mp3'
        assert str(track1) == "Cien años de soledad (Edición Sonora) - #1 Capítulo 1: Macondo"

    def test_get_book_audiobook_details_unauthenticated_and_authenticated(self, sample_audiobook_data):
        book = sample_audiobook_data['book']
        anon_user = None

        # 1. Consulta sin usuario autenticado
        details = get_book_audiobook_details(book.id, user=anon_user)
        assert details['has_audiobook'] is True
        assert details['tracks_count'] == 2
        assert details['total_duration_seconds'] == 4200  # 30m + 40m = 70m = 1 h 10 min
        assert details['formatted_total_duration'] == "1 h 10 min"
        assert details['narrators'] == ['Víctor Manuel']
        assert details['sample_track']['id'] == sample_audiobook_data['track1'].id
        assert details['progress'] is None

        # 2. Con usuario con progreso
        user = User.objects.create_user(username='listener1', email='l1@test.com', password='pwd')
        UserAudiobookProgress.objects.create(
            user=user,
            book=book,
            current_track=sample_audiobook_data['track2'],
            position_seconds=2100,  # 50%
            playback_speed=1.25,
            is_completed=False,
        )

        details_auth = get_book_audiobook_details(book.id, user=user)
        assert details_auth['progress'] is not None
        assert details_auth['progress']['current_track_id'] == sample_audiobook_data['track2'].id
        assert details_auth['progress']['position_seconds'] == 2100
        assert details_auth['progress']['playback_speed'] == 1.25
        assert details_auth['progress']['completion_percentage'] == 50.0

    def test_api_get_audiobook_detail_endpoint(self, sample_audiobook_data):
        client = APIClient()
        book = sample_audiobook_data['book']

        url = f"/api/v1/books/{book.id}/audiobook/"
        resp = client.get(url)
        assert resp.status_code == 200
        assert resp.data['book_id'] == book.id
        assert len(resp.data['tracks']) == 2
        assert resp.data['sample_track'] is not None

    def test_save_audiobook_progress_api_and_service(self, auth_client, sample_audiobook_data):
        client, user = auth_client
        book = sample_audiobook_data['book']
        track = sample_audiobook_data['track1']

        url = f"/api/v1/books/{book.id}/audiobook/progress/"
        payload = {
            'track_id': track.id,
            'position_seconds': 600,
            'playback_speed': 1.5,
            'is_completed': False,
        }
        resp = client.post(url, data=payload, format='json')
        assert resp.status_code == 200
        assert resp.data['status'] == 'saved'
        assert resp.data['position_seconds'] == 600
        assert resp.data['playback_speed'] == 1.5

        # Verificar persistencia en base de datos
        db_prog = UserAudiobookProgress.objects.get(user=user, book=book)
        assert db_prog.current_track_id == track.id
        assert db_prog.position_seconds == 600
        assert db_prog.playback_speed == 1.5

    def test_save_audiobook_progress_validation_errors(self, auth_client, sample_audiobook_data):
        client, _ = auth_client
        book = sample_audiobook_data['book']

        url = f"/api/v1/books/{book.id}/audiobook/progress/"
        # Pista inexistente o no perteneciente
        resp = client.post(url, data={'track_id': 99999, 'position_seconds': 100}, format='json')
        assert resp.status_code == 400
        assert 'detail' in resp.data

    def test_audiobook_catalog_and_category_filter(self, sample_audiobook_data):
        client = APIClient()
        url = "/api/v1/books/audiobooks/"

        resp = client.get(url)
        assert resp.status_code == 200
        assert resp.data['total'] >= 1
        results = resp.data['results']
        found = [b for b in results if b['book_id'] == sample_audiobook_data['book'].id]
        assert len(found) == 1
        assert found[0]['tracks_count'] == 2
        assert found[0]['has_sample'] is True

        # Filtrar por categoría
        cat_id = sample_audiobook_data['category'].id
        resp_cat = client.get(f"{url}?category_id={cat_id}")
        assert resp_cat.status_code == 200
        assert resp_cat.data['total'] >= 1

    def test_user_listening_shelf_and_tts_fallback(self, auth_client, sample_audiobook_data):
        client, user = auth_client
        book = sample_audiobook_data['book']
        book_tts = sample_audiobook_data['book_tts_only']

        # Guardar progreso
        save_audiobook_progress(
            user=user,
            book_id=book.id,
            track_id=sample_audiobook_data['track1'].id,
            position_seconds=900,
        )

        url_shelf = "/api/v1/books/audiobooks/in-progress/"
        resp_shelf = client.get(url_shelf)
        assert resp_shelf.status_code == 200
        assert resp_shelf.data['count'] == 1
        assert resp_shelf.data['results'][0]['book_id'] == book.id
        assert resp_shelf.data['results'][0]['position_seconds'] == 900

        # Verificar TTS fallback en libro sin pistas grabadas
        tts_details = get_book_audiobook_details(book_tts.id, user=user)
        assert tts_details['has_audiobook'] is False
        assert tts_details['tracks_count'] == 0
        assert tts_details['tts']['is_available'] is True
        assert tts_details['tts']['word_count'] > 0
        assert 'Santiago Nasar' in tts_details['tts']['text_content']
