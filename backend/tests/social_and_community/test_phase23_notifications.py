import pytest
from rest_framework import status
from users.models import Notification, NotificationPreference, NotificationType, User
from users.notification_service import NotificationService
from books.models import Book, Author, Review, ReviewComment, ReadingList, ReadingListPrivacy


from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def users_for_notifications(db):
    u1 = User.objects.create_user(username='alice_notif', email='alice@test.com', password='password123')
    u2 = User.objects.create_user(username='bob_notif', email='bob@test.com', password='password123')
    u3 = User.objects.create_user(username='charlie_notif', email='charlie@test.com', password='password123')
    return {'alice': u1, 'bob': u2, 'charlie': u3}


@pytest.fixture
def sample_book_and_review(db, users_for_notifications):
    alice = users_for_notifications['alice']
    author = Author.objects.create(name='Test Author')
    book = Book.objects.create(title='Libro de Notificaciones', isbn='9781234567897', author=author)
    review = Review.objects.create(book=book, user=alice, rating=5, title='Excelente', text='Gran libro')
    return {'book': book, 'review': review}


@pytest.mark.django_db
class TestNotificationService:
    def test_send_notification_creates_in_app(self, users_for_notifications):
        alice = users_for_notifications['alice']
        bob = users_for_notifications['bob']

        notif = NotificationService.send_notification(
            recipient=alice,
            actor=bob,
            notif_type=NotificationType.FOLLOW,
            title='Nuevo seguidor',
            message='Bob te ha seguido',
            link='/users/bob',
        )

        assert notif is not None
        assert notif.recipient == alice
        assert notif.actor == bob
        assert notif.type == NotificationType.FOLLOW
        assert notif.read is False
        assert Notification.objects.filter(recipient=alice).count() == 1

    def test_no_self_notification(self, users_for_notifications):
        alice = users_for_notifications['alice']
        notif = NotificationService.send_notification(
            recipient=alice,
            actor=alice,
            notif_type=NotificationType.LIKE,
            title='Auto-like',
        )
        assert notif is None
        assert Notification.objects.filter(recipient=alice).count() == 0

    def test_respects_in_app_preference_disabled(self, users_for_notifications):
        alice = users_for_notifications['alice']
        bob = users_for_notifications['bob']

        prefs = NotificationService.get_or_create_preferences(alice)
        prefs.in_app_like = False
        prefs.save()

        notif = NotificationService.send_notification(
            recipient=alice,
            actor=bob,
            notif_type=NotificationType.LIKE,
            title='A Bob le gustó tu reseña',
        )
        assert notif is None
        assert Notification.objects.filter(recipient=alice, type=NotificationType.LIKE).count() == 0

    def test_respects_blocked_user_policy(self, users_for_notifications):
        alice = users_for_notifications['alice']
        bob = users_for_notifications['bob']

        # Alice bloquea a Bob
        alice.blocked_users.add(bob)

        notif = NotificationService.send_notification(
            recipient=alice,
            actor=bob,
            notif_type=NotificationType.FOLLOW,
            title='Nuevo seguidor',
        )
        assert notif is None
        assert Notification.objects.filter(recipient=alice).count() == 0

    def test_respects_muted_user_policy(self, users_for_notifications):
        alice = users_for_notifications['alice']
        bob = users_for_notifications['bob']

        # Alice silencia a Bob
        alice.muted_users.add(bob)

        notif = NotificationService.send_notification(
            recipient=alice,
            actor=bob,
            notif_type=NotificationType.COMMENT,
            title='Bob comentó',
        )
        assert notif is None
        assert Notification.objects.filter(recipient=alice).count() == 0

    def test_email_dispatch_does_not_crash(self, users_for_notifications):
        alice = users_for_notifications['alice']
        bob = users_for_notifications['bob']

        prefs = NotificationService.get_or_create_preferences(alice)
        prefs.email_comment = True
        prefs.save()

        # Debe ejecutarse sin lanzar excepciones incluso si no hay SMTP activo
        notif = NotificationService.send_notification(
            recipient=alice,
            actor=bob,
            notif_type=NotificationType.COMMENT,
            title='Nuevo comentario',
            message='Contenido de prueba',
            link='/books/1',
        )
        assert notif is not None


@pytest.mark.django_db
class TestNotificationAPIEndpoints:
    def test_get_and_patch_preferences(self, api_client, users_for_notifications):
        alice = users_for_notifications['alice']
        api_client.force_authenticate(user=alice)

        # GET preferences
        res = api_client.get('/api/v1/users/notifications/preferences/')
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data['in_app_follow'] is True
        assert data['email_follow'] is False

        # PATCH preferences
        patch_res = api_client.patch('/api/v1/users/notifications/preferences/', {
            'in_app_follow': False,
            'email_follow': True,
            'push_enabled': True,
        }, format='json')
        assert patch_res.status_code == status.HTTP_200_OK
        updated = patch_res.json()
        assert updated['in_app_follow'] is False
        assert updated['email_follow'] is True
        assert updated['push_enabled'] is True

    def test_notification_list_filtering(self, api_client, users_for_notifications):
        alice = users_for_notifications['alice']
        bob = users_for_notifications['bob']

        Notification.objects.create(recipient=alice, actor=bob, type=NotificationType.FOLLOW, title='Follow 1', read=False)
        Notification.objects.create(recipient=alice, actor=bob, type=NotificationType.LIKE, title='Like 1', read=True)
        Notification.objects.create(recipient=alice, actor=bob, type=NotificationType.LIKE, title='Like 2', read=False)

        api_client.force_authenticate(user=alice)

        # 1. Total
        res_all = api_client.get('/api/v1/users/notifications/')
        assert res_all.status_code == status.HTTP_200_OK
        all_results = res_all.json()
        items = all_results if isinstance(all_results, list) else all_results.get('results', [])
        assert len(items) == 3

        # 2. Filter unread
        res_unread = api_client.get('/api/v1/users/notifications/?unread=1')
        unread_items = res_unread.json() if isinstance(res_unread.json(), list) else res_unread.json().get('results', [])
        assert len(unread_items) == 2

        # 3. Filter by type
        res_type = api_client.get('/api/v1/users/notifications/?type=FOLLOW')
        type_items = res_type.json() if isinstance(res_type.json(), list) else res_type.json().get('results', [])
        assert len(type_items) == 1
        assert type_items[0]['title'] == 'Follow 1'

    def test_notification_mark_read_and_clear_read(self, api_client, users_for_notifications):
        alice = users_for_notifications['alice']
        bob = users_for_notifications['bob']

        n1 = Notification.objects.create(recipient=alice, actor=bob, type=NotificationType.COMMENT, title='C1', read=False)
        n2 = Notification.objects.create(recipient=alice, actor=bob, type=NotificationType.COMMENT, title='C2', read=False)

        api_client.force_authenticate(user=alice)

        # Unread count inicial: 2
        res_count = api_client.get('/api/v1/users/notifications/unread-count/')
        assert res_count.status_code == status.HTTP_200_OK
        assert res_count.json()['unread_count'] == 2

        # Marcar n1 como leída
        res_read = api_client.post(f'/api/v1/users/notifications/{n1.id}/read/')
        assert res_read.status_code == status.HTTP_200_OK
        n1.refresh_from_db()
        assert n1.read is True

        # Unread count ahora: 1
        res_count2 = api_client.get('/api/v1/users/notifications/unread-count/')
        assert res_count2.json()['unread_count'] == 1

        # Marcar todas leídas
        res_read_all = api_client.post('/api/v1/users/notifications/read-all/')
        assert res_read_all.status_code == status.HTTP_200_OK
        assert Notification.objects.filter(recipient=alice, read=False).count() == 0

        # Eliminar leídas
        res_clear = api_client.post('/api/v1/users/notifications/clear-read/')
        assert res_clear.status_code == status.HTTP_200_OK
        assert res_clear.json()['deleted_count'] == 2
        assert Notification.objects.filter(recipient=alice).count() == 0

    def test_notification_delete_individual(self, api_client, users_for_notifications):
        alice = users_for_notifications['alice']
        bob = users_for_notifications['bob']

        n = Notification.objects.create(recipient=alice, actor=bob, type=NotificationType.MESSAGE, title='Msg', read=False)
        api_client.force_authenticate(user=alice)

        del_res = api_client.delete(f'/api/v1/users/notifications/{n.id}/')
        assert del_res.status_code == status.HTTP_204_NO_CONTENT
        assert Notification.objects.filter(id=n.id).exists() is False


@pytest.mark.django_db
class TestSocialIntegrationNotifications:
    def test_reading_list_follow_triggers_notification(self, api_client, users_for_notifications):
        alice = users_for_notifications['alice']
        bob = users_for_notifications['bob']

        rlist = ReadingList.objects.create(
            user=alice,
            name='Lista Favoritos Alice',
            privacy=ReadingListPrivacy.PUBLIC,
        )

        api_client.force_authenticate(user=bob)
        follow_res = api_client.post(f'/api/v1/books/reading-lists/{rlist.id}/follow/')
        assert follow_res.status_code == status.HTTP_200_OK

        notif = Notification.objects.filter(recipient=alice, actor=bob, type=NotificationType.LIST_FOLLOW).first()
        assert notif is not None
        assert 'ha comenzado a seguir tu lista' in notif.message

    def test_review_reply_triggers_reply_notification(self, api_client, users_for_notifications, sample_book_and_review):
        alice = users_for_notifications['alice']
        bob = users_for_notifications['bob']
        charlie = users_for_notifications['charlie']
        review = sample_book_and_review['review']

        # Bob comenta en la reseña de Alice
        c1 = ReviewComment.objects.create(user=bob, review=review, content='Comentario de Bob')

        # Charlie responde al comentario de Bob
        api_client.force_authenticate(user=charlie)
        res = api_client.post(f'/api/v1/reviews/{review.id}/comments/', {
            'content': 'Respuesta de Charlie para Bob',
            'parent_id': c1.id,
        }, format='json')
        assert res.status_code == status.HTTP_201_CREATED

        # Bob debe recibir una notificación de tipo REPLY
        notif = Notification.objects.filter(recipient=bob, actor=charlie, type=NotificationType.REPLY).first()
        assert notif is not None
        assert 'respondió a tu comentario' in notif.title
