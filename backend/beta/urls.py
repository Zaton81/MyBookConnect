from django.urls import path

from .views import (
    AdminBetaAlertsView,
    AdminSupportTicketDetailView,
    AdminSupportTicketListView,
    BetaCohortMetricsAdminView,
    BetaFeedbackAdminDetailView,
    BetaFeedbackAdminListView,
    BetaFeedbackCreateView,
    BetaInvitationAdminView,
    SupportTicketCreateView,
    UserSupportTicketListView,
    VerifyBetaInvitationView,
)

urlpatterns = [
    path('feedback/', BetaFeedbackCreateView.as_view(), name='beta-feedback-create'),
    path('admin/feedback/', BetaFeedbackAdminListView.as_view(), name='beta-feedback-admin-list'),
    path('admin/feedback/<int:pk>/', BetaFeedbackAdminDetailView.as_view(), name='beta-feedback-admin-detail'),
    path('admin/invitations/', BetaInvitationAdminView.as_view(), name='beta-invitations-admin'),
    path('admin/metrics/', BetaCohortMetricsAdminView.as_view(), name='beta-admin-metrics'),
    path('admin/alerts/', AdminBetaAlertsView.as_view(), name='beta-admin-alerts'),
    path('invitations/verify/', VerifyBetaInvitationView.as_view(), name='beta-invitation-verify'),
    path('support/', SupportTicketCreateView.as_view(), name='beta-support-create'),
    path('support/my/', UserSupportTicketListView.as_view(), name='beta-support-user-list'),
    path('admin/support/', AdminSupportTicketListView.as_view(), name='beta-support-admin-list'),
    path('admin/support/<int:pk>/', AdminSupportTicketDetailView.as_view(), name='beta-support-admin-detail'),
]
