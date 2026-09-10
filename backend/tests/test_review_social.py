import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from books.models import Author, Book, Review, ReviewComment, ReviewLike
from users.models import Notification, NotificationType

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def users_fixture():
    author_user = User.objects.create_user(username="reviewer", email="rev@example.com", password="password123")
    liker_user = User.objects.create_user(username="liker", email="like@example.com", password="password123")
    blocked_user = User.objects.create_user(username="blocked", email="blocked@example.com", password="password123")
    # Author blocks blocked_user
    author_user.blocked_users.add(blocked_user)

    author = Author.objects.create(name="Gabriel García Márquez")
    book = Book.objects.create(
        title="Cien años de soledad",
        isbn="9780307474728",
        author=author,
    )
    review = Review.objects.create(
        user=author_user,
        book=book,
        rating=10,
        title="Obra maestra",
        text="Realismo mágico en su máxima expresión.",
    )
    return {
        "author_user": author_user,
        "liker_user": liker_user,
        "blocked_user": blocked_user,
        "book": book,
        "review": review,
    }


@pytest.mark.django_db
class TestReviewLikesAndComments:
    def test_like_toggle_and_notification(self, api_client, users_fixture):
        liker = users_fixture["liker_user"]
        review = users_fixture["review"]
        api_client.force_authenticate(user=liker)

        # 1. Like
        res = api_client.post(f"/api/v1/books/reviews/{review.id}/like/")
        assert res.status_code == 200
        assert res.data["liked"] is True
        assert res.data["likes_count"] == 1
        assert ReviewLike.objects.filter(user=liker, review=review).exists()

        # Check notification received by review author
        notif = Notification.objects.filter(
            recipient=review.user,
            actor=liker,
            type=NotificationType.LIKE,
        ).first()
        assert notif is not None
        assert "le dio me gusta" in notif.title

        # 2. Unlike (toggle)
        res_unlike = api_client.post(f"/api/v1/books/reviews/{review.id}/like/")
        assert res_unlike.status_code == 200
        assert res_unlike.data["liked"] is False
        assert res_unlike.data["likes_count"] == 0
        assert not ReviewLike.objects.filter(user=liker, review=review).exists()

    def test_self_like_does_not_create_notification(self, api_client, users_fixture):
        author = users_fixture["author_user"]
        review = users_fixture["review"]
        api_client.force_authenticate(user=author)

        res = api_client.post(f"/api/v1/books/reviews/{review.id}/like/")
        assert res.status_code == 200
        assert res.data["liked"] is True

        # Notification should not be created for self-like
        notif = Notification.objects.filter(
            recipient=author,
            actor=author,
            type=NotificationType.LIKE,
        ).first()
        assert notif is None

    def test_blocked_user_cannot_like_review(self, api_client, users_fixture):
        blocked = users_fixture["blocked_user"]
        review = users_fixture["review"]
        api_client.force_authenticate(user=blocked)

        res = api_client.post(f"/api/v1/books/reviews/{review.id}/like/")
        assert res.status_code == 403
        assert not ReviewLike.objects.filter(user=blocked, review=review).exists()

    def test_comment_lifecycle_and_notification(self, api_client, users_fixture):
        liker = users_fixture["liker_user"]
        review = users_fixture["review"]
        api_client.force_authenticate(user=liker)

        # 1. Post comment
        res = api_client.post(
            f"/api/v1/books/reviews/{review.id}/comments/",
            {"content": "Totalmente de acuerdo, es mi favorito."},
            format="json",
        )
        assert res.status_code == 201
        assert res.data["content"] == "Totalmente de acuerdo, es mi favorito."
        assert res.data["user"]["username"] == liker.username
        assert res.data["is_owner"] is True
        comment_id = res.data["id"]

        # Check notification
        notif = Notification.objects.filter(
            recipient=review.user,
            actor=liker,
            type=NotificationType.COMMENT,
        ).first()
        assert notif is not None
        assert "comentó en tu reseña" in notif.title

        # 2. List comments
        res_list = api_client.get(f"/api/v1/books/reviews/{review.id}/comments/")
        assert res_list.status_code == 200
        assert len(res_list.data) == 1
        assert res_list.data[0]["id"] == comment_id

        # 3. Unauthorized deletion attempt by another user
        other_user = User.objects.create_user(username="other", email="other@test.com", password="pw")
        api_client.force_authenticate(user=other_user)
        res_del_unauth = api_client.delete(f"/api/v1/books/reviews/{review.id}/comments/{comment_id}/")
        assert res_del_unauth.status_code == 403

        # 4. Authorized deletion by author (soft delete)
        api_client.force_authenticate(user=liker)
        res_del = api_client.delete(f"/api/v1/books/reviews/{review.id}/comments/{comment_id}/")
        assert res_del.status_code == 204

        comment_db = ReviewComment.objects.get(id=comment_id)
        assert comment_db.deleted_at is not None

        # 5. List comments again -> should not return soft-deleted comment
        res_list2 = api_client.get(f"/api/v1/books/reviews/{review.id}/comments/")
        assert res_list2.status_code == 200
        assert len(res_list2.data) == 0

    def test_blocked_user_cannot_comment_and_comments_hidden(self, api_client, users_fixture):
        blocked = users_fixture["blocked_user"]
        author = users_fixture["author_user"]
        review = users_fixture["review"]

        # Attempt to comment while blocked -> 403
        api_client.force_authenticate(user=blocked)
        res = api_client.post(
            f"/api/v1/books/reviews/{review.id}/comments/",
            {"content": "No debería publicarse."},
            format="json",
        )
        assert res.status_code == 403

        # Create comment in DB manually from blocked user
        comment = ReviewComment.objects.create(
            user=blocked,
            review=review,
            content="Mensaje previo al bloqueo",
        )

        # Viewer is author (who blocked 'blocked'): comment from blocked user should be excluded
        api_client.force_authenticate(user=author)
        res_list = api_client.get(f"/api/v1/books/reviews/{review.id}/comments/")
        assert res_list.status_code == 200
        assert all(c["id"] != comment.id for c in res_list.data)

    def test_review_serializer_counts(self, api_client, users_fixture):
        liker = users_fixture["liker_user"]
        review = users_fixture["review"]

        # Create 1 like and 1 comment
        ReviewLike.objects.create(user=liker, review=review)
        ReviewComment.objects.create(user=liker, review=review, content="Gran libro")

        api_client.force_authenticate(user=liker)
        res = api_client.get(f"/api/v1/books/reviews/{review.id}/")
        assert res.status_code == 200
        assert res.data["likes_count"] == 1
        assert res.data["user_has_liked"] is True
        assert res.data["comments_count"] == 1

        # Check for another unauthenticated or different user
        api_client.logout()
        res_anon = api_client.get(f"/api/v1/books/reviews/{review.id}/")
        assert res_anon.status_code == 200
        assert res_anon.data["likes_count"] == 1
        assert res_anon.data["user_has_liked"] is False
        assert res_anon.data["comments_count"] == 1
