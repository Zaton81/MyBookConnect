"""
Test suite de validación de modularización y desacoplamiento sin downtime (Fase 2 Post-GA).
Verifica:
1. Registro de apps modulares en INSTALLED_APPS (clubs, gamification, audiobooks, marketplace, authors_portal, ops).
2. Preservación estricta de nombres de tablas PostgreSQL ('books_<modelo>') para cero pérdida de datos.
3. Integridad de re-exports bidireccionales en `books/` para retrocompatibilidad total.
4. Resolución canónica de rutas HTTP de cada dominio desacoplado.
"""
import pytest
from django.apps import apps
from django.conf import settings
from django.urls import resolve, reverse
from rest_framework import status
from rest_framework.test import APIClient

# Model imports from extracted apps
from clubs.models import ReadingClub, ReadingClubBook, ReadingClubDiscussion, ReadingClubMember
from gamification.models import (
    Badge,
    DailyReadingLog,
    ReadingChallenge,
    ReadingGoal,
    ReadingStreak,
    UserBadge,
    UserChallenge,
)
from audiobooks.models import AudiobookTrack, UserAudiobookProgress
from marketplace.models import BookBuyLink, MarketplaceClick, Publisher
from authors_portal.models import (
    AuthorAnnouncement,
    AuthorClaim,
    AuthorEvent,
    AuthorEventAttendee,
    AuthorNewsletter,
    AuthorNewsletterIssue,
    AuthorNewsletterSubscriber,
    AuthorProfile,
)


@pytest.mark.django_db
class TestModularizationArchitecture:
    """Verifica la arquitectura y configuración de aplicaciones extraídas."""

    def test_extracted_apps_in_installed_apps(self):
        installed = settings.INSTALLED_APPS
        expected = [
            'clubs.apps.ClubsConfig',
            'gamification.apps.GamificationConfig',
            'audiobooks.apps.AudiobooksConfig',
            'marketplace.apps.MarketplaceConfig',
            'authors_portal.apps.AuthorsPortalConfig',
            'ops.apps.OpsConfig',
        ]
        for app in expected:
            assert app in installed, f"App {app} debe estar registrada en INSTALLED_APPS"

    def test_database_table_names_preserved(self):
        """Asegura que el contrato de persistencia con PostgreSQL mantenga los nombres de tabla existentes."""
        expected_tables = {
            # Clubs
            ReadingClub: 'books_readingclub',
            ReadingClubMember: 'books_readingclubmember',
            ReadingClubBook: 'books_readingclubbook',
            ReadingClubDiscussion: 'books_readingclubdiscussion',
            # Gamification
            ReadingGoal: 'books_readinggoal',
            ReadingStreak: 'books_readingstreak',
            DailyReadingLog: 'books_dailyreadinglog',
            Badge: 'books_badge',
            UserBadge: 'books_userbadge',
            ReadingChallenge: 'books_readingchallenge',
            UserChallenge: 'books_userchallenge',
            # Audiobooks
            AudiobookTrack: 'books_audiobooktrack',
            UserAudiobookProgress: 'books_useraudiobookprogress',
            # Marketplace
            Publisher: 'books_publisher',
            BookBuyLink: 'books_bookbuylink',
            MarketplaceClick: 'books_marketplaceclick',
            # Authors Portal
            AuthorProfile: 'books_authorprofile',
            AuthorAnnouncement: 'books_authorannouncement',
            AuthorEvent: 'books_authorevent',
            AuthorEventAttendee: 'books_authoreventattendee',
            AuthorNewsletter: 'books_authornewsletter',
            AuthorNewsletterSubscriber: 'books_authornewslettersubscriber',
            AuthorNewsletterIssue: 'books_authornewsletterissue',
            AuthorClaim: 'books_authorclaim',
        }
        for model_cls, table_name in expected_tables.items():
            assert model_cls._meta.db_table == table_name, (
                f"El modelo {model_cls.__name__} debe mantener la tabla {table_name}, "
                f"pero tiene {model_cls._meta.db_table}"
            )

    def test_reexports_backward_compatibility(self):
        """Verifica que los símbolos importados desde `books` sean exactamente las mismas clases."""
        import books.models as bm
        import books.serializers as bs
        import books.views as bv

        # Models
        assert bm.ReadingClub is ReadingClub
        assert bm.ReadingGoal is ReadingGoal
        assert bm.AudiobookTrack is AudiobookTrack
        assert bm.Publisher is Publisher
        assert bm.AuthorProfile is AuthorProfile
        assert bm.AuthorEvent is AuthorEvent
        assert bm.AuthorNewsletter is AuthorNewsletter
        assert bm.AuthorClaim is AuthorClaim

        # Views
        from books.club_views import ReadingClubViewSet as BooksReadingClubViewSet
        from books.gamification_views import GamificationOverviewView as BooksGamificationOverviewView
        from clubs.views import ReadingClubViewSet
        from gamification.views import GamificationOverviewView
        from audiobooks.views import AudiobookCatalogView
        from marketplace.views import BookMarketplaceLinksView
        from authors_portal.views import AuthorProfileMeView

        assert BooksReadingClubViewSet is ReadingClubViewSet
        assert BooksGamificationOverviewView is GamificationOverviewView
        assert bv.AudiobookCatalogView is AudiobookCatalogView
        assert bv.BookMarketplaceLinksView is BookMarketplaceLinksView
        assert bv.AuthorProfileMeView is AuthorProfileMeView

    def test_author_catalog_entity_remains_in_books(self):
        """Invariante de catálogo: Author permanece en `books.models`."""
        from books.models import Author
        assert Author._meta.app_label == 'books'
        assert Author._meta.db_table == 'books_author'

    def test_urls_resolve_to_extracted_views(self):
        """Verifica que los endpoints REST principales enruten a las vistas modularizadas."""
        # Clubs
        match = resolve('/api/v1/clubs/')
        assert 'clubs' in match.func.__module__

        # Gamification
        match = resolve('/api/v1/gamification/overview/')
        assert 'gamification' in match.func.__module__

        # Audiobooks
        match = resolve('/api/v1/audiobooks/catalog/')
        assert 'audiobooks' in match.func.__module__

        # Marketplace
        match = resolve('/api/v1/marketplace/publishers/')
        assert 'marketplace' in match.func.__module__

        # Authors Portal
        match = resolve('/api/v1/authors/me/')
        assert 'authors_portal' in match.func.__module__
