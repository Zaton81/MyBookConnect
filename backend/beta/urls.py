from django.urls import path
from .views import (
    BetaFeedbackAdminDetailView,
    BetaFeedbackAdminListView,
    BetaFeedbackCreateView,
    BetaInvitationAdminView,
    VerifyBetaInvitationView,
)

urlpatterns = [
    path('feedback/', BetaFeedbackCreateView.as_view(), name='beta-feedback-create'),
    path('admin/feedback/', BetaFeedbackAdminListView.as_view(), name='beta-feedback-admin-list'),
    path('admin/feedback/<int:pk>/', BetaFeedbackAdminDetailView.as_view(), name='beta-feedback-admin-detail'),
    path('admin/invitations/', BetaInvitationAdminView.as_view(), name='beta-invitations-admin'),
    path('invitations/verify/', VerifyBetaInvitationView.as_view(), name='beta-invitation-verify'),
]
