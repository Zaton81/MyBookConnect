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
from .services import maybe_enrich_author, maybe_enrich_book

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


class IsAdminOrEditor(permissions.BasePermission):
    """
    Permite acceso a administradores o editores para la gestión editorial de libros/autores/erratas.
    """
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and (
                request.user.is_staff
                or request.user.is_superuser
                or getattr(request.user, 'is_editor', False)
            )
        )


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

        serializer.save()


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


class AdminBookEnrichView(APIView):
    permission_classes = [IsAdminOrEditor]

    def post(self, request, pk):
        try:
            book = Book.objects.get(pk=pk)
        except Book.DoesNotExist:
            return Response({"detail": "Libro no encontrado"}, status=status.HTTP_404_NOT_FOUND)

        book.enrichment_attempted = False
        book.save(update_fields=['enrichment_attempted'])
        maybe_enrich_book(book)
        book.refresh_from_db()
        return Response(BookSerializer(book, context={'request': request}).data)


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


class AdminAuthorEnrichView(APIView):
    permission_classes = [IsAdminOrEditor]

    def post(self, request, pk):
        try:
            author = Author.objects.get(pk=pk)
        except Author.DoesNotExist:
            return Response({"detail": "Autor no encontrado"}, status=status.HTTP_404_NOT_FOUND)

        author.enrichment_attempted = False
        author.save(update_fields=['enrichment_attempted'])
        maybe_enrich_author(author)
        author.refresh_from_db()
        return Response(AuthorSerializer(author, context={'request': request}).data)


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
