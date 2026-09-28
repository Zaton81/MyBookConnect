from django.urls import path

from analytics.views import (
    AnalyticsCollectView,
    AnalyticsFunnelView,
    AnalyticsSummaryView,
)

urlpatterns = [
    path('collect/', AnalyticsCollectView.as_view(), name='analytics-collect'),
    path('funnel/', AnalyticsFunnelView.as_view(), name='analytics-funnel'),
    path('summary/', AnalyticsSummaryView.as_view(), name='analytics-summary'),
]
