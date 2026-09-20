import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from books.models import Author, Book, Review, ReviewComment
from messages_app.models import Conversation, Message
from mybookconnect.html_sanitizer import sanitize_html, sanitize_plain_text

User = get_user_model()


# ---------------------------------------------------------------------------
# Unit tests for HTML and plain text sanitizers
# ---------------------------------------------------------------------------
class TestHtmlSanitizerUnit:
    def test_sanitize_html_removes_dangerous_tags_and_scripts(self):
        malicious_input = (
            "<p>Hola mundo</p>"
            "<script>alert('XSS')</script>"
            "<iframe src='https://evil.com'></iframe>"
            "<style>body { display: none; }</style>"
        )
        cleaned = sanitize_html(malicious_input)
        assert "<script>" not in cleaned
        assert "alert('XSS')" not in cleaned
        assert "<iframe>" not in cleaned
        assert "<style>" not in cleaned
        assert "<p>Hola mundo</p>" in cleaned

    def test_sanitize_html_removes_event_handlers(self):
        payload = (
            '<a href="https://example.com" onclick="stealCookies()">Enlace seguro</a>'
            '<span onmouseover="exploit()">Pasa el ratón</span>'
            '<img src="invalid.jpg" onerror="alert(1)">'
        )
        cleaned = sanitize_html(payload)
        assert "onclick" not in cleaned
        assert "stealCookies" not in cleaned
        assert "onmouseover" not in cleaned
        assert "onerror" not in cleaned
        assert "alert(1)" not in cleaned
        assert "Enlace seguro" in cleaned
        assert "Pasa el ratón" in cleaned

    def test_sanitize_html_preserves_safe_rich_tags(self):
        rich_content = (
            "<h1>Título</h1>"
            "<p>Este es un <strong>texto en negrita</strong> y <em>cursiva</em> con <u>subrayado</u>.</p>"
            "<blockquote>Cita célebre</blockquote>"
            "<ul><li>Elemento 1</li><li>Elemento 2</li></ul>"
            "<pre><code>print('hola')</code></pre>"
        )
        cleaned = sanitize_html(rich_content)
        assert "<h1>Título</h1>" in cleaned
        assert "<strong>texto en negrita</strong>" in cleaned
        assert "<em>cursiva</em>" in cleaned
        assert "<u>subrayado</u>" in cleaned
        assert "<blockquote>Cita célebre</blockquote>" in cleaned
        assert "<ul><li>Elemento 1</li><li>Elemento 2</li></ul>" in cleaned
        assert "<pre><code>print('hola')</code></pre>" in cleaned

    def test_sanitize_html_enforces_safe_link_attributes(self):
        link_html = '<a href="https://books.example.com" target="_blank">Visitar sitio</a>'
        cleaned = sanitize_html(link_html)
        assert 'href="https://books.example.com"' in cleaned
        assert 'rel="noopener noreferrer nofollow"' in cleaned

    def test_sanitize_html_neutralizes_javascript_uris(self):
        bad_link = '<a href="javascript:alert(1)">Haz clic aquí</a>'
        cleaned = sanitize_html(bad_link)
        assert "javascript:" not in cleaned
        assert "alert(1)" not in cleaned

    def test_sanitize_plain_text_strips_all_tags(self):
        raw = "<p>Hola <b>amigos</b> lectores, <script>alert('xss')</script>bienvenidos.</p>"
        cleaned = sanitize_plain_text(raw)
        assert "<" not in cleaned
        assert ">" not in cleaned
        assert "alert" not in cleaned
        assert cleaned == "Hola amigos lectores, bienvenidos."


# ---------------------------------------------------------------------------
# Integration tests across UGC surfaces
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestUgcSurfacesSecurity:
    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username="booklover",
            email="lover@example.com",
            password="StrongPassword123!",
        )

    @pytest.fixture
    def client(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    @pytest.fixture
    def book(self):
        author = Author.objects.create(name="Ursula K. Le Guin")
        return Book.objects.create(
            title="Los desposeídos",
            author=author,
            isbn="9788445070260",
        )

    def test_profile_bio_and_fields_sanitization(self, client, user):
        """Surface 1: Profiles - Bio sanitizes rich HTML, text fields strip tags completely."""
        update_data = {
            "bio": "<p>Amante de la ciencia ficción.</p><script>alert('hack')</script><iframe src='evil.com'></iframe>",
            "location": "<b>Madrid</b><script>xss()</script>",
            "first_name": "Ana <u>María</u>",
            "last_name": "García <i>López</i>",
        }
        res = client.patch("/api/v1/auth/profile/update/", update_data, format="json")
        assert res.status_code == 200, res.data

        user.refresh_from_db()
        assert "<script>" not in user.bio
        assert "alert('hack')" not in user.bio
        assert "evil.com" not in user.bio
        assert "<p>Amante de la ciencia ficción.</p>" in user.bio
        assert user.location == "Madrid"
        assert user.first_name == "Ana María"
        assert user.last_name == "García López"

    def test_book_review_sanitization(self, client, user, book):
        """Surface 2: Reviews - Title stripped to plain text, text sanitizes rich HTML."""
        review_data = {
            "book_id": book.id,
            "rating": 9,
            "title": "<h3>Magnífica novela</h3><script>alert(1)</script>",
            "text": "<p>Una utopía ambigua inolvidable.</p><script>stealToken()</script><img src=x onerror=alert(2)>",
        }
        res = client.post("/api/v1/reviews/", review_data, format="json")
        assert res.status_code == 201, res.data

        review = Review.objects.get(id=res.data["id"])
        assert review.title == "Magnífica novela"
        assert "<script>" not in review.text
        assert "stealToken" not in review.text
        assert "onerror" not in review.text
        assert "<p>Una utopía ambigua inolvidable.</p>" in review.text

    def test_review_comment_sanitization(self, client, user, book):
        """Surface 3: Comments - Content sanitized to clean plain text (no scripts or HTML injection)."""
        review = Review.objects.create(
            user=user,
            book=book,
            rating=10,
            title="Excelente",
            text="Un clásico absoluto.",
        )
        comment_payload = {
            "content": "<p>Totalmente de acuerdo.<script>alert('pwn')</script></p>"
        }
        res = client.post(f"/api/v1/reviews/{review.id}/comments/", comment_payload, format="json")
        assert res.status_code == 201, res.data

        comment = ReviewComment.objects.get(id=res.data["id"])
        assert "<script>" not in comment.content
        assert "alert('pwn')" not in comment.content
        assert comment.content == "Totalmente de acuerdo."

    def test_chat_message_sanitization(self, client, user):
        """Surface 4: Chat / Messages - Plain text sanitized, removing dangerous injected tags."""
        other_user = User.objects.create_user(
            username="reader_friend",
            email="friend@example.com",
            password="StrongPassword123!",
        )
        user.following.add(other_user)
        conv, _ = Conversation.get_or_create_direct(user, other_user)

        message_payload = {
            "conversation": conv.id,
            "text": "Hola! Mira esto: <script>document.location='http://evil.com'</script><b>genial</b>",
        }
        res = client.post("/api/v1/messages/", message_payload, format="json")
        assert res.status_code == 201, res.data

        msg = Message.objects.get(id=res.data["id"])
        assert "<script>" not in msg.text
        assert "evil.com" not in msg.text
        assert "<b>" not in msg.text
        assert msg.text == "Hola! Mira esto: genial"
