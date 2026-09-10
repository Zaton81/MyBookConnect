import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from books.models import Author, Book, Review
from messages_app.models import Conversation, Message
from users.models import PrivacyChoices
from users.policies import (
    can_access_conversation,
    can_edit_review,
    can_message,
    can_view_profile,
    can_view_review,
    filter_visible_reviews,
    filter_visible_users,
)

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def privacy_users():
    alice = User.objects.create_user(username='alice_priv', email='alice_priv@example.com', password='password123')
    bob = User.objects.create_user(username='bob_priv', email='bob_priv@example.com', password='password123')
    charlie = User.objects.create_user(username='charlie_priv', email='charlie_priv@example.com', password='password123')
    david = User.objects.create_user(username='david_priv', email='david_priv@example.com', password='password123')
    staff_user = User.objects.create_user(
        username='admin_priv', email='admin_priv@example.com', password='password123', is_staff=True
    )

    alice.privacy_level = PrivacyChoices.PUBLIC
    alice.save()
    bob.privacy_level = PrivacyChoices.PRIVATE
    bob.save()
    charlie.privacy_level = PrivacyChoices.FRIENDS
    charlie.save()
    david.privacy_level = PrivacyChoices.PUBLIC
    david.save()

    return {
        'alice': alice,
        'bob': bob,
        'charlie': charlie,
        'david': david,
        'staff': staff_user,
    }


@pytest.fixture
def sample_book():
    author = Author.objects.create(name='Test Author')
    return Book.objects.create(title='Privacy Testing Book', author=author, isbn='9781234567890')


@pytest.mark.django_db
class TestCentralizedPolicies:
    def test_can_view_profile_policy(self, privacy_users):
        alice = privacy_users['alice']      # public
        bob = privacy_users['bob']          # private
        charlie = privacy_users['charlie']  # friends
        staff = privacy_users['staff']

        # 1. Mismo usuario siempre True
        assert can_view_profile(bob, bob) is True

        # 2. Staff siempre True
        assert can_view_profile(staff, bob) is True

        # 3. Anónimo ve público, no privado ni amigos
        assert can_view_profile(None, alice) is True
        assert can_view_profile(None, bob) is False
        assert can_view_profile(None, charlie) is False

        # 4. Privado: denegado a otros usuarios
        assert can_view_profile(alice, bob) is False

        # 5. Amigos: denegado si no sigue
        assert can_view_profile(alice, charlie) is False
        alice.following.add(charlie)
        assert can_view_profile(alice, charlie) is True

        # 6. Bloqueo: si target bloqueó a viewer -> False
        alice.blocked_users.add(charlie)
        assert can_view_profile(charlie, alice) is False  # charlie no puede ver a alice
        # Pero alice puede ver a charlie para desbloquear
        assert can_view_profile(alice, charlie) is True

    def test_can_view_review_and_filter_visible_reviews(self, privacy_users, sample_book):
        alice = privacy_users['alice']
        bob = privacy_users['bob']
        charlie = privacy_users['charlie']

        r_alice = Review.objects.create(book=sample_book, user=alice, rating=9, title='Alice Review')
        r_bob = Review.objects.create(book=sample_book, user=bob, rating=8, title='Bob Review')
        r_charlie = Review.objects.create(book=sample_book, user=charlie, rating=7, title='Charlie Review')

        # can_view_review unit tests
        assert can_view_review(None, r_alice) is True
        assert can_view_review(None, r_bob) is False
        assert can_view_review(None, r_charlie) is False

        # Bob puede ver su propia reseña privada
        assert can_view_review(bob, r_bob) is True
        assert can_view_review(alice, r_bob) is False

        # Con amigos
        assert can_view_review(alice, r_charlie) is False
        alice.following.add(charlie)
        assert can_view_review(alice, r_charlie) is True

        # Bloqueo mutuo oculta review
        alice.blocked_users.add(charlie)
        assert can_view_review(alice, r_charlie) is False
        assert can_view_review(charlie, r_alice) is False

        # Queryset filter_visible_reviews
        qs = Review.objects.all()
        visible_alice = list(filter_visible_reviews(alice, qs))
        assert r_alice in visible_alice
        assert r_bob not in visible_alice
        assert r_charlie not in visible_alice  # Bloqueado

    def test_can_edit_review_policy(self, privacy_users, sample_book):
        alice = privacy_users['alice']
        bob = privacy_users['bob']
        staff = privacy_users['staff']

        r_alice = Review.objects.create(book=sample_book, user=alice, rating=9, title='Alice Review')

        assert can_edit_review(alice, r_alice) is True
        assert can_edit_review(bob, r_alice) is False
        assert can_edit_review(staff, r_alice) is True
        assert can_edit_review(None, r_alice) is False

    def test_can_access_conversation_and_message_policy(self, privacy_users):
        alice = privacy_users['alice']
        david = privacy_users['david']

        conv = Conversation.objects.create()
        conv.participants.add(alice, david)

        assert can_access_conversation(alice, conv) is True
        assert can_access_conversation(privacy_users['bob'], conv) is False

        # can_message: no son amigos mutuos todavía
        assert can_message(alice, david) is False

        # Ahora son amigos mutuos
        alice.following.add(david)
        david.following.add(alice)
        assert can_message(alice, david) is True

        # Si uno bloquea al otro
        alice.blocked_users.add(david)
        assert can_message(alice, david) is False
        assert can_message(david, alice) is False


@pytest.mark.django_db
class TestPermissionsAndPrivacyIntegration:
    def test_bidirectional_unfollow_on_block(self, api_client, privacy_users):
        alice = privacy_users['alice']
        david = privacy_users['david']

        # Establecer seguimiento mutuo
        alice.following.add(david)
        david.following.add(alice)
        assert alice.following.filter(id=david.id).exists()
        assert david.following.filter(id=alice.id).exists()

        api_client.force_authenticate(user=alice)
        res = api_client.post(f'/api/v1/users/{david.id}/block/')
        assert res.status_code == 200

        # Bloqueo registrado
        assert alice.blocked_users.filter(id=david.id).exists()
        # Ruptura bidireccional de seguimiento
        assert not alice.following.filter(id=david.id).exists()
        assert not david.following.filter(id=alice.id).exists()

    def test_follow_blocked_user_forbidden(self, api_client, privacy_users):
        alice = privacy_users['alice']
        david = privacy_users['david']

        # Alice bloquea a David
        alice.blocked_users.add(david)

        # David intenta seguir a Alice -> 403
        api_client.force_authenticate(user=david)
        res_david = api_client.post(f'/api/v1/users/{alice.id}/follow/')
        assert res_david.status_code == 403

        # Alice intenta seguir a David a quien tiene bloqueado -> 403
        api_client.force_authenticate(user=alice)
        res_alice = api_client.post(f'/api/v1/users/{david.id}/follow/')
        assert res_alice.status_code == 403

    def test_user_search_excludes_blocked_users(self, api_client, privacy_users):
        alice = privacy_users['alice']
        david = privacy_users['david']

        # Búsqueda inicial encuentra a david_priv
        api_client.force_authenticate(user=alice)
        res_before = api_client.get('/api/v1/users/search/?q=david_priv')
        assert res_before.status_code == 200
        results = res_before.data if isinstance(res_before.data, list) else res_before.data.get('results', [])
        assert any(u['username'] == 'david_priv' for u in results)

        # Alice bloquea a David
        alice.blocked_users.add(david)

        # David ya no debe aparecer en la búsqueda de Alice
        res_after = api_client.get('/api/v1/users/search/?q=david_priv')
        assert res_after.status_code == 200
        results_after = res_after.data if isinstance(res_after.data, list) else res_after.data.get('results', [])
        assert not any(u['username'] == 'david_priv' for u in results_after)

        # Y Alice no debe aparecer en la búsqueda de David
        api_client.force_authenticate(user=david)
        res_david = api_client.get('/api/v1/users/search/?q=alice_priv')
        assert res_david.status_code == 200
        results_david = res_david.data if isinstance(res_david.data, list) else res_david.data.get('results', [])
        assert not any(u['username'] == 'alice_priv' for u in results_david)

    def test_reviews_list_excludes_blocked_users(self, api_client, privacy_users, sample_book):
        alice = privacy_users['alice']
        david = privacy_users['david']

        Review.objects.create(book=sample_book, user=david, rating=9, title='David Review')

        api_client.force_authenticate(user=alice)
        res_before = api_client.get(f'/api/v1/books/reviews/?book={sample_book.id}')
        assert res_before.status_code == 200
        results = res_before.data if isinstance(res_before.data, list) else res_before.data.get('results', [])
        assert any(r['title'] == 'David Review' for r in results)

        # Alice bloquea a David
        alice.blocked_users.add(david)

        # David's review disappears from Alice's book reviews view
        res_after = api_client.get(f'/api/v1/books/reviews/?book={sample_book.id}')
        assert res_after.status_code == 200
        results_after = res_after.data if isinstance(res_after.data, list) else res_after.data.get('results', [])
        assert not any(r['title'] == 'David Review' for r in results_after)

    def test_message_create_blocked_user_denied(self, api_client, privacy_users):
        alice = privacy_users['alice']
        david = privacy_users['david']

        # Amigos mutuos
        alice.following.add(david)
        david.following.add(alice)

        conv = Conversation.objects.create()
        conv.participants.add(alice, david)

        api_client.force_authenticate(user=alice)
        msg_res = api_client.post('/api/v1/users/messages/', {'conversation': conv.id, 'text': 'Hola David'})
        assert msg_res.status_code == 201

        # David bloquea a Alice
        david.blocked_users.add(alice)

        # Alice intenta enviar otro mensaje -> denegado (ValidationError 400)
        msg_res_blocked = api_client.post('/api/v1/users/messages/', {'conversation': conv.id, 'text': 'Sigues ahi?'})
        assert msg_res_blocked.status_code == 400
