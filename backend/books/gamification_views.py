from django.contrib.auth import get_user_model
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from books.gamification_models import (
    Badge,
    ReadingChallenge,
    ReadingGoal,
    UserBadge,
    UserChallenge,
)
from books.gamification_serializers import (
    BadgeSerializer,
    DailyReadingLogSerializer,
    GamificationPreferenceSerializer,
    ReadingChallengeSerializer,
    ReadingGoalSerializer,
)
from books.models import Book
from books.services.gamification_service import GamificationService

User = get_user_model()


class GamificationOverviewView(APIView):
    """
    Resumen integral de gamificación: objetivo anual, racha actual,
    insignias desbloqueadas y retos activos (Fase 54).
    """
    permission_classes = (permissions.AllowAny,)

    @extend_schema(
        summary="Resumen de gamificación del usuario",
        parameters=[
            OpenApiParameter('user_id', int, required=False, description="ID del usuario a consultar (por defecto el usuario autenticado)"),
        ],
        tags=['Gamification'],
    )
    def get(self, request, *args, **kwargs):
        user_id = request.query_params.get('user_id')
        if user_id:
            try:
                target_user = User.objects.get(id=int(user_id))
            except (ValueError, User.DoesNotExist):
                return Response({'detail': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

            # Privacidad
            is_self = request.user.is_authenticated and request.user.id == target_user.id
            is_staff = request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)

            if not is_self and not is_staff:
                privacy = getattr(target_user, 'privacy_level', 'public')
                if privacy == 'private':
                    return Response({'detail': 'Este perfil es privado.'}, status=status.HTTP_403_FORBIDDEN)
                elif privacy in ('friends', 'friends_only'):
                    if not request.user.is_authenticated:
                        return Response({'detail': 'Inicia sesión para ver este perfil.'}, status=status.HTTP_401_UNAUTHORIZED)
                    is_mutual = target_user.followers.filter(id=request.user.id).exists() and \
                                request.user.followers.filter(id=target_user.id).exists()
                    if not is_mutual:
                        return Response({'detail': 'Solo los amigos mutuos pueden ver este perfil.'}, status=status.HTTP_403_FORBIDDEN)
        else:
            if not request.user.is_authenticated:
                return Response({'detail': 'Se requiere autenticación para consultar el propio resumen.'}, status=status.HTTP_401_UNAUTHORIZED)
            target_user = request.user

        data = GamificationService.get_gamification_overview(target_user, request.user if request.user.is_authenticated else None)
        return Response(data, status=status.HTTP_200_OK)


class ReadingGoalView(APIView):
    """
    Consulta, define o actualiza el objetivo anual de lectura (Fase 54).
    """
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Consultar objetivo de lectura de un año",
        parameters=[
            OpenApiParameter('year', int, required=False, description="Año a consultar (por defecto el actual)"),
        ],
        tags=['Gamification'],
    )
    def get(self, request, *args, **kwargs):
        year_param = request.query_params.get('year')
        year = int(year_param) if year_param and year_param.isdigit() else timezone.now().year
        data = GamificationService.evaluate_reading_goal(request.user, year)
        return Response(data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Crear o actualizar objetivo anual de lectura",
        request=ReadingGoalSerializer,
        responses={200: ReadingGoalSerializer, 201: ReadingGoalSerializer},
        tags=['Gamification'],
    )
    def post(self, request, *args, **kwargs):
        year = request.data.get('year', timezone.now().year)
        goal, created = ReadingGoal.objects.get_or_create(
            user=request.user,
            year=year,
            defaults={'target_books': 12},
        )
        serializer = ReadingGoalSerializer(goal, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        overview = GamificationService.evaluate_reading_goal(request.user, year)
        return Response({
            'goal': serializer.data,
            'overview': overview,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class DailyReadingLogView(APIView):
    """
    Registra una sesión diaria de lectura o marca 'he leído hoy' (Fase 54).
    """
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Registrar progreso diario de lectura para racha",
        request=DailyReadingLogSerializer,
        tags=['Gamification'],
    )
    def post(self, request, *args, **kwargs):
        serializer = DailyReadingLogSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pages = serializer.validated_data.get('pages_read', 0)
        minutes = serializer.validated_data.get('minutes_read', 0)
        book_id = serializer.validated_data.get('book_id')
        target_date = serializer.validated_data.get('date', timezone.now().date())

        book = None
        if book_id:
            try:
                book = Book.objects.get(id=book_id)
            except Book.DoesNotExist:
                pass

        result = GamificationService.record_daily_reading(
            user=request.user,
            pages=pages,
            minutes=minutes,
            book=book,
            target_date=target_date,
        )

        new_badges = GamificationService.evaluate_user_badges(request.user)

        return Response({
            'detail': 'Sesión de lectura registrada correctamente.',
            'date': str(target_date),
            'current_streak': result['streak'].current_streak,
            'longest_streak': result['streak'].longest_streak,
            'new_badges_awarded': new_badges,
        }, status=status.HTTP_200_OK)


class BadgeListView(APIView):
    """
    Catálogo de insignias con estado de desbloqueo del usuario actual (Fase 54).
    """
    permission_classes = (permissions.AllowAny,)

    @extend_schema(
        summary="Listado de insignias y logros de la plataforma",
        responses={200: BadgeSerializer(many=True)},
        tags=['Gamification'],
    )
    def get(self, request, *args, **kwargs):
        from books.services.gamification_service import ensure_default_badges
        ensure_default_badges()

        badges = Badge.objects.all().order_by('category', 'points')
        user_awards = {}
        if request.user.is_authenticated:
            user_awards = {
                ub.badge_id: ub.awarded_at
                for ub in UserBadge.objects.filter(user=request.user)
            }

        data = []
        for b in badges:
            unlocked = b.id in user_awards
            data.append({
                'id': b.id,
                'slug': b.slug,
                'name': b.name,
                'description': b.description,
                'icon': b.icon,
                'category': b.category,
                'category_display': b.get_category_display(),
                'points': b.points,
                'unlocked': unlocked,
                'awarded_at': user_awards.get(b.id),
            })
        return Response(data, status=status.HTTP_200_OK)


class ReadingChallengeListView(APIView):
    """
    Lista los retos de lectura activos y la participación del usuario (Fase 54).
    """
    permission_classes = (permissions.AllowAny,)

    @extend_schema(
        summary="Listado de retos de lectura activos",
        responses={200: ReadingChallengeSerializer(many=True)},
        tags=['Gamification'],
    )
    def get(self, request, *args, **kwargs):
        challenges = ReadingChallenge.objects.filter(is_active=True).order_by('-end_date')
        serializer = ReadingChallengeSerializer(challenges, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class JoinChallengeView(APIView):
    """
    Permite al usuario unirse a un reto de lectura activo (Fase 54).
    """
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Unirse a un reto de lectura",
        tags=['Gamification'],
    )
    def post(self, request, slug, *args, **kwargs):
        try:
            challenge = ReadingChallenge.objects.get(slug=slug, is_active=True)
        except ReadingChallenge.DoesNotExist:
            return Response({'detail': 'Reto no encontrado o no disponible.'}, status=status.HTTP_404_NOT_FOUND)

        user_challenge, created = UserChallenge.objects.get_or_create(
            user=request.user,
            challenge=challenge,
        )

        return Response({
            'detail': '¡Te has unido al reto con éxito!' if created else 'Ya estabas inscrito en este reto.',
            'challenge_title': challenge.title,
            'current_progress': user_challenge.current_progress,
            'target_count': challenge.target_count,
            'is_completed': user_challenge.is_completed,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class GamificationPreferenceView(APIView):
    """
    Permite activar o desactivar la gamificación del perfil (Fase 54).
    """
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Activar o desactivar gamificación para la cuenta",
        request=GamificationPreferenceSerializer,
        tags=['Gamification'],
    )
    def patch(self, request, *args, **kwargs):
        serializer = GamificationPreferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        enabled = serializer.validated_data['gamification_enabled']
        request.user.gamification_enabled = enabled
        request.user.save(update_fields=['gamification_enabled'])

        return Response({
            'detail': 'Preferencia de gamificación actualizada correctamente.',
            'gamification_enabled': request.user.gamification_enabled,
        }, status=status.HTTP_200_OK)
