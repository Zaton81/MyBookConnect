from django.urls import path

from .views import (
    ReviewCommentDeleteView,
    ReviewCommentListCreateView,
    ReviewDetailView,
    ReviewLikeToggleView,
    ReviewListCreateView,
)

urlpatterns = [
    path('', ReviewListCreateView.as_view(), name='canonical-reviews-list-create'),
    path('<int:pk>/', ReviewDetailView.as_view(), name='canonical-review-detail'),
    path('<int:review_id>/like/', ReviewLikeToggleView.as_view(), name='canonical-review-like'),
    path('<int:review_id>/comments/', ReviewCommentListCreateView.as_view(), name='canonical-review-comments'),
    path('<int:review_id>/comments/<int:comment_id>/', ReviewCommentDeleteView.as_view(), name='canonical-review-comment-delete'),
]
