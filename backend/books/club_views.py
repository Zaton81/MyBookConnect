from rest_framework import status, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from django.db.models import Count, Q, Prefetch
from django.shortcuts import get_object_or_404

from .club_models import (
    ReadingClub,
    ReadingClubMember,
    ReadingClubBook,
    ReadingClubDiscussion,
    ReadingClubDiscussionComment,
)
from .club_serializers import (
    ReadingClubListSerializer,
    ReadingClubDetailSerializer,
    ReadingClubMemberSerializer,
    ReadingClubBookSerializer,
    ReadingClubDiscussionSerializer,
    ReadingClubDiscussionCommentSerializer,
)


class IsClubAdminOrReadOnly(permissions.BasePermission):
    """
    Permiso que permite lectura a cualquiera (si es público) o miembros (si es privado),
    y modificación únicamente a Administradores del club.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            if not obj.is_private:
                return True
            if not request.user.is_authenticated:
                return False
            return obj.memberships.filter(
                user=request.user,
                status=ReadingClubMember.Status.ACTIVE,
            ).exists() or request.user.is_staff

        if not request.user.is_authenticated:
            return False
        return obj.memberships.filter(
            user=request.user,
            role=ReadingClubMember.Role.ADMIN,
            status=ReadingClubMember.Status.ACTIVE,
        ).exists() or request.user.is_staff or obj.creator == request.user


class ReadingClubViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión integral de clubs de lectura.
    RoadmapV3 Sección 30.1.
    """
    lookup_field = 'slug'
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsClubAdminOrReadOnly]

    def get_serializer_class(self):
        if self.action in ['list']:
            return ReadingClubListSerializer
        return ReadingClubDetailSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = ReadingClub.objects.select_related(
            'creator',
            'current_book',
            'current_book__author',
        ).annotate(
            _annotated_members_count=Count(
                'memberships',
                filter=Q(memberships__status=ReadingClubMember.Status.ACTIVE),
                distinct=True,
            )
        )

        my_clubs = self.request.query_params.get('my_clubs')
        if my_clubs and my_clubs.lower() in ['true', '1']:
            if not user.is_authenticated:
                return queryset.none()
            return queryset.filter(
                memberships__user=user,
                memberships__status=ReadingClubMember.Status.ACTIVE,
            ).distinct()

        # Filtro de visibilidad general: clubs públicos visibles para todos; privados solo si es miembro o staff
        q = self.request.query_params.get('q')
        if q:
            queryset = queryset.filter(
                Q(name__icontains=q) | Q(description__icontains=q)
            )

        if self.action in ['join', 'leave', 'members', 'manage_member', 'books']:
            return queryset

        if not user.is_authenticated or not user.is_staff:
            queryset = queryset.filter(
                Q(is_private=False) |
                Q(memberships__user=user, memberships__status=ReadingClubMember.Status.ACTIVE)
            ).distinct()

        return queryset

    def perform_create(self, serializer):
        club = serializer.save(creator=self.request.user)
        # Crear membresía de ADMIN automática para el creador
        ReadingClubMember.objects.create(
            club=club,
            user=self.request.user,
            role=ReadingClubMember.Role.ADMIN,
            status=ReadingClubMember.Status.ACTIVE,
        )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def join(self, request, slug=None):
        club = self.get_object()
        user = request.user

        membership = ReadingClubMember.objects.filter(club=club, user=user).first()
        if membership:
            if membership.status == ReadingClubMember.Status.ACTIVE:
                return Response(
                    {'detail': 'Ya eres miembro activo de este club.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            elif membership.status == ReadingClubMember.Status.BANNED:
                return Response(
                    {'detail': 'Has sido bloqueado de este club.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            elif membership.status == ReadingClubMember.Status.PENDING:
                return Response(
                    {'detail': 'Tu solicitud de ingreso ya está pendiente de aprobación.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        initial_status = (
            ReadingClubMember.Status.PENDING
            if club.is_private
            else ReadingClubMember.Status.ACTIVE
        )

        ReadingClubMember.objects.create(
            club=club,
            user=user,
            role=ReadingClubMember.Role.MEMBER,
            status=initial_status,
        )

        msg = (
            'Solicitud enviada para aprobación del administrador.'
            if club.is_private
            else 'Te has unido exitosamente al club.'
        )
        return Response({'detail': msg, 'status': initial_status}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def leave(self, request, slug=None):
        club = self.get_object()
        user = request.user

        membership = ReadingClubMember.objects.filter(club=club, user=user).first()
        if not membership:
            return Response(
                {'detail': 'No perteneces a este club.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if membership.role == ReadingClubMember.Role.ADMIN:
            # Comprobar si hay otro admin
            other_admins = ReadingClubMember.objects.filter(
                club=club,
                role=ReadingClubMember.Role.ADMIN,
                status=ReadingClubMember.Status.ACTIVE,
            ).exclude(user=user).exists()
            if not other_admins:
                return Response(
                    {'detail': 'Eres el único administrador del club. Asigna otro administrador antes de salir o elimina el club.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        membership.delete()
        return Response({'detail': 'Has salido del club correctamente.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticatedOrReadOnly])
    def members(self, request, slug=None):
        club = self.get_object()
        memberships = club.memberships.select_related('user').order_by('role', '-joined_at')
        serializer = ReadingClubMemberSerializer(memberships, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'], url_path='members/(?P<user_id>[^/.]+)', permission_classes=[permissions.IsAuthenticated])
    def manage_member(self, request, slug=None, user_id=None):
        club = self.get_object()
        actor = request.user

        # Verificar si el actor es ADMIN o MODERATOR
        actor_membership = ReadingClubMember.objects.filter(
            club=club,
            user=actor,
            status=ReadingClubMember.Status.ACTIVE,
        ).first()

        if not actor_membership or actor_membership.role not in [
            ReadingClubMember.Role.ADMIN,
            ReadingClubMember.Role.MODERATOR,
        ]:
            if not actor.is_staff and club.creator != actor:
                raise PermissionDenied('No tienes permisos de moderación en este club.')

        target_membership = get_object_or_404(ReadingClubMember, club=club, user_id=user_id)

        new_role = request.data.get('role')
        new_status = request.data.get('status')

        if new_role:
            if actor_membership and actor_membership.role != ReadingClubMember.Role.ADMIN and not actor.is_staff:
                raise PermissionDenied('Solo los administradores pueden cambiar roles de miembros.')
            if new_role in ReadingClubMember.Role.values:
                target_membership.role = new_role

        if new_status:
            if new_status in ReadingClubMember.Status.values:
                target_membership.status = new_status

        target_membership.save()
        serializer = ReadingClubMemberSerializer(target_membership)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'], permission_classes=[permissions.IsAuthenticatedOrReadOnly])
    def books(self, request, slug=None):
        club = self.get_object()

        if request.method == 'GET':
            books = club.reading_plan.select_related('book', 'book__author').order_by('-created_at')
            serializer = ReadingClubBookSerializer(books, many=True)
            return Response(serializer.data)

        # POST: Añadir libro al plan de lectura
        if not request.user.is_authenticated:
            raise PermissionDenied('Debes iniciar sesión para proponer lecturas.')

        # Verificar permisos de admin o moderador
        actor_membership = ReadingClubMember.objects.filter(
            club=club,
            user=request.user,
            status=ReadingClubMember.Status.ACTIVE,
        ).first()

        if not actor_membership or actor_membership.role not in [
            ReadingClubMember.Role.ADMIN,
            ReadingClubMember.Role.MODERATOR,
        ]:
            if not request.user.is_staff and club.creator != request.user:
                raise PermissionDenied('Solo los moderadores y administradores pueden gestionar el plan de lectura.')

        serializer = ReadingClubBookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reading_book = serializer.save(club=club)

        # Si el status es CURRENT, actualizar también current_book en ReadingClub
        if reading_book.status == ReadingClubBook.ReadingStatus.CURRENT:
            club.current_book = reading_book.book
            club.save(update_fields=['current_book'])

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ReadingClubDiscussionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para los hilos de debate de un club.
    """
    serializer_class = ReadingClubDiscussionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_club(self):
        club_slug = self.kwargs.get('club_slug')
        return get_object_or_404(ReadingClub, slug=club_slug)

    def get_queryset(self):
        club = self.get_club()
        user = self.request.user

        # Verificar privacidad del club
        if club.is_private:
            if not user.is_authenticated:
                return ReadingClubDiscussion.objects.none()
            is_active_member = club.memberships.filter(
                user=user,
                status=ReadingClubMember.Status.ACTIVE,
            ).exists()
            if not is_active_member and not user.is_staff:
                return ReadingClubDiscussion.objects.none()

        qs = ReadingClubDiscussion.objects.filter(club=club).select_related(
            'author',
            'book',
        ).annotate(
            _annotated_comments_count=Count('comments', distinct=True)
        ).order_by('-is_pinned', '-created_at')

        book_id = self.request.query_params.get('book_id')
        if book_id:
            qs = qs.filter(book_id=book_id)

        return qs

    def perform_create(self, serializer):
        club = self.get_club()
        user = self.request.user

        # Comprobar que el usuario es miembro activo
        is_member = club.memberships.filter(
            user=user,
            status=ReadingClubMember.Status.ACTIVE,
        ).exists()
        if not is_member and not user.is_staff and club.creator != user:
            raise PermissionDenied('Debes ser miembro activo del club para abrir debates.')

        serializer.save(club=club, author=user)

    @action(detail=True, methods=['get', 'post'], permission_classes=[permissions.IsAuthenticatedOrReadOnly])
    def comments(self, request, club_slug=None, pk=None):
        discussion = self.get_object()

        if request.method == 'GET':
            comments = discussion.comments.select_related('author').order_by('created_at')
            serializer = ReadingClubDiscussionCommentSerializer(comments, many=True)
            return Response(serializer.data)

        # POST comment
        if not request.user.is_authenticated:
            raise PermissionDenied('Debes iniciar sesión para comentar.')

        # Comprobar membresía activa si el club es privado
        club = discussion.club
        if club.is_private:
            is_member = club.memberships.filter(
                user=request.user,
                status=ReadingClubMember.Status.ACTIVE,
            ).exists()
            if not is_member and not request.user.is_staff:
                raise PermissionDenied('Debes ser miembro del club para comentar.')

        serializer = ReadingClubDiscussionCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(discussion=discussion, author=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
