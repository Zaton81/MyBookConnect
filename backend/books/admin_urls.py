from django.urls import path

from users.audit_views import (
    AdminAuditLogDetailView,
    AdminAuditLogListView,
    AdminAuditLogStatsView,
)
from users.moderation_views import (
    AdminContentHideView,
    AdminContentRestoreView,
    AdminModerationStatsView,
    AdminReportDetailView,
    AdminReportListView,
    AdminUserBanView,
    AdminUserMuteView,
    AdminUserUnbanView,
    AdminUserUnmuteView,
)

from .admin_views import (
    AdminAuthorBulkActionView,
    AdminAuthorDetailView,
    AdminAuthorEnrichView,
    AdminAuthorListView,
    AdminBookBulkActionView,
    AdminBookDetailView,
    AdminBookEnrichView,
    AdminBookListView,
    AdminCategoryListView,
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
    path('books/bulk-action/', AdminBookBulkActionView.as_view(), name='admin-books-bulk-action'),
    path('books/<int:pk>/', AdminBookDetailView.as_view(), name='admin-books-detail'),
    path('books/<int:pk>/enrich/', AdminBookEnrichView.as_view(), name='admin-books-enrich'),

    # Catálogo: Autores
    path('authors/', AdminAuthorListView.as_view(), name='admin-authors-list'),
    path('authors/bulk-action/', AdminAuthorBulkActionView.as_view(), name='admin-authors-bulk-action'),
    path('authors/<int:pk>/', AdminAuthorDetailView.as_view(), name='admin-authors-detail'),
    path('authors/<int:pk>/enrich/', AdminAuthorEnrichView.as_view(), name='admin-authors-enrich'),

    # Categorías
    path('categories/', AdminCategoryListView.as_view(), name='admin-categories-list'),

    # Erratas y sugerencias
    path('erratas/', AdminErrataListView.as_view(), name='admin-erratas-list'),
    path('erratas/<int:pk>/', AdminErrataDetailView.as_view(), name='admin-erratas-detail'),

    # CMS Legal
    path('legal/', AdminLegalDocumentListView.as_view(), name='admin-legal-list'),
    path('legal/<slug:slug>/', AdminLegalDocumentDetailView.as_view(), name='admin-legal-detail'),

    # Moderación y Denuncias (Fase 29 y Fase 58)
    path('reports/', AdminReportListView.as_view(), name='admin-reports-list'),
    path('reports/stats/', AdminModerationStatsView.as_view(), name='admin-reports-stats'),
    path('reports/<int:pk>/', AdminReportDetailView.as_view(), name='admin-reports-detail'),
    path('moderation/hide/', AdminContentHideView.as_view(), name='admin-moderation-hide'),
    path('moderation/restore/', AdminContentRestoreView.as_view(), name='admin-moderation-restore'),
    path('moderation/users/<int:user_id>/mute/', AdminUserMuteView.as_view(), name='admin-moderation-user-mute'),
    path('moderation/users/<int:user_id>/unmute/', AdminUserUnmuteView.as_view(), name='admin-moderation-user-unmute'),
    path('moderation/users/<int:user_id>/ban/', AdminUserBanView.as_view(), name='admin-moderation-user-ban'),
    path('moderation/users/<int:user_id>/unban/', AdminUserUnbanView.as_view(), name='admin-moderation-user-unban'),

    # Registro de Auditoría (Fase 30)
    path('audit-logs/', AdminAuditLogListView.as_view(), name='admin-audit-logs-list'),
    path('audit-logs/stats/', AdminAuditLogStatsView.as_view(), name='admin-audit-logs-stats'),
    path('audit-logs/<int:pk>/', AdminAuditLogDetailView.as_view(), name='admin-audit-logs-detail'),
]

