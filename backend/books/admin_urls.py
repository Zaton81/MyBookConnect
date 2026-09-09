from django.urls import path

from .admin_views import (
    AdminAuthorDetailView,
    AdminAuthorEnrichView,
    AdminAuthorListView,
    AdminBookDetailView,
    AdminBookEnrichView,
    AdminBookListView,
    AdminErrataDetailView,
    AdminErrataListView,
    AdminLegalDocumentDetailView,
    AdminLegalDocumentListView,
    AdminStatsView,
    AdminUserDetailView,
    AdminUserListView,
)

urlpatterns = [
    # Métricas y estadísticas
    path('stats/', AdminStatsView.as_view(), name='admin-stats'),

    # Usuarios
    path('users/', AdminUserListView.as_view(), name='admin-users-list'),
    path('users/<int:pk>/', AdminUserDetailView.as_view(), name='admin-users-detail'),

    # Catálogo: Libros
    path('books/', AdminBookListView.as_view(), name='admin-books-list'),
    path('books/<int:pk>/', AdminBookDetailView.as_view(), name='admin-books-detail'),
    path('books/<int:pk>/enrich/', AdminBookEnrichView.as_view(), name='admin-books-enrich'),

    # Catálogo: Autores
    path('authors/', AdminAuthorListView.as_view(), name='admin-authors-list'),
    path('authors/<int:pk>/', AdminAuthorDetailView.as_view(), name='admin-authors-detail'),
    path('authors/<int:pk>/enrich/', AdminAuthorEnrichView.as_view(), name='admin-authors-enrich'),

    # Erratas y sugerencias
    path('erratas/', AdminErrataListView.as_view(), name='admin-erratas-list'),
    path('erratas/<int:pk>/', AdminErrataDetailView.as_view(), name='admin-erratas-detail'),

    # CMS Legal
    path('legal/', AdminLegalDocumentListView.as_view(), name='admin-legal-list'),
    path('legal/<slug:slug>/', AdminLegalDocumentDetailView.as_view(), name='admin-legal-detail'),
]
