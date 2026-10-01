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
    RegistrationStatusView,
    SupportTicketCreateView,
    UserReferralCodeView,
    UserReferralStatsView,
    UserSupportTicketListView,
    VerifyBetaInvitationView,
)

urlpatterns = [
    path('registration-status/', RegistrationStatusView.as_view(), name='beta-registration-status'),
    path('feedback/', BetaFeedbackCreateView.as_view(), name='beta-feedback-create'),
    path('admin/feedback/', BetaFeedbackAdminListView.as_view(), name='beta-feedback-admin-list'),
    path('admin/feedback/<int:pk>/', BetaFeedbackAdminDetailView.as_view(), name='beta-feedback-admin-detail'),
    path('admin/invitations/', BetaInvitationAdminView.as_view(), name='beta-invitations-admin'),
    path('admin/metrics/', BetaCohortMetricsAdminView.as_view(), name='beta-admin-metrics'),
    path('admin/alerts/', AdminBetaAlertsView.as_view(), name='beta-admin-alerts'),
    path('invitations/verify/', VerifyBetaInvitationView.as_view(), name='beta-invitation-verify'),
    path('referrals/my-code/', UserReferralCodeView.as_view(), name='beta-referral-code'),
    path('referrals/stats/', UserReferralStatsView.as_view(), name='beta-referral-stats'),
    path('support/', SupportTicketCreateView.as_view(), name='beta-support-create'),
    path('support/my/', UserSupportTicketListView.as_view(), name='beta-support-user-list'),
    path('admin/support/', AdminSupportTicketListView.as_view(), name='beta-support-admin-list'),
    path('admin/support/<int:pk>/', AdminSupportTicketDetailView.as_view(), name='beta-support-admin-detail'),
]
