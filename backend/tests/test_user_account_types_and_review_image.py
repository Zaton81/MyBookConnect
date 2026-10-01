import io
import pytest
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient
from users.models import User, AccountType
from books.models import Book, Author, Review, AuthorProfile

pytestmark = pytest.mark.django_db


def create_test_image():
    file = io.BytesIO()
    image = Image.new('RGB', (100, 100), color='blue')
    image.save(file, 'jpeg')
    file.seek(0)
    return SimpleUploadedFile('test_photo.jpg', file.read(), content_type='image/jpeg')


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def test_book():
    author = Author.objects.create(name="Gabriel García Márquez")
    return Book.objects.create(
        title="Cien años de soledad",
        author=author,
        isbn="9780307474728"
    )


from django.test import override_settings

class TestUserAccountTypes:
    def test_register_as_reader(self, api_client):
        with override_settings(PUBLIC_REGISTRATION_ENABLED=True, REQUIRE_BETA_INVITATION=False):
            url = "/api/v1/users/register/"
            payload = {
                "username": "lector_dev",
                "email": "lector@example.com",
                "password": "ComplexPassword2026!",
                "password2": "ComplexPassword2026!",
                "account_type": AccountType.READER
            }
            response = api_client.post(url, payload, format="json")
            assert response.status_code == status.HTTP_201_CREATED
            user = User.objects.get(username="lector_dev")
            assert user.account_type == AccountType.READER
            assert user.is_author is False
            assert not hasattr(user, 'author_profile')

    def test_register_as_author(self, api_client):
        with override_settings(PUBLIC_REGISTRATION_ENABLED=True, REQUIRE_BETA_INVITATION=False):
            url = "/api/v1/users/register/"
            payload = {
                "username": "escritor_dev",
                "email": "escritor@example.com",
                "password": "ComplexPassword2026!",
                "password2": "ComplexPassword2026!",
                "account_type": AccountType.AUTHOR
            }
            response = api_client.post(url, payload, format="json")
            assert response.status_code == status.HTTP_201_CREATED
            user = User.objects.get(username="escritor_dev")
            assert user.account_type == AccountType.AUTHOR
            assert user.is_author is True
            assert AuthorProfile.objects.filter(user=user).exists()

    def test_register_as_both(self, api_client):
        with override_settings(PUBLIC_REGISTRATION_ENABLED=True, REQUIRE_BETA_INVITATION=False):
            url = "/api/v1/users/register/"
            payload = {
                "username": "lector_y_escritor",
                "email": "both@example.com",
                "password": "ComplexPassword2026!",
                "password2": "ComplexPassword2026!",
                "account_type": AccountType.BOTH
            }
            response = api_client.post(url, payload, format="json")
            assert response.status_code == status.HTTP_201_CREATED
            user = User.objects.get(username="lector_y_escritor")
            assert user.account_type == AccountType.BOTH
            assert user.is_author is True
            assert AuthorProfile.objects.filter(user=user).exists()

    def test_update_profile_account_type_to_author(self, api_client):
        user = User.objects.create_user(
            username="lector_transicion",
            email="trans@example.com",
            password="ComplexPassword2026!",
            account_type=AccountType.READER
        )
        api_client.force_authenticate(user=user)

        url = "/api/v1/users/profile/update/"
        response = api_client.patch(url, {"account_type": AccountType.AUTHOR}, format="json")
        assert response.status_code == status.HTTP_200_OK

        user.refresh_from_db()
        assert user.account_type == AccountType.AUTHOR
        assert user.is_author is True
        assert AuthorProfile.objects.filter(user=user).exists()


class TestReviewImageUpload:
    def test_create_review_with_image_multipart(self, api_client, test_book):
        user = User.objects.create_user(
            username="resenador_foto",
            email="resena_foto@example.com",
            password="Password123!"
        )
        api_client.force_authenticate(user=user)

        image_file = create_test_image()
        url = "/api/v1/reviews/"
        payload = {
            "book_id": test_book.id,
            "book": test_book.id,
            "rating": 5,
            "title": "Edición bellísima con foto",
            "text": "Adjunto una foto de la portada y mis anotaciones con **negrita**.",
            "image": image_file
        }
        response = api_client.post(url, payload, format="multipart")
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["rating"] == 5
        assert data["title"] == "Edición bellísima con foto"
        assert data["image"] is not None
        assert "test_photo" in data["image"]

        review = Review.objects.get(id=data["id"])
        assert review.image is not None
        assert "reviews/" in review.image.name
