import logging

from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Author, Book, Errata, ErrataStatus, LegalDocument, Review, UserBook
from .serializers import (
    AdminUserSerializer,
    AuthorSerializer,
    BookSerializer,
    ErrataSerializer,
    LegalDocumentSerializer,
)
from .tasks import enrich_book_task, refresh_author_task

logger = logging.getLogger(__name__)
User = get_user_model()


class IsAdminOrSuperUser(permissions.BasePermission):
    """
    Permite el acceso exclusivamente a usuarios activos con privilegios de staff o superusuario.
    """
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and (request.user.is_staff or request.user.is_superuser)
        )


class IsModeratorOrAdmin(permissions.BasePermission):
    """
    Permite acceso a moderadores o administradores para la gestión de denuncias y moderación (Fase 29).
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.is_active):
            return False
        from users.policies import can_moderate
        return can_moderate(request.user)


class IsAdminOrEditor(permissions.BasePermission):
    """
    Permite acceso a administradores, moderadores o editores para la gestión editorial de libros/autores/erratas.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.is_active):
            return False
        from users.policies import can_edit_catalog
        return can_edit_catalog(request.user)


class AdminStatsView(APIView):
    permission_classes = [IsAdminOrSuperUser]

    def get(self, request):
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        banned_users = total_users - active_users
        staff_users = User.objects.filter(is_staff=True).count()
        editor_users = User.objects.filter(is_editor=True).count()

        total_books = Book.objects.count()
        total_authors = Author.objects.count()
        total_reviews = Review.objects.count()
        total_user_books = UserBook.objects.count()

        open_erratas = Errata.objects.filter(status=ErrataStatus.OPEN).count()
        approved_erratas = Errata.objects.filter(status=ErrataStatus.APPROVED).count()
        total_erratas = Errata.objects.count()

        return Response({
            'users': {
                'total': total_users,
                'active': active_users,
                'banned': banned_users,
                'staff': staff_users,
                'editors': editor_users,
            },
            'catalog': {
                'books': total_books,
                'authors': total_authors,
                'reviews': total_reviews,
                'user_shelves': total_user_books,
            },
            'erratas': {
                'open': open_erratas,
                'approved': approved_erratas,
                'total': total_erratas,
            }
        })


class AdminUserListView(generics.ListAPIView):
    permission_classes = [IsAdminOrSuperUser]
    serializer_class = AdminUserSerializer

    def get_queryset(self):
        qs = User.objects.all().order_by('-date_joined')
        search = self.request.query_params.get('search')
        if search:
            search = search.strip()
            qs = qs.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )

        status_filter = self.request.query_params.get('status')
        if status_filter == 'active':
            qs = qs.filter(is_active=True)
        elif status_filter == 'banned':
            qs = qs.filter(is_active=False)

        role = self.request.query_params.get('role')
        if role == 'staff':
            qs = qs.filter(is_staff=True)
        elif role == 'editor':
            qs = qs.filter(is_editor=True)

        return qs


class AdminUserDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAdminOrSuperUser]
    serializer_class = AdminUserSerializer
    queryset = User.objects.all()

    def perform_update(self, serializer):
        instance = self.get_object()
        current_user = self.request.user
        old_active = instance.is_active
        old_staff = instance.is_staff
        old_role = getattr(instance, 'role', None)

        # Protecciones de seguridad estrictas
        if 'is_active' in self.request.data:
            target_active = bool(self.request.data.get('is_active'))
            if instance == current_user and not target_active:
                raise ValidationError({"detail": "No puedes bloquear o desactivar tu propia cuenta."})

        if 'is_staff' in self.request.data:
            target_staff = bool(self.request.data.get('is_staff'))
            if instance == current_user and not target_staff:
                raise ValidationError({"detail": "No puedes retirar tus propios permisos de administración."})

        if instance.is_superuser and not current_user.is_superuser:
            raise PermissionDenied("Solo un superadministrador puede modificar las credenciales de otro superadministrador.")

        updated_user = serializer.save()

        # Registro de auditoría
        from users.audit_service import log_audit
        from users.models import AuditAction

        if 'is_active' in self.request.data and old_active != updated_user.is_active:
            action = AuditAction.USER_UNBAN if updated_user.is_active else AuditAction.USER_BAN
            log_audit(
                action=action,
                actor=current_user,
                target=updated_user,
                request=self.request,
                metadata={"is_active": updated_user.is_active},
            )

        if 'role' in self.request.data and old_role != getattr(updated_user, 'role', None):
            log_audit(
                action=AuditAction.ROLE_CHANGE,
                actor=current_user,
                target=updated_user,
                request=self.request,
                metadata={"old_role": old_role, "new_role": updated_user.role},
            )
        elif 'is_staff' in self.request.data and old_staff != updated_user.is_staff:
            log_audit(
                action=AuditAction.ROLE_CHANGE,
                actor=current_user,
                target=updated_user,
                request=self.request,
                metadata={"old_is_staff": old_staff, "new_is_staff": updated_user.is_staff},
            )


class AdminBookListView(generics.ListCreateAPIView):
    permission_classes = [IsAdminOrEditor]
    serializer_class = BookSerializer

    def get_queryset(self):
        qs = Book.objects.select_related('author').prefetch_related('categories').order_by('-id')
        search = self.request.query_params.get('search')
        if search:
            search = search.strip()
            qs = qs.filter(
                Q(title__icontains=search)
                | Q(isbn__icontains=search)
                | Q(author__name__icontains=search)
            )
        return qs


class AdminBookDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminOrEditor]
    serializer_class = BookSerializer
    queryset = Book.objects.all()

    def perform_destroy(self, instance):
        from users.audit_service import log_audit
        from users.models import AuditAction
        log_audit(
            action=AuditAction.CONTENT_DELETE,
            actor=self.request.user,
            target=instance,
            request=self.request,
            metadata={"deleted_type": "Book", "title": instance.title},
        )
        super().perform_destroy(instance)


class AdminBookEnrichView(APIView):
    permission_classes = [IsAdminOrEditor]

    def post(self, request, pk):
        try:
            book = Book.objects.get(pk=pk)
        except Book.DoesNotExist:
            return Response({"detail": "Libro no encontrado"}, status=status.HTTP_404_NOT_FOUND)

        book.enrichment_attempted = False
        book.save(update_fields=['enrichment_attempted'])
        task = enrich_book_task.delay(book.id)
        data = BookSerializer(book, context={'request': request}).data
        data['task_id'] = task.id
        data['status'] = 'queued'
        return Response(data, status=status.HTTP_202_ACCEPTED)


class AdminAuthorListView(generics.ListCreateAPIView):
    permission_classes = [IsAdminOrEditor]
    serializer_class = AuthorSerializer

    def get_queryset(self):
        qs = Author.objects.all().order_by('name')
        search = self.request.query_params.get('search')
        if search:
            search = search.strip()
            qs = qs.filter(name__icontains=search)
        return qs


class AdminAuthorDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminOrEditor]
    serializer_class = AuthorSerializer
    queryset = Author.objects.all()

    def perform_destroy(self, instance):
        from users.audit_service import log_audit
        from users.models import AuditAction
        log_audit(
            action=AuditAction.CONTENT_DELETE,
            actor=self.request.user,
            target=instance,
            request=self.request,
            metadata={"deleted_type": "Author", "name": instance.name},
        )
        super().perform_destroy(instance)


class AdminAuthorEnrichView(APIView):
    permission_classes = [IsAdminOrEditor]

    def post(self, request, pk):
        try:
            author = Author.objects.get(pk=pk)
        except Author.DoesNotExist:
            return Response({"detail": "Autor no encontrado"}, status=status.HTTP_404_NOT_FOUND)

        author.enrichment_attempted = False
        author.save(update_fields=['enrichment_attempted'])
        task = refresh_author_task.delay(author.id)
        data = AuthorSerializer(author, context={'request': request}).data
        data['task_id'] = task.id
        data['status'] = 'queued'
        return Response(data, status=status.HTTP_202_ACCEPTED)


class AdminErrataListView(generics.ListAPIView):
    permission_classes = [IsAdminOrEditor]
    serializer_class = ErrataSerializer

    def get_queryset(self):
        qs = Errata.objects.select_related('user', 'book', 'author', 'editor').order_by('-created_at')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        errata_type = self.request.query_params.get('type')
        if errata_type:
            qs = qs.filter(type=errata_type)
        search = self.request.query_params.get('search')
        if search:
            search = search.strip()
            qs = qs.filter(
                Q(text__icontains=search)
                | Q(book__title__icontains=search)
                | Q(author__name__icontains=search)
                | Q(user__username__icontains=search)
            )
        return qs


class AdminErrataDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAdminOrEditor]
    serializer_class = ErrataSerializer
    queryset = Errata.objects.all()

    def perform_update(self, serializer):
        serializer.save(editor=self.request.user)


class AdminLegalDocumentListView(generics.ListCreateAPIView):
    permission_classes = [IsAdminOrSuperUser]
    serializer_class = LegalDocumentSerializer
    queryset = LegalDocument.objects.all().order_by('slug')

    def perform_create(self, serializer):
        serializer.save(updated_by=self.request.user)


class AdminLegalDocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminOrSuperUser]
    serializer_class = LegalDocumentSerializer
    lookup_field = 'slug'
    queryset = LegalDocument.objects.all()

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class PublicLegalDocumentView(generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LegalDocumentSerializer
    lookup_field = 'slug'
    queryset = LegalDocument.objects.all()
