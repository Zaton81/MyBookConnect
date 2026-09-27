"""
Vistas para la gestión de cuenta, seguridad y derechos de privacidad RGPD (Fase 17).

Proporciona:
- Cambio de dirección de correo electrónico con validación de credenciales (EmailChangeView).
- Eliminación y anonimización irreversible de la cuenta con disociación de datos (AccountDeleteView).
- Exportación completa de datos personales en formato JSON estructurado y portable (DataExportView).
- Registro exhaustivo en AuditLog para cada operación sensible.
"""

import json
import logging

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from books.models import ReadingList, RecommendationFeedback, Review, ReviewComment, UserBook
from users.audit_service import log_audit
from users.models import AuditAction, Notification

User = get_user_model()
logger = logging.getLogger('mybookconnect.security')


class EmailChangeView(APIView):
    """
    Endpoint para cambiar la dirección de correo electrónico del usuario autenticado.
    Requiere la contraseña actual para verificar la identidad (Fase 17).
    POST /api/v1/users/email/change/
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Cambiar dirección de correo electrónico",
        description="Actualiza el email del usuario previa validación de su contraseña actual.",
        request=inline_serializer(
            name='EmailChangeRequest',
            fields={
                'new_email': serializers.EmailField(),
                'password': serializers.CharField(),
            },
        ),
        responses={
            200: inline_serializer(
                name='EmailChangeResponse',
                fields={
                    'detail': serializers.CharField(),
                    'email': serializers.EmailField(),
                },
            ),
            400: OpenApiResponse(description="Contraseña incorrecta o email inválido/duplicado"),
        },
        tags=['Users'],
    )
    def post(self, request):
        new_email = request.data.get('new_email', '').strip().lower()
        password = request.data.get('password') or request.data.get('current_password', '')

        if not new_email or not password:
            return Response(
                {'detail': 'Se requiere el nuevo correo electrónico y la contraseña actual.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1. Validar formato de email
        try:
            validate_email(new_email)
        except ValidationError:
            return Response(
                {'detail': 'El formato del nuevo correo electrónico no es válido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2. Validar contraseña actual
        user = request.user
        if not user.check_password(password):
            return Response(
                {'detail': 'La contraseña actual introducida es incorrecta.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3. Comprobar si el email ya pertenece al propio usuario
        if user.email and user.email.lower() == new_email:
            return Response(
                {'detail': 'El nuevo correo electrónico debe ser diferente al actual.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 4. Comprobar si el nuevo email ya está en uso por otra cuenta
        if User.objects.filter(email__iexact=new_email).exclude(id=user.id).exists():
            return Response(
                {'detail': 'Esta dirección de correo electrónico ya está registrada en el sistema.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_email = user.email

        with transaction.atomic():
            user.email = new_email
            user.is_email_verified = False
            user.save(update_fields=['email', 'is_email_verified'])

            # Registro de auditoría
            log_audit(
                action=AuditAction.EMAIL_CHANGE,
                actor=user,
                target=user,
                request=request,
                metadata={
                    "old_email": old_email,
                    "new_email": new_email,
                    "timestamp": timezone.now().isoformat(),
                },
            )

        logger.info("Usuario @%s cambió exitosamente su email de %s a %s", user.username, old_email, new_email)

        return Response({
            'detail': 'Correo electrónico actualizado correctamente. Por favor, confirma tu nueva dirección.',
            'email': new_email,
        }, status=status.HTTP_200_OK)


class AccountDeleteView(APIView):
    """
    Endpoint para solicitar la eliminación y anonimización de la cuenta (Derecho al Olvido - RGPD 22.1).
    Requiere la contraseña actual y una confirmación explícita ("DELETE" o "ELIMINAR").
    POST /api/v1/users/account/delete/
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Eliminar y anonimizar cuenta (Derecho al olvido)",
        description="Anonimiza los datos personales, desvincula relaciones sociales, oculta colecciones y revoca sesiones.",
        request=inline_serializer(
            name='AccountDeleteRequest',
            fields={
                'password': serializers.CharField(),
                'confirmation': serializers.CharField(),
            },
        ),
        responses={
            200: inline_serializer(
                name='AccountDeleteResponse',
                fields={
                    'detail': serializers.CharField(),
                    'deleted': serializers.BooleanField(),
                },
            ),
            400: OpenApiResponse(description="Contraseña errónea, confirmación inválida o superadmin único"),
        },
        tags=['Users'],
    )
    def post(self, request):
        password = request.data.get('password', '')
        confirmation = str(request.data.get('confirmation', '')).strip().upper()

        if not password or confirmation not in ('DELETE', 'ELIMINAR'):
            return Response(
                {'detail': 'Se requiere la contraseña actual y teclear la confirmación "ELIMINAR" o "DELETE".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        if not user.check_password(password):
            return Response(
                {'detail': 'La contraseña actual introducida es incorrecta.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Protección: evitar eliminar el único superusuario del sistema
        if user.is_superuser:
            active_superusers = User.objects.filter(is_superuser=True, is_active=True).exclude(id=user.id).count()
            if active_superusers < 1:
                return Response(
                    {'detail': 'No se puede eliminar la cuenta del único superadministrador activo del sistema.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        user_id = user.id
        original_username = user.username
        now = timezone.now()

        with transaction.atomic():
            # 1. Revocar tokens JWT de sesión
            try:
                tokens = OutstandingToken.objects.filter(user=user)
                for t in tokens:
                    BlacklistedToken.objects.get_or_create(token=t)
            except Exception as token_err:
                logger.warning("Error al colocar tokens en blacklist durante baja de usuario %s: %s", user_id, token_err)

            # 2. Desvincular relaciones sociales (follows, bloqueos, mutes)
            user.following.clear()
            user.followers.clear()
            user.blocked_users.clear()
            user.muted_users.clear()

            # 3. Ocultar colecciones de lectura personales (ReadingList)
            ReadingList.objects.filter(user=user).update(privacy='private', is_moderated=True)

            # 4. Soft-delete de comentarios de reseñas
            ReviewComment.objects.filter(user=user).update(deleted_at=now)

            # 5. Limpieza de notificaciones y feedbacks de recomendación
            Notification.objects.filter(recipient=user).delete()
            RecommendationFeedback.objects.filter(user=user).delete()

            # 6. Eliminar archivo de avatar si existía
            if user.avatar:
                try:
                    user.avatar.delete(save=False)
                except Exception as av_err:
                    logger.warning("No se pudo eliminar archivo avatar de usuario %s: %s", user_id, av_err)
                user.avatar = None

            # 7. Anonimización estricta de la entidad User
            user.username = f"deleted_user_{user_id}"
            user.email = f"deleted_{user_id}_{int(now.timestamp())}@deleted.local"
            user.first_name = ""
            user.last_name = ""
            user.bio = ""
            user.location = ""
            user.birth_date = None
            user.is_active = False
            user.deleted_at = now
            user.set_unusable_password()
            user.save()

            # 8. Registro de auditoría
            log_audit(
                action=AuditAction.USER_DELETE,
                actor=None,  # Cuenta disociada
                target=user,
                request=request,
                metadata={
                    "original_user_id": user_id,
                    "original_username": original_username,
                    "deleted_at": now.isoformat(),
                    "reason": "Solicitud de baja voluntaria por el titular (RGPD Art. 17)",
                },
            )

        logger.info("Cuenta de usuario #%s (@%s) eliminada y anonimizada con éxito.", user_id, original_username)

        return Response({
            'detail': 'Tu cuenta ha sido eliminada y tus datos han sido anonimizados conforme al RGPD.',
            'deleted': True,
        }, status=status.HTTP_200_OK)


class DataExportView(APIView):
    """
    Endpoint para exportar todos los datos personales del usuario en formato JSON estructurado
    (Derecho a la Portabilidad de Datos - RGPD 22.2).
    GET /api/v1/users/account/export/
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Exportar datos personales (Portabilidad RGPD)",
        description="Genera y descarga un archivo JSON completo con toda la información de la cuenta, biblioteca y actividad.",
        responses={
            200: OpenApiResponse(description="Archivo JSON descargable con todos los datos portables"),
        },
        tags=['Users'],
    )
    def get(self, request):
        user = request.user

        # 1. Perfil y preferencias
        profile_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": f"{user.first_name} {user.last_name}".strip(),
            "bio": user.bio,
            "location": user.location,
            "birth_date": user.birth_date.isoformat() if user.birth_date else None,
            "date_joined": user.date_joined.isoformat() if user.date_joined else None,
            "is_email_verified": user.is_email_verified,
            "privacy": {
                "profile": user.privacy_level,
                "reading": user.reading_privacy_level,
                "activity": user.activity_privacy_level,
                "messages": user.allow_messages_from,
                "show_email": user.show_email,
                "show_birth_date": user.show_birth_date,
                "show_location": user.show_location,
                "show_bio": user.show_bio,
            },
            "consents": {
                "terms_accepted_at": user.terms_accepted_at.isoformat() if user.terms_accepted_at else None,
                "privacy_accepted_at": user.privacy_accepted_at.isoformat() if user.privacy_accepted_at else None,
            },
            "gamification_enabled": user.gamification_enabled,
        }

        # 2. Biblioteca de lecturas (UserBook)
        library_items = []
        user_books = UserBook.objects.filter(user=user).select_related('book', 'book__author')
        for ub in user_books:
            library_items.append({
                "book_id": ub.book.id,
                "book_title": ub.book.title,
                "author_name": ub.book.author.name if ub.book.author else None,
                "isbn": ub.book.isbn,
                "reading_status": ub.status,
                "rating": ub.rating,
                "progress": ub.progress,
                "current_page": ub.current_page,
                "started_at": ub.started_at.isoformat() if ub.started_at else None,
                "finished_at": ub.finished_at.isoformat() if ub.finished_at else None,
                "owned": ub.owned,
                "wishlist": ub.wishlist,
                "notes": ub.notes,
                "updated_at": ub.updated_at.isoformat() if getattr(ub, 'updated_at', None) else None,
            })

        # 3. Reseñas redactadas (Review)
        reviews_data = []
        user_reviews = Review.objects.filter(user=user, deleted_at__isnull=True).select_related('book')
        for r in user_reviews:
            reviews_data.append({
                "review_id": r.id,
                "book_id": r.book.id,
                "book_title": r.book.title,
                "rating": r.rating,
                "review_text": r.text,
                "likes_count": r.likes.count(),
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            })

        # 4. Comentarios en reseñas (ReviewComment)
        comments_data = []
        user_comments = ReviewComment.objects.filter(user=user, deleted_at__isnull=True).select_related('review')
        for c in user_comments:
            comments_data.append({
                "comment_id": c.id,
                "review_id": c.review.id if c.review else None,
                "content": c.content,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            })

        # 5. Listas de lectura (ReadingList)
        lists_data = []
        reading_lists = ReadingList.objects.filter(user=user).prefetch_related('items__book', 'items__book__author')
        for rl in reading_lists:
            books_in_list = [
                {
                    "book_id": item.book.id,
                    "title": item.book.title,
                    "author": item.book.author.name if item.book.author else None,
                    "position": item.position,
                    "notes": item.notes,
                }
                for item in rl.items.all().order_by('position')
            ]
            lists_data.append({
                "list_id": rl.id,
                "name": rl.name,
                "slug": rl.slug,
                "description": rl.description,
                "privacy": rl.privacy,
                "created_at": rl.created_at.isoformat() if rl.created_at else None,
                "books": books_in_list,
            })

        # 6. Relaciones sociales
        following_list = list(user.following.values_list('username', flat=True))
        followers_list = list(user.followers.values_list('username', flat=True))

        # Ensamble final del paquete de datos portables (Roadmap 22.2)
        export_payload = {
            "_metadata": {
                "platform": "MyBookConnect",
                "version": "1.0.0-gdpr",
                "exported_at": timezone.now().isoformat(),
                "user_id": user.id,
                "purpose": "RGPD Portabilidad de Datos Personales (Art. 20)",
            },
            "profile": profile_data,
            "library": library_items,
            "reviews": reviews_data,
            "comments": comments_data,
            "reading_lists": lists_data,
            "social": {
                "following": following_list,
                "following_count": len(following_list),
                "followers": followers_list,
                "followers_count": len(followers_list),
            },
        }

        # Auditoría de exportación
        log_audit(
            action=AuditAction.DATA_EXPORT,
            actor=user,
            target=user,
            request=request,
            metadata={"exported_at": timezone.now().isoformat()},
        )

        json_bytes = json.dumps(export_payload, ensure_ascii=False, indent=2).encode('utf-8')
        filename = f"mybookconnect_data_export_{user.username}.json"

        response = HttpResponse(json_bytes, content_type='application/json; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(json_bytes)
        return response
