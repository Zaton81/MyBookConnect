from django.urls import path

from .views import (
    BookMarketplaceClickView,
    BookMarketplaceLinkDetailView,
    BookMarketplaceLinksView,
    BookMarketplaceView,
    PublisherDetailView,
    PublisherListView,
)

urlpatterns = [
    path('books/<int:pk>/', BookMarketplaceView.as_view(), name='marketplace-book'),
    path('books/<int:pk>/click/', BookMarketplaceClickView.as_view(), name='marketplace-click'),
    path('books/<int:pk>/links/', BookMarketplaceLinksView.as_view(), name='marketplace-links'),
    path('links/<int:link_id>/', BookMarketplaceLinkDetailView.as_view(), name='marketplace-link-detail'),
    path('publishers/', PublisherListView.as_view(), name='publisher-list'),
    path('publishers/<str:identifier>/', PublisherDetailView.as_view(), name='publisher-detail'),
]
