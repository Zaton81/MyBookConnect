from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from books.gamification_models import (
    Badge,
    ChallengeType,
    DailyReadingLog,
    ReadingChallenge,
    ReadingGoal,
    ReadingStreak,
    UserBadge,
    UserChallenge,
)
from books.models import Author, Book, Category, ReadingStatus, Review, UserBook
from books.services.gamification_service import GamificationService, ensure_default_badges

User = get_user_model()


class Phase54GamificationTests(APITestCase):
    """
    Suite de pruebas automatizadas para la Fase 54 — Gamificación opcional.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='lector1',
            email='lector1@example.com',
            password='Password123!',
        )
        self.other_user = User.objects.create_user(
            username='lector2',
            email='lector2@example.com',
            password='Password123!',
        )
        self.author = Author.objects.create(name='Ursula K. Le Guin')
        self.category_scifi = Category.objects.create(name='Ciencia Ficción', slug='ciencia-ficcion')
        self.book1 = Book.objects.create(title='Los desposeídos', author=self.author)
        self.book1.categories.add(self.category_scifi)
        self.book2 = Book.objects.create(title='La mano izquierda de la oscuridad', author=self.author)
        self.book2.categories.add(self.category_scifi)

        ensure_default_badges()

    def test_ensure_default_badges_is_idempotent(self):
        """Verifica que las insignias predeterminadas se crean y no se duplican."""
        initial_count = Badge.objects.count()
        self.assertGreaterEqual(initial_count, 10)
        # Segunda llamada no debe duplicar
        ensure_default_badges()
        self.assertEqual(Badge.objects.count(), initial_count)

    def test_reading_goal_creation_and_pacing(self):
        """Prueba creación de objetivo anual y cálculo de ritmo."""
        current_year = timezone.now().year
        # Crear objetivo de 10 libros
        ReadingGoal.objects.create(
            user=self.user,
            year=current_year,
            target_books=10,
        )

        # Sin libros leídos
        goal_data = GamificationService.evaluate_reading_goal(self.user, current_year)
        self.assertEqual(goal_data['target_books'], 10)
        self.assertEqual(goal_data['current_books'], 0)
        self.assertEqual(goal_data['percentage'], 0.0)
        self.assertEqual(goal_data['remaining_books'], 10)
        self.assertTrue(goal_data['has_goal'])

        # Marcar 2 libros como leídos en este año
        UserBook.objects.create(
            user=self.user,
            book=self.book1,
            status=ReadingStatus.READ,
            finished_at=date(current_year, 1, 15),
        )
        UserBook.objects.create(
            user=self.user,
            book=self.book2,
            status=ReadingStatus.READ,
            finished_at=date(current_year, 2, 10),
        )

        updated_goal = GamificationService.evaluate_reading_goal(self.user, current_year)
        self.assertEqual(updated_goal['current_books'], 2)
        self.assertEqual(updated_goal['percentage'], 20.0)
        self.assertEqual(updated_goal['remaining_books'], 8)

    def test_daily_reading_log_and_streak_progression(self):
        """Prueba registro diario y avance consecutivo de racha."""
        base_date = date(2026, 5, 1)

        # Día 1
        res1 = GamificationService.record_daily_reading(
            user=self.user,
            pages=30,
            minutes=25,
            book=self.book1,
            target_date=base_date,
        )
        self.assertEqual(res1['streak'].current_streak, 1)
        self.assertEqual(res1['streak'].longest_streak, 1)
        self.assertEqual(DailyReadingLog.objects.filter(user=self.user).count(), 1)

        # Mismo día 1 otra sesión (idempotente para la racha, acumulativo para el log)
        res1_again = GamificationService.record_daily_reading(
            user=self.user,
            pages=20,
            minutes=15,
            book=self.book1,
            target_date=base_date,
        )
        self.assertEqual(res1_again['streak'].current_streak, 1)
        log1 = DailyReadingLog.objects.get(user=self.user, date=base_date)
        self.assertEqual(log1.pages_read, 50)
        self.assertEqual(log1.minutes_read, 40)

        # Día 2 consecutivo
        res2 = GamificationService.record_daily_reading(
            user=self.user,
            pages=40,
            target_date=base_date + timedelta(days=1),
        )
        self.assertEqual(res2['streak'].current_streak, 2)
        self.assertEqual(res2['streak'].longest_streak, 2)

        # Día 3 consecutivo
        res3 = GamificationService.record_daily_reading(
            user=self.user,
            pages=15,
            target_date=base_date + timedelta(days=2),
        )
        self.assertEqual(res3['streak'].current_streak, 3)
        self.assertEqual(res3['streak'].longest_streak, 3)

        # Salto de 3 días (racha rota, reinicia a 1)
        res4 = GamificationService.record_daily_reading(
            user=self.user,
            pages=20,
            target_date=base_date + timedelta(days=6),
        )
        self.assertEqual(res4['streak'].current_streak, 1)
        self.assertEqual(res4['streak'].longest_streak, 3)  # Récord preservado

    def test_streak_broken_by_inactivity(self):
        """Verifica que get_or_calculate_streak pone a 0 la racha si no se ha leído desde antes de ayer."""
        three_days_ago = timezone.now().date() - timedelta(days=3)
        ReadingStreak.objects.create(
            user=self.user,
            current_streak=5,
            longest_streak=5,
            last_reading_date=three_days_ago,
        )
        evaluated = GamificationService.get_or_calculate_streak(self.user)
        self.assertEqual(evaluated.current_streak, 0)
        self.assertEqual(evaluated.longest_streak, 5)

    def test_badge_unlocking_triggers(self):
        """Verifica desbloqueo automático de insignias al alcanzar hitos."""
        # 1. Primer libro leído -> ratón de biblioteca
        UserBook.objects.create(
            user=self.user,
            book=self.book1,
            status=ReadingStatus.READ,
        )
        awarded = GamificationService.evaluate_user_badges(self.user)
        self.assertIn('raton-de-biblioteca', awarded)
        self.assertTrue(UserBadge.objects.filter(user=self.user, badge__slug='raton-de-biblioteca').exists())

        # 2. Primera reseña -> voz literaria
        Review.objects.create(
            user=self.user,
            book=self.book1,
            rating=5,
            text='Obra maestra imprescindible.',
        )
        awarded_review = GamificationService.evaluate_user_badges(self.user)
        self.assertIn('primera-resena', awarded_review)
        self.assertTrue(UserBadge.objects.filter(user=self.user, badge__slug='primera-resena').exists())

    def test_reading_challenge_lifecycle(self):
        """Prueba ciclo completo de un reto: creación, inscripción, avance y premio."""
        today = timezone.now().date()
        badge_reward = Badge.objects.get(slug='reto-superado')

        challenge = ReadingChallenge.objects.create(
            slug='reto-otono-2026',
            title='Reto de Otoño: 2 Libros',
            description='Lee 2 obras este mes.',
            challenge_type=ChallengeType.BOOKS_COUNT,
            target_count=2,
            start_date=today - timedelta(days=5),
            end_date=today + timedelta(days=25),
            badge_reward=badge_reward,
            is_active=True,
        )

        # Usuario se une
        uc = UserChallenge.objects.create(user=self.user, challenge=challenge)
        self.assertEqual(uc.current_progress, 0)
        self.assertFalse(uc.is_completed)

        # Lee primer libro
        GamificationService.on_book_finished(self.user, self.book1)
        uc.refresh_from_db()
        self.assertEqual(uc.current_progress, 1)
        self.assertFalse(uc.is_completed)

        # Lee segundo libro (completa reto)
        GamificationService.on_book_finished(self.user, self.book2)
        uc.refresh_from_db()
        self.assertEqual(uc.current_progress, 2)
        self.assertTrue(uc.is_completed)
        self.assertIsNotNone(uc.completed_at)

        # Insignia del reto otorgada
        self.assertTrue(UserBadge.objects.filter(user=self.user, badge=badge_reward).exists())

    def test_gamification_disabled_opt_out(self):
        """Prueba que un usuario puede desactivar opcionalmente la gamificación."""
        self.user.gamification_enabled = False
        self.user.save()

        overview = GamificationService.get_gamification_overview(self.user)
        self.assertFalse(overview['gamification_enabled'])
        self.assertIn('desactivado', overview['detail'])

    def test_api_gamification_endpoints(self):
        """Prueba integral de los endpoints REST de gamificación."""
        self.client.force_authenticate(user=self.user)

        # 1. Definir objetivo anual
        current_year = timezone.now().year
        res_goal = self.client.post('/api/v1/gamification/goals/', {
            'year': current_year,
            'target_books': 15,
        })
        self.assertIn(res_goal.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        self.assertEqual(res_goal.data['goal']['target_books'], 15)

        # 2. Registrar lectura diaria ('he leído hoy')
        res_log = self.client.post('/api/v1/gamification/log/', {
            'pages_read': 25,
            'minutes_read': 30,
            'book_id': self.book1.id,
        })
        self.assertEqual(res_log.status_code, status.HTTP_200_OK)
        self.assertEqual(res_log.data['current_streak'], 1)

        # 3. Consultar listado de insignias
        res_badges = self.client.get('/api/v1/gamification/badges/')
        self.assertEqual(res_badges.status_code, status.HTTP_200_OK)
        self.assertGreater(len(res_badges.data), 0)

        # 4. Unirse a un reto por API
        today = timezone.now().date()
        challenge = ReadingChallenge.objects.create(
            slug='reto-api-test',
            title='Reto API',
            description='Prueba API',
            challenge_type=ChallengeType.BOOKS_COUNT,
            target_count=3,
            start_date=today,
            end_date=today + timedelta(days=10),
            is_active=True,
        )
        res_join = self.client.post(f'/api/v1/gamification/challenges/{challenge.slug}/join/')
        self.assertEqual(res_join.status_code, status.HTTP_201_CREATED)

        # 5. Obtener overview completo
        res_overview = self.client.get('/api/v1/gamification/overview/')
        self.assertEqual(res_overview.status_code, status.HTTP_200_OK)
        self.assertTrue(res_overview.data['gamification_enabled'])
        self.assertEqual(res_overview.data['streak']['current_streak'], 1)
        self.assertEqual(res_overview.data['goal']['target_books'], 15)

        # 6. Cambiar preferencia de gamificación (opt-out)
        res_pref = self.client.patch('/api/v1/gamification/preferences/', {
            'gamification_enabled': False,
        })
        self.assertEqual(res_pref.status_code, status.HTTP_200_OK)
        self.assertFalse(res_pref.data['gamification_enabled'])

        # Ahora el overview refleja gamification_enabled=False
        res_overview_after = self.client.get('/api/v1/gamification/overview/')
        self.assertFalse(res_overview_after.data['gamification_enabled'])
