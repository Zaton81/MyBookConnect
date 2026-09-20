import calendar
from datetime import date, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from books.gamification_models import (
    Badge,
    BadgeCategory,
    ChallengeType,
    DailyReadingLog,
    ReadingGoal,
    ReadingStreak,
    UserBadge,
    UserChallenge,
)
from books.models import ReadingStatus, Review, UserBook

DEFAULT_BADGES = [
    {
        'slug': 'raton-de-biblioteca',
        'name': 'Ratón de biblioteca',
        'description': 'Has terminado de leer tu primer libro en la plataforma.',
        'icon': '📚',
        'category': BadgeCategory.READING,
        'points': 10,
    },
    {
        'slug': 'lector-en-marcha',
        'name': 'Lector en marcha',
        'description': 'Has leído 5 libros. ¡Tu estantería empieza a llenarse!',
        'icon': '📖',
        'category': BadgeCategory.READING,
        'points': 20,
    },
    {
        'slug': 'lector-voraz',
        'name': 'Lector voraz',
        'description': '25 libros leídos. Eres un verdadero devorador de historias.',
        'icon': '🦁',
        'category': BadgeCategory.READING,
        'points': 50,
    },
    {
        'slug': 'maestro-de-las-letras',
        'name': 'Maestro de las letras',
        'description': '50 obras completadas. Tu conocimiento literario es legendario.',
        'icon': '👑',
        'category': BadgeCategory.READING,
        'points': 100,
    },
    {
        'slug': 'racha-3-dias',
        'name': 'Chispa lectora',
        'description': 'Has mantenido una racha de lectura durante 3 días consecutivos.',
        'icon': '⚡',
        'category': BadgeCategory.STREAK,
        'points': 15,
    },
    {
        'slug': 'racha-7-dias',
        'name': 'Hábito de fuego',
        'description': '7 días seguidos leyendo. Tu hábito lector arde con fuerza.',
        'icon': '🔥',
        'category': BadgeCategory.STREAK,
        'points': 30,
    },
    {
        'slug': 'racha-30-dias',
        'name': 'Lector imparable',
        'description': '30 días consecutivos de lectura diaria. Disciplina inquebrantable.',
        'icon': '🌟',
        'category': BadgeCategory.STREAK,
        'points': 75,
    },
    {
        'slug': 'primera-resena',
        'name': 'Voz literaria',
        'description': 'Has publicado tu primera reseña crítica para la comunidad.',
        'icon': '✍️',
        'category': BadgeCategory.REVIEWS,
        'points': 15,
    },
    {
        'slug': 'critico-agudo',
        'name': 'Crítico agudo',
        'description': 'Has compartido 5 reseñas detalladas con tus valoraciones.',
        'icon': '⭐',
        'category': BadgeCategory.REVIEWS,
        'points': 35,
    },
    {
        'slug': 'reto-superado',
        'name': 'Conquistador de retos',
        'description': 'Has completado con éxito un reto de lectura comunitario.',
        'icon': '🎯',
        'category': BadgeCategory.CHALLENGES,
        'points': 50,
    },
    {
        'slug': 'espiritu-comunitario',
        'name': 'Espíritu comunitario',
        'description': 'Sigues a 5 lectores o formas parte activa de la red.',
        'icon': '🤝',
        'category': BadgeCategory.COMMUNITY,
        'points': 20,
    },
]


def ensure_default_badges():
    """Siembra las insignias predeterminadas en el catálogo de la plataforma de forma idempotente."""
    for badge_data in DEFAULT_BADGES:
        Badge.objects.get_or_create(
            slug=badge_data['slug'],
            defaults=badge_data,
        )


class GamificationService:
    """
    Servicio central de lógica de gamificación opcional (Fase 54).
    Gestiona rachas, objetivos, insignias y retos.
    """

    @classmethod
    def record_daily_reading(cls, user, pages=0, minutes=0, book=None, target_date=None):
        """
        Registra una sesión o día de lectura, actualiza el log diario y recalcula la racha.
        """
        ensure_default_badges()

        if target_date is None:
            target_date = timezone.now().date()
        elif isinstance(target_date, str):
            target_date = date.fromisoformat(target_date)

        with transaction.atomic():
            log = DailyReadingLog.objects.select_for_update().filter(user=user, date=target_date).first()
            if not log:
                try:
                    with transaction.atomic():
                        log = DailyReadingLog.objects.create(
                            user=user,
                            date=target_date,
                            pages_read=0,
                            minutes_read=0,
                        )
                except IntegrityError:
                    log = DailyReadingLog.objects.select_for_update().get(user=user, date=target_date)

            if pages > 0:
                log.pages_read += pages
            if minutes > 0:
                log.minutes_read += minutes
            if book:
                log.books.add(book)
            log.save()

            # Gestión y recalculo de racha bajo bloqueo exclusivo
            streak = ReadingStreak.objects.select_for_update().filter(user=user).first()
            if not streak:
                try:
                    with transaction.atomic():
                        streak = ReadingStreak.objects.create(
                            user=user,
                            current_streak=0,
                            longest_streak=0,
                            last_reading_date=None,
                        )
                except IntegrityError:
                    streak = ReadingStreak.objects.select_for_update().get(user=user)

            last_date = streak.last_reading_date

            if last_date is None:
                # Primera vez que lee
                streak.current_streak = 1
                streak.longest_streak = max(streak.longest_streak, 1)
                streak.last_reading_date = target_date
            elif last_date == target_date:
                # Ya había registrado hoy, no altera racha
                pass
            elif last_date == target_date - timedelta(days=1):
                # Día inmediatamente consecutivo: incrementa racha
                streak.current_streak += 1
                streak.longest_streak = max(streak.longest_streak, streak.current_streak)
                streak.last_reading_date = target_date
            elif target_date > last_date:
                # Pasó más de un día sin leer: la racha se reinicia a 1
                streak.current_streak = 1
                streak.last_reading_date = target_date

            streak.save()

            # Evaluar retos de tipo páginas leídas
            if pages > 0:
                cls._advance_pages_challenges(user, pages)

            # Evaluar insignias derivadas de rachas
            cls.evaluate_streak_badges(user, streak.current_streak)

            return {
                'log': log,
                'streak': streak,
            }

    @classmethod
    def get_or_calculate_streak(cls, user):
        """
        Retorna la racha del usuario, verificando si se rompió por inactividad.
        Si la última fecha de lectura fue antes de ayer, la racha actual vuelve a 0.
        """
        streak, _ = ReadingStreak.objects.get_or_create(
            user=user,
            defaults={'current_streak': 0, 'longest_streak': 0, 'last_reading_date': None},
        )
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)

        if streak.last_reading_date and streak.last_reading_date < yesterday:
            # Racha rota por inactividad
            if streak.current_streak > 0:
                streak.current_streak = 0
                streak.save(update_fields=['current_streak'])

        return streak

    @classmethod
    def evaluate_reading_goal(cls, user, year=None):
        """
        Calcula el progreso y ritmo del objetivo anual de lectura.
        """
        if year is None:
            year = timezone.now().year

        goal = ReadingGoal.objects.filter(user=user, year=year).first()
        target_books = goal.target_books if goal else 0
        target_pages = goal.target_pages if goal else 0

        # Contar libros leídos en el año especificado
        read_entries = UserBook.objects.filter(
            user=user,
            status=ReadingStatus.READ,
        )
        # Filtramos por finished_at__year o fallback a updated_at__year
        books_read_count = 0
        for entry in read_entries:
            entry_year = entry.finished_at.year if entry.finished_at else entry.updated_at.year
            if entry_year == year:
                books_read_count += 1

        percentage = round((books_read_count / target_books) * 100, 1) if target_books > 0 else 0
        remaining_books = max(0, target_books - books_read_count) if target_books > 0 else 0

        # Cálculo de ritmo / pacing
        today = timezone.now().date()
        if today.year == year and target_books > 0:
            day_of_year = today.timetuple().tm_yday
            total_days = 366 if calendar.isleap(year) else 365
            expected_books = (target_books / total_days) * day_of_year
            diff = books_read_count - expected_books

            if diff >= 1.0:
                pacing_status = 'ahead'
                pacing_text = f'Adelantado por {int(round(diff))} libros'
            elif diff <= -1.0:
                pacing_status = 'behind'
                pacing_text = f'Por detrás por {abs(int(round(diff)))} libros'
            else:
                pacing_status = 'on_track'
                pacing_text = 'Vas al ritmo previsto'
        else:
            pacing_status = 'completed' if books_read_count >= target_books and target_books > 0 else 'inactive'
            pacing_text = 'Meta superada' if books_read_count >= target_books and target_books > 0 else ''

        return {
            'year': year,
            'target_books': target_books,
            'target_pages': target_pages,
            'current_books': books_read_count,
            'remaining_books': remaining_books,
            'percentage': min(100.0, percentage),
            'pacing_status': pacing_status,
            'pacing_text': pacing_text,
            'has_goal': goal is not None,
        }

    @classmethod
    def evaluate_user_badges(cls, user):
        """
        Analiza todos los logros e hitos de la cuenta y desbloquea insignias que correspondan.
        """
        ensure_default_badges()
        newly_awarded = []

        # 1. Libros leídos
        books_read = UserBook.objects.filter(user=user, status=ReadingStatus.READ).count()
        if books_read >= 1:
            if cls._award_badge(user, 'raton-de-biblioteca'):
                newly_awarded.append('raton-de-biblioteca')
        if books_read >= 5:
            if cls._award_badge(user, 'lector-en-marcha'):
                newly_awarded.append('lector-en-marcha')
        if books_read >= 25:
            if cls._award_badge(user, 'lector-voraz'):
                newly_awarded.append('lector-voraz')
        if books_read >= 50:
            if cls._award_badge(user, 'maestro-de-las-letras'):
                newly_awarded.append('maestro-de-las-letras')

        # 2. Reseñas
        reviews_count = Review.objects.filter(user=user, deleted_at__isnull=True).count()
        if reviews_count >= 1:
            if cls._award_badge(user, 'primera-resena'):
                newly_awarded.append('primera-resena')
        if reviews_count >= 5:
            if cls._award_badge(user, 'critico-agudo'):
                newly_awarded.append('critico-agudo')

        # 3. Rachas
        streak = cls.get_or_calculate_streak(user)
        streak_awards = cls.evaluate_streak_badges(user, max(streak.current_streak, streak.longest_streak))
        newly_awarded.extend(streak_awards)

        # 4. Comunidad
        following_count = user.following.count()
        if following_count >= 5:
            if cls._award_badge(user, 'espiritu-comunitario'):
                newly_awarded.append('espiritu-comunitario')

        # 5. Retos completados
        completed_challenges = UserChallenge.objects.filter(user=user, is_completed=True).count()
        if completed_challenges >= 1:
            if cls._award_badge(user, 'reto-superado'):
                newly_awarded.append('reto-superado')

        return newly_awarded

    @classmethod
    def evaluate_streak_badges(cls, user, streak_count):
        """Verifica y otorga insignias de racha."""
        awards = []
        if streak_count >= 3 and cls._award_badge(user, 'racha-3-dias'):
            awards.append('racha-3-dias')
        if streak_count >= 7 and cls._award_badge(user, 'racha-7-dias'):
            awards.append('racha-7-dias')
        if streak_count >= 30 and cls._award_badge(user, 'racha-30-dias'):
            awards.append('racha-30-dias')
        return awards

    @classmethod
    def on_book_finished(cls, user, book):
        """Llamado cuando un usuario marca un libro como LEÍDO."""
        today = timezone.now().date()
        # Registrar lectura del día
        cls.record_daily_reading(user, pages=book.page_count if hasattr(book, 'page_count') and book.page_count else 20, book=book)

        # Evaluar retos activos
        active_challenges = UserChallenge.objects.filter(
            user=user,
            is_completed=False,
            challenge__is_active=True,
            challenge__start_date__lte=today,
            challenge__end_date__gte=today,
        ).select_related('challenge', 'challenge__badge_reward')

        for uc in active_challenges:
            ch = uc.challenge
            matches = False

            if ch.challenge_type == ChallengeType.BOOKS_COUNT:
                matches = True
            elif ch.challenge_type == ChallengeType.GENRE_BOOKS:
                if ch.category and book.categories.filter(id=ch.category.id).exists():
                    matches = True

            if matches:
                uc.current_progress += 1
                if uc.current_progress >= ch.target_count:
                    uc.is_completed = True
                    uc.completed_at = timezone.now()
                    if ch.badge_reward:
                        cls._award_badge(user, ch.badge_reward.slug)
                    cls._award_badge(user, 'reto-superado')
                uc.save()

        # Reevaluar insignias
        cls.evaluate_user_badges(user)

    @classmethod
    def on_review_created(cls, user):
        """Llamado cuando un usuario crea una reseña."""
        today = timezone.now().date()
        active_challenges = UserChallenge.objects.filter(
            user=user,
            is_completed=False,
            challenge__is_active=True,
            challenge__challenge_type=ChallengeType.REVIEWS_COUNT,
            challenge__start_date__lte=today,
            challenge__end_date__gte=today,
        ).select_related('challenge', 'challenge__badge_reward')

        for uc in active_challenges:
            uc.current_progress += 1
            if uc.current_progress >= uc.challenge.target_count:
                uc.is_completed = True
                uc.completed_at = timezone.now()
                if uc.challenge.badge_reward:
                    cls._award_badge(user, uc.challenge.badge_reward.slug)
                cls._award_badge(user, 'reto-superado')
            uc.save()

        cls.evaluate_user_badges(user)

    @classmethod
    def _advance_pages_challenges(cls, user, pages):
        """Avanza los retos de lectura basados en páginas."""
        today = timezone.now().date()
        active_challenges = UserChallenge.objects.filter(
            user=user,
            is_completed=False,
            challenge__is_active=True,
            challenge__challenge_type=ChallengeType.PAGES_COUNT,
            challenge__start_date__lte=today,
            challenge__end_date__gte=today,
        ).select_related('challenge')

        for uc in active_challenges:
            uc.current_progress += pages
            if uc.current_progress >= uc.challenge.target_count:
                uc.is_completed = True
                uc.completed_at = timezone.now()
                if uc.challenge.badge_reward:
                    cls._award_badge(user, uc.challenge.badge_reward.slug)
                cls._award_badge(user, 'reto-superado')
            uc.save()

    @classmethod
    def _award_badge(cls, user, slug):
        """Otorga una insignia de forma idempotente. Retorna True si fue otorgada ahora."""
        badge = Badge.objects.filter(slug=slug).first()
        if not badge:
            return False
        user_badge, created = UserBadge.objects.get_or_create(user=user, badge=badge)
        return created

    @classmethod
    def get_gamification_overview(cls, target_user, requesting_user=None):
        """
        Genera el compendio completo de gamificación del usuario.
        Respeta la bandera opcional `gamification_enabled`.
        """
        ensure_default_badges()

        if not getattr(target_user, 'gamification_enabled', True):
            return {
                'gamification_enabled': False,
                'detail': 'El usuario ha desactivado la gamificación de lectura.',
            }

        streak = cls.get_or_calculate_streak(target_user)
        goal = cls.evaluate_reading_goal(target_user)

        # Insignias del usuario vs catálogo completo
        all_badges = Badge.objects.all().order_by('category', 'points')
        user_badge_map = {
            ub.badge_id: ub.awarded_at
            for ub in UserBadge.objects.filter(user=target_user)
        }

        badges_list = []
        total_points = 0
        for b in all_badges:
            is_unlocked = b.id in user_badge_map
            if is_unlocked:
                total_points += b.points
            badges_list.append({
                'id': b.id,
                'slug': b.slug,
                'name': b.name,
                'description': b.description,
                'icon': b.icon,
                'category': b.category,
                'category_display': b.get_category_display(),
                'points': b.points,
                'unlocked': is_unlocked,
                'awarded_at': user_badge_map.get(b.id),
            })

        # Retos del usuario
        today = timezone.now().date()
        user_challenges = UserChallenge.objects.filter(
            user=target_user,
        ).select_related('challenge', 'challenge__category', 'challenge__badge_reward')

        challenges_list = []
        for uc in user_challenges:
            ch = uc.challenge
            pct = round((uc.current_progress / ch.target_count) * 100, 1) if ch.target_count > 0 else 0
            challenges_list.append({
                'id': ch.id,
                'slug': ch.slug,
                'title': ch.title,
                'description': ch.description,
                'challenge_type': ch.challenge_type,
                'target_count': ch.target_count,
                'current_progress': uc.current_progress,
                'percentage': min(100.0, pct),
                'is_completed': uc.is_completed,
                'completed_at': uc.completed_at,
                'start_date': ch.start_date,
                'end_date': ch.end_date,
                'is_active': ch.is_active and ch.start_date <= today <= ch.end_date,
                'badge_reward': {
                    'name': ch.badge_reward.name,
                    'icon': ch.badge_reward.icon,
                } if ch.badge_reward else None,
            })

        return {
            'gamification_enabled': True,
            'streak': {
                'current_streak': streak.current_streak,
                'longest_streak': streak.longest_streak,
                'last_reading_date': streak.last_reading_date,
                'read_today': streak.last_reading_date == today,
            },
            'goal': goal,
            'badges': {
                'total_badges': len(badges_list),
                'unlocked_count': len(user_badge_map),
                'total_points': total_points,
                'list': badges_list,
            },
            'challenges': challenges_list,
        }
