from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from books.models import Author
from books.pagination import StandardResultsSetPagination
from books.throttling import AuthorClaimThrottle

from .models import (
    AuthorAnnouncement,
    AuthorClaim,
    AuthorClaimStatus,
    AuthorEvent,
    AuthorEventAttendee,
    AuthorNewsletter,
    AuthorNewsletterIssue,
    AuthorNewsletterSubscriber,
    AuthorProfile,
)
from .serializers import (
    AuthorAnnouncementCreateUpdateSerializer,
    AuthorAnnouncementSerializer,
    AuthorClaimAdminSerializer,
    AuthorClaimCreateSerializer,
    AuthorEventAttendeeSerializer,
    AuthorEventCreateUpdateSerializer,
    AuthorEventSerializer,
    AuthorNewsletterCreateUpdateSerializer,
    AuthorNewsletterIssueCreateUpdateSerializer,
    AuthorNewsletterIssueSerializer,
    AuthorNewsletterSerializer,
    AuthorNewsletterSubscriberSerializer,
    AuthorProfileSerializer,
)
from .services import AuthorService


class AuthorProfileMeView(APIView):
    """
    Consulta y actualización del perfil de autor del usuario autenticado.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile = AuthorService.get_or_create_profile(request.user)
        serializer = AuthorProfileSerializer(profile, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        profile = AuthorService.get_or_create_profile(request.user)
        for field in ('pen_name', 'bio', 'website', 'twitter', 'instagram'):
            if field in request.data:
                setattr(profile, field, request.data[field])
        profile.save()
        serializer = AuthorProfileSerializer(profile, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class AuthorClaimView(APIView):
    """
    Permite a un usuario solicitar la verificación o reclamo de un autor del catálogo.
    """
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AuthorClaimThrottle]

    def post(self, request):
        author_id = request.data.get('author_id')
        if not author_id:
            return Response({'detail': 'El campo author_id es obligatorio.'}, status=status.HTTP_400_BAD_REQUEST)

        pen_name = request.data.get('pen_name', '')
        verification_notes = request.data.get('verification_notes', '')

        try:
            profile = AuthorService.claim_author(
                user=request.user,
                author_id=int(author_id),
                pen_name=pen_name,
                verification_notes=verification_notes,
            )
            serializer = AuthorProfileSerializer(profile, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValueError as err:
            return Response({'detail': str(err)}, status=status.HTTP_400_BAD_REQUEST)


class AuthorDashboardView(APIView):
    """
    Panel analítico privado con métricas consolidadas de las obras del autor.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile = AuthorService.get_or_create_profile(request.user)
        metrics = AuthorService.get_author_dashboard_metrics(profile)
        return Response(metrics, status=status.HTTP_200_OK)


class AuthorAnnouncementCreateView(APIView):
    """
    Publicación de comunicados y publicaciones avanzadas por parte de un autor verificado.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        profile = AuthorService.get_or_create_profile(request.user)
        title = request.data.get('title', '').strip()
        content = request.data.get('content', '').strip()
        book_id = request.data.get('book_id')
        is_pinned = bool(request.data.get('is_pinned', False))
        publication_type = request.data.get('publication_type', 'ANNOUNCEMENT')
        excerpt = request.data.get('excerpt', '').strip()
        has_spoilers = bool(request.data.get('has_spoilers', False))
        spoiler_warning = request.data.get('spoiler_warning', '').strip()
        estimated_reading_time = request.data.get('estimated_reading_time')
        is_draft = bool(request.data.get('is_draft', False))
        is_paid = bool(request.data.get('is_paid', False))
        price = request.data.get('price')
        author_id = request.data.get('author_id') or request.data.get('author')

        if not title or not content:
            return Response(
                {'detail': 'Título y contenido son obligatorios.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target_author = None
        if author_id:
            target_author = Author.objects.filter(id=int(author_id)).first()
        elif profile.author:
            target_author = profile.author

        if not target_author:
            return Response(
                {'detail': 'Debes especificar un autor del catálogo verificado para publicar.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Regla estricta: Solo el autor verificado titular puede publicar en su perfil
        is_verified_owner = (
            (target_author.claimed_by_id == request.user.id and target_author.is_verified) or
            (profile.author_id == target_author.id and profile.is_verified)
        )
        if not is_verified_owner:
            return Response(
                {'detail': 'Solo el autor verificado titular de esta página puede publicar en su perfil.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        announcement = AuthorService.create_announcement(
            author_profile=profile,
            title=title,
            content=content,
            book_id=int(book_id) if book_id else None,
            is_pinned=is_pinned,
            publication_type=publication_type,
            excerpt=excerpt,
            has_spoilers=has_spoilers,
            spoiler_warning=spoiler_warning,
            estimated_reading_time=int(estimated_reading_time) if estimated_reading_time else None,
            is_draft=is_draft,
            author_id=target_author.id,
            is_paid=is_paid,
            price=float(price) if price is not None else None,
        )
        serializer = AuthorAnnouncementSerializer(announcement, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AuthorAnnouncementListView(APIView):
    """
    Listado público de comunicados y publicaciones avanzadas para un autor del catálogo.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        include_drafts = False
        if request.user.is_authenticated and request.query_params.get('drafts') == 'true':
            include_drafts = True

        include_moderated = False
        if request.user.is_authenticated:
            is_admin = request.user.is_staff or getattr(request.user, 'role', '') in ('ADMIN', 'MODERATOR')
            include_moderated = is_admin

        pub_type = request.query_params.get('type') or request.query_params.get('publication_type')
        announcements = AuthorService.get_announcements_for_author(
            author_id=pk,
            include_drafts=include_drafts,
            publication_type=pub_type,
            include_moderated=include_moderated,
        )
        serializer = AuthorAnnouncementSerializer(announcements, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class AuthorClaimCreateView(APIView):
    """
    Permite a un usuario autenticado reclamar la página de un autor del catálogo.
    RoadmapV3 Sprint 3 (Sección 4.4).
    """
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AuthorClaimThrottle]

    @extend_schema(
        summary="Reclamar página de autor",
        tags=['Authors'],
    )
    def post(self, request, pk):
        author = get_object_or_404(Author, id=pk)
        serializer = AuthorClaimCreateSerializer(
            data=request.data,
            context={'author': author, 'user': request.user, 'request': request},
        )
        serializer.is_valid(raise_exception=True)
        claim = serializer.save()
        return Response(
            AuthorClaimAdminSerializer(claim, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class AuthorClaimStatusView(APIView):
    """
    Comprueba si el usuario autenticado tiene reclamaciones para este autor.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Consultar estado de reclamación del autor para el usuario actual",
        tags=['Authors'],
    )
    def get(self, request, pk):
        author = get_object_or_404(Author, id=pk)
        latest_claim = AuthorClaim.objects.filter(
            author=author,
            user=request.user,
        ).order_by('-created_at').first()

        is_owner = (author.claimed_by_id == request.user.id)
        has_pending = (latest_claim.status == AuthorClaimStatus.PENDING) if latest_claim else False

        return Response({
            'author_id': author.id,
            'is_verified': author.is_verified,
            'is_owner': is_owner,
            'has_pending_claim': has_pending,
            'claim_status': latest_claim.status if latest_claim else None,
            'claim_id': latest_claim.id if latest_claim else None,
        }, status=status.HTTP_200_OK)


class AuthorEventViewSet(viewsets.ModelViewSet):
    """
    Gestión y consulta de eventos literarios de autores (presentaciones, firmas, Q&A, etc.).
    RoadmapV3 Sección 30 — Sprint 11.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = AuthorEvent.objects.select_related('author', 'book', 'created_by', 'author_profile').prefetch_related('attendees')

        author_id = self.request.query_params.get('author') or self.request.query_params.get('author_id')
        if author_id:
            qs = qs.filter(author_id=author_id)

        book_id = self.request.query_params.get('book') or self.request.query_params.get('book_id')
        if book_id:
            qs = qs.filter(book_id=book_id)

        event_type = self.request.query_params.get('event_type')
        if event_type:
            qs = qs.filter(event_type=event_type)

        event_format = self.request.query_params.get('format') or self.request.query_params.get('event_format')
        if event_format:
            qs = qs.filter(event_format=event_format)

        upcoming = self.request.query_params.get('upcoming')
        if upcoming in ('true', '1', 'True'):
            qs = qs.filter(start_time__gte=timezone.now(), is_cancelled=False)
        elif self.request.query_params.get('past') in ('true', '1', 'True'):
            qs = qs.filter(start_time__lt=timezone.now())

        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search) | Q(location_name__icontains=search))

        return qs.order_by('start_time')

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return AuthorEventCreateUpdateSerializer
        return AuthorEventSerializer

    def perform_create(self, serializer):
        author = serializer.validated_data['author']
        author_profile = AuthorProfile.objects.filter(user=self.request.user, author=author).first()
        serializer.save(created_by=self.request.user, author_profile=author_profile)

    def perform_destroy(self, instance):
        user = self.request.user
        is_owner = (instance.created_by_id == user.id or instance.author.claimed_by_id == user.id)
        is_staff = user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
        if not (is_owner or is_staff):
            raise PermissionDenied("No tienes permisos para eliminar este evento.")
        instance.delete()

    def perform_update(self, serializer):
        user = self.request.user
        instance = self.get_object()
        is_owner = (instance.created_by_id == user.id or instance.author.claimed_by_id == user.id)
        is_staff = user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
        if not (is_owner or is_staff):
            raise PermissionDenied("No tienes permisos para modificar este evento.")
        serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def register(self, request, pk=None):
        event = self.get_object()

        if event.is_cancelled:
            return Response({'detail': 'Este evento ha sido cancelado.'}, status=status.HTTP_400_BAD_REQUEST)

        notes = request.data.get('notes', '').strip()
        attendee = AuthorEventAttendee.objects.filter(event=event, user=request.user).first()

        if attendee:
            if attendee.status in (AuthorEventAttendee.AttendeeStatus.REGISTERED, AuthorEventAttendee.AttendeeStatus.WAITLIST):
                if notes:
                    attendee.notes = notes
                    attendee.save()
                return Response({
                    'detail': f'Ya estás inscrito en este evento ({attendee.get_status_display()}).',
                    'status': attendee.status,
                    'is_waitlist': (attendee.status == AuthorEventAttendee.AttendeeStatus.WAITLIST),
                }, status=status.HTTP_200_OK)
            else:
                new_status = AuthorEventAttendee.AttendeeStatus.WAITLIST if event.is_full else AuthorEventAttendee.AttendeeStatus.REGISTERED
                attendee.status = new_status
                attendee.notes = notes
                attendee.save()
                return Response({
                    'detail': f'Inscripción reactivada ({attendee.get_status_display()}).',
                    'status': attendee.status,
                    'is_waitlist': (new_status == AuthorEventAttendee.AttendeeStatus.WAITLIST),
                }, status=status.HTTP_200_OK)

        new_status = AuthorEventAttendee.AttendeeStatus.WAITLIST if event.is_full else AuthorEventAttendee.AttendeeStatus.REGISTERED
        attendee = AuthorEventAttendee.objects.create(
            event=event,
            user=request.user,
            status=new_status,
            notes=notes,
        )
        msg = 'Te hemos añadido a la lista de espera.' if new_status == AuthorEventAttendee.AttendeeStatus.WAITLIST else '¡Inscripción confirmada!'
        return Response({
            'detail': msg,
            'status': new_status,
            'is_waitlist': (new_status == AuthorEventAttendee.AttendeeStatus.WAITLIST),
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def cancel_registration(self, request, pk=None):
        event = self.get_object()
        attendee = AuthorEventAttendee.objects.filter(event=event, user=request.user).first()

        if not attendee or attendee.status == AuthorEventAttendee.AttendeeStatus.CANCELLED:
            return Response({'detail': 'No tienes una inscripción activa para este evento.'}, status=status.HTTP_400_BAD_REQUEST)

        was_registered = (attendee.status == AuthorEventAttendee.AttendeeStatus.REGISTERED)
        attendee.status = AuthorEventAttendee.AttendeeStatus.CANCELLED
        attendee.save()

        promoted_username = None
        if was_registered:
            next_in_line = event.attendees.filter(
                status=AuthorEventAttendee.AttendeeStatus.WAITLIST
            ).order_by('created_at').first()
            if next_in_line:
                next_in_line.status = AuthorEventAttendee.AttendeeStatus.REGISTERED
                next_in_line.save()
                promoted_username = next_in_line.user.username

        return Response({
            'detail': 'Tu inscripción ha sido cancelada correctamente.',
            'status': 'CANCELLED',
            'promoted_user': promoted_username,
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def attendees(self, request, pk=None):
        event = self.get_object()
        user = request.user
        is_organizer = (event.created_by_id == user.id or event.author.claimed_by_id == user.id or user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR'))

        if is_organizer:
            attendees = event.attendees.select_related('user').all().order_by('created_at')
        else:
            attendees = event.attendees.filter(status='REGISTERED').select_related('user').order_by('created_at')

        serializer = AuthorEventAttendeeSerializer(attendees, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class AuthorPublicationViewSet(viewsets.ModelViewSet):
    """
    Gestión CRUD completa y consulta de publicaciones avanzadas de autor (adelantos, notas, comunicados).
    RoadmapV3 Sección 30 — Sprint 12.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return AuthorAnnouncementCreateUpdateSerializer
        return AuthorAnnouncementSerializer

    def get_queryset(self):
        qs = AuthorAnnouncement.objects.select_related('author_profile', 'author', 'book')

        author_id = self.request.query_params.get('author') or self.request.query_params.get('author_id')
        if author_id:
            qs = qs.filter(Q(author_id=author_id) | Q(author_profile__author_id=author_id))

        book_id = self.request.query_params.get('book') or self.request.query_params.get('book_id')
        if book_id:
            qs = qs.filter(book_id=book_id)

        pub_type = self.request.query_params.get('type') or self.request.query_params.get('publication_type')
        if pub_type:
            qs = qs.filter(publication_type=pub_type)

        is_pinned = self.request.query_params.get('pinned')
        if is_pinned in ('true', '1'):
            qs = qs.filter(is_pinned=True)

        user = self.request.user
        drafts_param = self.request.query_params.get('drafts')
        if drafts_param in ('true', '1') and user.is_authenticated:
            qs = qs.filter(Q(is_draft=False) | Q(author_profile__user=user) | Q(author__claimed_by=user))
        else:
            qs = qs.filter(is_draft=False)

        is_admin = user.is_authenticated and (user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR'))
        if not is_admin:
            if user.is_authenticated:
                qs = qs.filter(Q(is_moderated=False) | Q(author_profile__user=user) | Q(author__claimed_by=user))
            else:
                qs = qs.filter(is_moderated=False)

        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(content__icontains=search) | Q(excerpt__icontains=search))

        return qs.order_by('-is_pinned', '-created_at')

    def perform_create(self, serializer):
        user = self.request.user
        author = serializer.validated_data.get('author')
        profile = AuthorService.get_or_create_profile(user)

        if not author:
            if profile.author:
                author = profile.author
            elif Author.objects.filter(claimed_by=user).exists():
                author = Author.objects.filter(claimed_by=user).first()

        if not author:
            raise PermissionDenied("Debes estar vinculado a un autor del catálogo verificado para publicar.")

        is_verified_author = (
            (author.claimed_by_id == user.id and author.is_verified) or
            (profile.author_id == author.id and profile.is_verified)
        )
        if not is_verified_author:
            raise PermissionDenied("Solo el autor verificado titular de esta página puede publicar en su perfil.")

        serializer.save(author_profile=profile, author=author)

    def perform_update(self, serializer):
        user = self.request.user
        instance = self.get_object()
        is_author_owner = (
            ((instance.author_profile.user_id == user.id) or (instance.author and instance.author.claimed_by_id == user.id)) and
            ((instance.author and instance.author.is_verified) or instance.author_profile.is_verified)
        )
        is_admin = user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
        if not (is_author_owner or is_admin):
            raise PermissionDenied("No tienes permisos para modificar esta publicación.")

        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        is_author_owner = (
            ((instance.author_profile.user_id == user.id) or (instance.author and instance.author.claimed_by_id == user.id)) and
            ((instance.author and instance.author.is_verified) or instance.author_profile.is_verified)
        )
        is_admin = user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
        if not (is_author_owner or is_admin):
            raise PermissionDenied("No tienes permisos para eliminar esta publicación.")

        instance.delete()

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def toggle_pin(self, request, pk=None):
        instance = self.get_object()
        user = request.user
        is_author_owner = (
            ((instance.author_profile.user_id == user.id) or (instance.author and instance.author.claimed_by_id == user.id)) and
            ((instance.author and instance.author.is_verified) or instance.author_profile.is_verified)
        )
        is_admin = user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
        if not (is_author_owner or is_admin):
            return Response({'detail': 'No tienes permisos.'}, status=status.HTTP_403_FORBIDDEN)
        instance.is_pinned = not instance.is_pinned
        instance.save()
        return Response({'id': instance.id, 'is_pinned': instance.is_pinned}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def censor(self, request, pk=None):
        """
        Permite a un administrador o moderador censurar u ocultar una publicación de autor.
        """
        from users.audit_service import log_audit
        from users.models import AuditAction

        instance = self.get_object()
        user = request.user
        is_admin = user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
        if not is_admin:
            return Response(
                {'detail': 'Solo los administradores o moderadores pueden censurar publicaciones.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        target_flag = request.data.get('is_moderated')
        if target_flag is None:
            instance.is_moderated = not instance.is_moderated
        else:
            instance.is_moderated = bool(target_flag)

        reason = request.data.get('reason', request.data.get('moderation_reason', '')).strip()
        if reason:
            instance.moderation_reason = reason
        elif instance.is_moderated and not instance.moderation_reason:
            instance.moderation_reason = 'Contenido censurado por el equipo de administración.'

        instance.moderated_by = user
        instance.moderated_at = timezone.now() if instance.is_moderated else None
        instance.save(update_fields=['is_moderated', 'moderation_reason', 'moderated_by', 'moderated_at'])

        try:
            log_audit(
                action=AuditAction.CONTENT_HIDE if instance.is_moderated else AuditAction.CONTENT_RESTORE,
                actor=user,
                target=instance,
                request=request,
                metadata={'reason': instance.moderation_reason, 'publication_id': instance.id},
            )
        except Exception:
            pass

        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AuthorNewsletterViewSet(viewsets.ModelViewSet):
    """
    CRUD y gestión de newsletters/boletines literarios de autores, con suscripción 1-clic y consulta de suscriptores.
    """
    queryset = AuthorNewsletter.objects.select_related('author', 'author_profile').prefetch_related('subscribers', 'issues')
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return AuthorNewsletterCreateUpdateSerializer
        return AuthorNewsletterSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        author_id = self.request.query_params.get('author') or self.request.query_params.get('author_id')
        if author_id:
            qs = qs.filter(Q(author_id=author_id) | Q(author_profile__author_id=author_id))

        user = self.request.user
        if not user.is_staff and getattr(user, 'role', '') not in ('ADMIN', 'MODERATOR'):
            if user.is_authenticated:
                qs = qs.filter(Q(is_active=True) | Q(author__claimed_by=user) | Q(author_profile__user=user))
            else:
                qs = qs.filter(is_active=True)
        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        user = self.request.user
        author = serializer.validated_data.get('author')
        profile = AuthorService.get_or_create_profile(user)
        if not author and profile.author:
            author = profile.author
        serializer.save(author=author, author_profile=profile)

    def perform_update(self, serializer):
        user = self.request.user
        instance = self.get_object()
        is_owner = (
            (instance.author_profile and instance.author_profile.user_id == user.id) or
            (instance.author and instance.author.claimed_by_id == user.id) or
            user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
        )
        if not is_owner:
            raise PermissionDenied("No tienes permisos para modificar este boletín.")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        is_owner = (
            (instance.author_profile and instance.author_profile.user_id == user.id) or
            (instance.author and instance.author.claimed_by_id == user.id) or
            user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
        )
        if not is_owner:
            raise PermissionDenied("No tienes permisos para eliminar este boletín.")
        instance.delete()

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def subscribe(self, request, pk=None):
        newsletter = self.get_object()
        sub, created = AuthorNewsletterSubscriber.objects.get_or_create(
            newsletter=newsletter,
            user=request.user,
            defaults={'is_active': True}
        )
        if not created and not sub.is_active:
            sub.is_active = True
            sub.unsubscribed_at = None
            sub.save(update_fields=['is_active', 'unsubscribed_at'])

        return Response({
            'detail': 'Te has suscrito correctamente al boletín del autor.',
            'is_subscribed': True,
            'active_subscribers_count': newsletter.active_subscribers_count,
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def unsubscribe(self, request, pk=None):
        newsletter = self.get_object()
        sub = AuthorNewsletterSubscriber.objects.filter(newsletter=newsletter, user=request.user).first()
        if sub and sub.is_active:
            sub.is_active = False
            sub.unsubscribed_at = timezone.now()
            sub.save(update_fields=['is_active', 'unsubscribed_at'])

        return Response({
            'detail': 'Te has desuscrito del boletín.',
            'is_subscribed': False,
            'active_subscribers_count': newsletter.active_subscribers_count,
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_subscriptions(self, request):
        subs = AuthorNewsletterSubscriber.objects.filter(
            user=request.user,
            is_active=True
        ).select_related('newsletter__author')
        newsletters = [sub.newsletter for sub in subs if sub.newsletter.is_active]
        serializer = AuthorNewsletterSerializer(newsletters, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def subscribers(self, request, pk=None):
        newsletter = self.get_object()
        user = request.user
        is_owner = (
            (newsletter.author_profile and newsletter.author_profile.user_id == user.id) or
            (newsletter.author and newsletter.author.claimed_by_id == user.id) or
            user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
        )
        if not is_owner:
            return Response({'detail': 'No tienes permisos para consultar la lista de suscriptores.'}, status=status.HTTP_403_FORBIDDEN)

        subs = newsletter.subscribers.filter(is_active=True).select_related('user').order_by('-subscribed_at')
        page = self.paginate_queryset(subs)
        if page is not None:
            serializer = AuthorNewsletterSubscriberSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = AuthorNewsletterSubscriberSerializer(subs, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class AuthorNewsletterIssueViewSet(viewsets.ModelViewSet):
    """
    Gestión de entregas de boletines (borradores, programados y enviados) y acción de envío inmediato.
    """
    queryset = AuthorNewsletterIssue.objects.select_related('newsletter__author')
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return AuthorNewsletterIssueCreateUpdateSerializer
        return AuthorNewsletterIssueSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        newsletter_id = self.request.query_params.get('newsletter') or self.request.query_params.get('newsletter_id')
        if newsletter_id:
            qs = qs.filter(newsletter_id=newsletter_id)

        user = self.request.user
        if not user.is_staff and getattr(user, 'role', '') not in ('ADMIN', 'MODERATOR'):
            if user.is_authenticated:
                qs = qs.filter(
                    Q(status=AuthorNewsletterIssue.IssueStatus.SENT) |
                    Q(newsletter__author__claimed_by=user) |
                    Q(newsletter__author_profile__user=user)
                )
            else:
                qs = qs.filter(status=AuthorNewsletterIssue.IssueStatus.SENT)

        return qs.order_by('-sent_at', '-created_at')

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        instance = self.get_object()
        author = instance.newsletter.author
        is_owner = (
            (instance.newsletter.author_profile and instance.newsletter.author_profile.user_id == user.id) or
            (author and author.claimed_by_id == user.id) or
            user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
        )
        if not is_owner:
            raise PermissionDenied("No tienes permisos para modificar esta entrega.")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        author = instance.newsletter.author
        is_owner = (
            (instance.newsletter.author_profile and instance.newsletter.author_profile.user_id == user.id) or
            (author and author.claimed_by_id == user.id) or
            user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
        )
        if not is_owner:
            raise PermissionDenied("No tienes permisos para eliminar esta entrega.")
        instance.delete()

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def send_issue(self, request, pk=None):
        issue = self.get_object()
        user = request.user
        author = issue.newsletter.author
        is_owner = (
            (issue.newsletter.author_profile and issue.newsletter.author_profile.user_id == user.id) or
            (author and author.claimed_by_id == user.id) or
            user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
        )
        if not is_owner:
            return Response({'detail': 'No tienes permisos para enviar esta entrega.'}, status=status.HTTP_403_FORBIDDEN)

        recipients_count = issue.newsletter.subscribers.filter(is_active=True).count()
        issue.status = AuthorNewsletterIssue.IssueStatus.SENT
        issue.sent_at = timezone.now()
        issue.recipients_count = recipients_count
        issue.save(update_fields=['status', 'sent_at', 'recipients_count', 'updated_at'])

        serializer = AuthorNewsletterIssueSerializer(issue, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
