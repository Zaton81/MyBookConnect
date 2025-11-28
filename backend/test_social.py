import os
import django
from django.conf import settings

# Configure Django settings
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mybookconnect.settings')
    django.setup()

from django.contrib.auth import get_user_model
from books.models import Book, UserBook, Review
from rest_framework.test import APIRequestFactory
from books.serializers import ReviewSerializer
from users.serializers import UserSerializer

User = get_user_model()

def test_sync_userbook_review():
    print("Testing UserBook -> Review Sync...")
    # Create user and book
    user, _ = User.objects.get_or_create(username='test_social_user', email='test_social@example.com')
    book, _ = Book.objects.get_or_create(title='Test Book Social', isbn='1234567890')

    # Create UserBook with notes and rating
    ub, created = UserBook.objects.update_or_create(
        user=user, book=book,
        defaults={'notes': 'Great book!', 'rating': 9}
    )

    # Check if Review was created
    review = Review.objects.filter(user=user, book=book).first()
    if review and review.text == 'Great book!' and review.rating == 9:
        print("PASS: Review created/updated from UserBook.")
    else:
        print(f"FAIL: Review not synced correctly. Found: {review}")

    # Update UserBook
    ub.notes = 'Updated note'
    ub.save()
    
    review.refresh_from_db()
    if review.text == 'Updated note':
        print("PASS: Review updated from UserBook change.")
    else:
        print(f"FAIL: Review not updated. Text: {review.text}")

def test_user_stats():
    print("\nTesting User Stats...")
    user = User.objects.get(username='test_social_user')
    
    # We just added a review (via sync), so reviews_count should be >= 1
    serializer = UserSerializer(user)
    data = serializer.data
    
    print(f"Stats: Reviews={data.get('reviews_count')}, BooksRead={data.get('books_read_count')}")
    
    if data.get('reviews_count') >= 1:
        print("PASS: reviews_count is correct.")
    else:
        print("FAIL: reviews_count is 0.")

def run_tests():
    try:
        test_sync_userbook_review()
        test_user_stats()
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == '__main__':
    run_tests()
