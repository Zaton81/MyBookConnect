import logging

logger = logging.getLogger(__name__)


class AuthorService:
    @classmethod
    def get_or_create_profile(cls, user):
        """Obtiene o crea un perfil de autor para el usuario indicado."""
        from authors_portal.models import AuthorProfile
        profile, _ = AuthorProfile.objects.get_or_create(user=user)
        return profile

    @classmethod
    def claim_author(cls, user, author_id: int, pen_name: str = "", verification_notes: str = ""):
        """
        Inicia el proceso de reclamación y vinculación de un autor del catálogo
        con la cuenta del usuario.
        """
        from books.models import Author
        author = Author.objects.filter(id=author_id).first()
        if not author:
            raise ValueError(f"El autor #{author_id} no existe en el catálogo.")

        profile = cls.get_or_create_profile(user)
        profile.author = author
        if pen_name:
            profile.pen_name = pen_name
        elif not profile.pen_name:
            profile.pen_name = author.name

        profile.verification_notes = verification_notes
        if user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'EDITOR'):
            profile.is_verified = True
        profile.save()
        logger.info(f"Usuario {user.username} reclamó autor #{author_id} ({author.name})")
        return profile

    @classmethod
    def get_author_dashboard_metrics(cls, author_profile) -> dict:
        """
        Genera el resumen de métricas e impacto de las obras del autor para su panel privado.
        """
        from django.db.models import Avg, Count

        from books.models import Book, Review, UserBook

        author = author_profile.author
        if not author:
            return {
                "author_id": None,
                "author_name": author_profile.pen_name or author_profile.user.username,
                "is_verified": author_profile.is_verified,
                "books_count": 0,
                "readers_total": 0,
                "readers_by_status": {"want_to_read": 0, "reading": 0, "read": 0, "abandoned": 0},
                "average_rating": None,
                "recent_reviews": [],
            }

        books = Book.objects.filter(author=author)
        book_ids = list(books.values_list('id', flat=True))
        books_count = len(book_ids)

        # Lectores totales y por estado
        user_books = UserBook.objects.filter(book_id__in=book_ids)
        readers_total = user_books.count()

        status_counts = user_books.values('status').annotate(total=Count('id'))
        readers_by_status = {"want_to_read": 0, "reading": 0, "read": 0, "abandoned": 0}
        for sc in status_counts:
            st = sc.get('status')
            if st in readers_by_status:
                readers_by_status[st] = sc.get('total', 0)

        # Valoración media agregada de todas las obras del autor
        avg_rating = Review.objects.filter(
            book_id__in=book_ids,
            rating__isnull=False,
            deleted_at__isnull=True,
            is_moderated=False,
        ).aggregate(avg=Avg('rating'))['avg']
        if avg_rating is not None:
            avg_rating = round(avg_rating, 2)

        # Últimas reseñas sobre libros del autor
        recent_reviews_qs = (
            Review.objects.filter(
                book_id__in=book_ids,
                deleted_at__isnull=True,
                is_moderated=False,
            )
            .select_related('user', 'book')
            .order_by('-created_at')[:10]
        )
        recent_reviews = [
            {
                "id": rev.id,
                "book_id": rev.book_id,
                "book_title": rev.book.title,
                "username": rev.user.username,
                "rating": rev.rating,
                "title": rev.title or "",
                "content": rev.text[:200] if rev.text else "",
                "created_at": rev.created_at.isoformat() if rev.created_at else None,
            }
            for rev in recent_reviews_qs
        ]

        return {
            "author_id": author.id,
            "author_name": author.name,
            "pen_name": author_profile.pen_name or author.name,
            "is_verified": author_profile.is_verified,
            "books_count": books_count,
            "readers_total": readers_total,
            "readers_by_status": readers_by_status,
            "average_rating": avg_rating,
            "recent_reviews": recent_reviews,
        }

    @classmethod
    def create_announcement(
        cls,
        author_profile,
        title: str,
        content: str,
        book_id: int | None = None,
        is_pinned: bool = False,
        publication_type: str = "ANNOUNCEMENT",
        excerpt: str = "",
        has_spoilers: bool = False,
        spoiler_warning: str = "",
        estimated_reading_time: int | None = None,
        is_draft: bool = False,
        author_id: int | None = None,
        is_paid: bool = False,
        price: float | None = None,
    ):
        """Crea una publicación oficial o comunicado emitido por el autor."""
        from django.utils import timezone

        from authors_portal.models import AuthorAnnouncement
        from books.models import Author, Book

        book = Book.objects.filter(id=book_id).first() if book_id else None
        author = Author.objects.filter(id=author_id).first() if author_id else (author_profile.author if author_profile else None)

        announcement = AuthorAnnouncement(
            author_profile=author_profile,
            author=author,
            book=book,
            title=title.strip(),
            content=content.strip(),
            excerpt=excerpt.strip(),
            publication_type=publication_type,
            has_spoilers=has_spoilers,
            spoiler_warning=spoiler_warning.strip(),
            is_pinned=is_pinned,
            is_draft=is_draft,
            is_paid=is_paid,
            price=price,
            created_at=timezone.now(),
        )
        if estimated_reading_time:
            announcement.estimated_reading_time = estimated_reading_time
        announcement.save()
        return announcement

    @classmethod
    def get_announcements_for_author(
        cls,
        author_id: int,
        include_drafts: bool = False,
        publication_type: str | None = None,
        include_moderated: bool = False,
    ):
        """Obtiene las publicaciones asociadas a un autor del catálogo."""
        from django.db.models import Q

        from authors_portal.models import AuthorAnnouncement
        qs = AuthorAnnouncement.objects.filter(
            Q(author_id=author_id) | Q(author_profile__author_id=author_id)
        ).select_related('author_profile', 'author', 'book')
        if not include_moderated:
            qs = qs.filter(is_moderated=False)
        if not include_drafts:
            qs = qs.filter(is_draft=False)
        if publication_type:
            qs = qs.filter(publication_type=publication_type)
        return qs.order_by('-is_pinned', '-created_at')
