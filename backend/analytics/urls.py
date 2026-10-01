from django.urls import path

from analytics.views import (
    AnalyticsCollectView,
    AnalyticsFunnelView,
    AnalyticsRetentionView,
    AnalyticsSummaryView,
)

urlpatterns = [
    path('collect/', AnalyticsCollectView.as_view(), name='analytics-collect'),
    path('funnel/', AnalyticsFunnelView.as_view(), name='analytics-funnel'),
    path('retention/', AnalyticsRetentionView.as_view(), name='analytics-retention'),
    path('summary/', AnalyticsSummaryView.as_view(), name='analytics-summary'),
]
