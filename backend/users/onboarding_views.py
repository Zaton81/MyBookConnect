"""
Vistas para la experiencia de bienvenida y Onboarding del nuevo lector (Fase 19).
Permite configurar géneros favoritos, añadir primeras lecturas o importar biblioteca,
y recibir la primera recomendación instantánea sin fricción ni bloqueos obligatorios.
"""

import logging

from django.db import transaction
from django.db.models import Count
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from books.cache_utils import safe_cache_delete, user_profile_key
from books.media_utils import build_media_url
from books.models import Book, Category, ReadingStatus, UserBook
from books.services import recommendation_service
from mybookconnect.html_sanitizer import sanitize_plain_text

logger = logging.getLogger('mybookconnect.onboarding')


class OnboardingStatusView(APIView):
    """
    Endpoint para consultar el estado del onboarding y las opciones de personalización inicial.
    GET /api/v1/users/onboarding/
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Estado y opciones de Onboarding para el nuevo lector",
        description="Devuelve el estado de completado, categorías literarias disponibles y libros populares sugeridos.",
        responses={
            200: inline_serializer(
                name='OnboardingStatusResponse',
                fields={
                    'onboarding_completed': serializers.BooleanField(),
                    'favorite_categories': serializers.ListField(child=serializers.DictField()),
                    'available_categories': serializers.ListField(child=serializers.DictField()),
                    'suggested_books': serializers.ListField(child=serializers.DictField()),
                },
            ),
        },
        tags=['Onboarding'],
    )
    def get(self, request):
        user = request.user

        # 1. Categorías disponibles con recuento de libros
        categories = (
            Category.objects.annotate(books_count=Count('books'))
            .filter(books_count__gt=0)
            .order_by('-books_count', 'name')[:24]
        )
        available_categories = [
            {'id': c.id, 'name': c.name, 'slug': c.slug, 'books_count': c.books_count}
            for c in categories
        ]

        # 2. Categorías ya marcadas como favoritas por el usuario
        user_favs = user.favorite_categories.all()
        favorite_categories = [
            {'id': c.id, 'name': c.name, 'slug': c.slug}
            for c in user_favs
        ]

        # 3. Libros sugeridos para el arranque en frío (alta valoración o populares)
        suggested_qs = (
            Book.objects.filter(average_rating__gte=3.5)
            .select_related('author')
            .prefetch_related('categories')
            .order_by('-average_rating', '-created_at')[:12]
        )
        suggested_books = []
        for b in suggested_qs:
            suggested_books.append({
                'id': b.id,
                'title': b.title,
                'author_name': b.author.name if b.author else 'Autor desconocido',
                'cover': build_media_url(b.cover.name if b.cover else None, request=request),
                'average_rating': b.average_rating,
                'category_names': [c.name for c in b.categories.all()[:2]],
            })

        return Response({
            'onboarding_completed': user.onboarding_completed,
            'favorite_categories': favorite_categories,
            'available_categories': available_categories,
            'suggested_books': suggested_books,
        })

    def post(self, request):
        return OnboardingCompleteView().post(request)


class OnboardingCompleteView(APIView):
    """
    Endpoint para completar el flujo de Onboarding.
    Guarda los géneros favoritos, añade primeros libros a la biblioteca, actualiza bio opcional
    y genera la primera recomendación en tiempo real.
    POST /api/v1/users/onboarding/
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Completar Onboarding y generar primera recomendación",
        description="Asocia géneros literarios favoritos, añade lecturas iniciales y devuelve la primera recomendación.",
        request=inline_serializer(
            name='OnboardingCompleteRequest',
            fields={
                'category_ids': serializers.ListField(child=serializers.IntegerField(), required=False),
                'books': serializers.ListField(child=serializers.DictField(), required=False),
                'bio': serializers.CharField(required=False, allow_blank=True),
            },
        ),
        responses={
            200: inline_serializer(
                name='OnboardingCompleteResponse',
                fields={
                    'success': serializers.BooleanField(),
                    'detail': serializers.CharField(),
                    'first_recommendation': serializers.DictField(allow_null=True),
                },
            ),
        },
        tags=['Onboarding'],
    )
    def post(self, request):
        user = request.user
        category_ids = request.data.get('category_ids', [])
        books_data = request.data.get('books', [])
        bio = request.data.get('bio', '')

        with transaction.atomic():
            # 1. Asociar categorías favoritas
            if category_ids:
                valid_cats = Category.objects.filter(id__in=category_ids)
                user.favorite_categories.set(valid_cats)

            # 2. Actualizar biografía inicial si se proporcionó
            if bio and isinstance(bio, str):
                cleaned_bio = sanitize_plain_text(bio).strip()
                if cleaned_bio:
                    user.bio = cleaned_bio[:500]

            # 3. Añadir primeros libros a la biblioteca (UserBook)
            for item in books_data:
                if not isinstance(item, dict):
                    continue
                book_id = item.get('book_id') or item.get('id')
                if not book_id:
                    continue

                raw_status = str(item.get('status', ReadingStatus.WANT_TO_READ)).lower().strip()
                if raw_status not in ReadingStatus.values:
                    raw_status = ReadingStatus.WANT_TO_READ

                book = Book.objects.filter(id=book_id).first()
                if book:
                    user_book, created = UserBook.objects.get_or_create(
                        user=user,
                        book=book,
                        defaults={
                            'status': raw_status,
                            'is_read': (raw_status == ReadingStatus.READ),
                            'rating': item.get('rating'),
                        }
                    )
                    if not created and item.get('status'):
                        user_book.status = raw_status
                        user_book.is_read = (raw_status == ReadingStatus.READ)
                        if item.get('rating'):
                            user_book.rating = item.get('rating')
                        user_book.save()

            # 4. Marcar onboarding como finalizado
            user.onboarding_completed = True
            user.save(update_fields=['bio', 'onboarding_completed'] if bio else ['onboarding_completed'])

            # 5. Invalidar caché del perfil de usuario
            safe_cache_delete(user_profile_key(user.id))

        # 6. Calcular la primera recomendación visible basada en las nuevas preferencias
        first_rec = None
        try:
            recs = recommendation_service.get_user_recommendations(user=user, limit=1, request=request)
            if recs:
                first_rec = recs[0]
        except Exception as exc:
            logger.warning("No se pudo calcular la primera recomendación de onboarding para @%s: %s", user.username, exc)

        logger.info("Usuario @%s completó con éxito el onboarding.", user.username)

        return Response({
            'success': True,
            'detail': 'Onboarding completado con éxito. ¡Bienvenido a MyBookConnect!',
            'first_recommendation': first_rec,
        }, status=status.HTTP_200_OK)


class OnboardingSkipView(APIView):
    """
    Endpoint para omitir el Onboarding y acceder directamente al catálogo (Fase 19).
    Cumple con el principio de no bloquear la navegación con pantallas obligatorias.
    POST /api/v1/users/onboarding/skip/
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Omitir el flujo de Onboarding",
        description="Marca el onboarding como completado permitiendo explorar la plataforma de inmediato.",
        responses={
            200: inline_serializer(
                name='OnboardingSkipResponse',
                fields={
                    'success': serializers.BooleanField(),
                    'detail': serializers.CharField(),
                },
            ),
        },
        tags=['Onboarding'],
    )
    def post(self, request):
        user = request.user
        user.onboarding_completed = True
        user.save(update_fields=['onboarding_completed'])

        safe_cache_delete(user_profile_key(user.id))
        logger.info("Usuario @%s omitió el flujo de onboarding.", user.username)

        return Response({
            'success': True,
            'detail': 'Flujo de bienvenida omitido. Puedes personalizar tus lecturas en cualquier momento.',
        }, status=status.HTTP_200_OK)
