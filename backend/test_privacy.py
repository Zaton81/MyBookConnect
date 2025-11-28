import os
import django
from django.conf import settings
# Configure Django settings
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mybookconnect.settings')
    django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status
from django.contrib.auth import get_user_model
from users.views import UserDetailView, FollowUserView, BlockUserView, UnblockUserView

User = get_user_model()

def test_privacy_and_actions():
    print("Testing Privacy and Social Actions...")
    
    # Create users
    alice, _ = User.objects.get_or_create(username='alice', email='alice@example.com')
    bob, _ = User.objects.get_or_create(username='bob', email='bob@example.com')
    charlie, _ = User.objects.get_or_create(username='charlie', email='charlie@example.com')
    
    # Reset relationships
    alice.following.clear()
    alice.blocked_users.clear()
    bob.following.clear()
    bob.blocked_users.clear()
    charlie.following.clear()
    
    # Set privacy
    alice.privacy_level = 'public'
    alice.save()
    bob.privacy_level = 'private'
    bob.save()
    charlie.privacy_level = 'friends'
    charlie.save()

    factory = APIRequestFactory()

    # 1. Test Public Profile (Alice) - Bob can see
    request = factory.get(f'/api/v1/users/{alice.id}/')
    force_authenticate(request, user=bob)
    view = UserDetailView.as_view()
    response = view(request, id=alice.id)
    if response.status_code == 200:
        print("PASS: Public profile accessible.")
    else:
        print(f"FAIL: Public profile not accessible. {response.status_code}")

    # 2. Test Private Profile (Bob) - Alice cannot see
    request = factory.get(f'/api/v1/users/{bob.id}/')
    force_authenticate(request, user=alice)
    response = view(request, id=bob.id)
    if response.status_code == 403:
        print("PASS: Private profile denied.")
    else:
        print(f"FAIL: Private profile accessible. {response.status_code}")

    # 3. Test Friends Profile (Charlie) - Alice cannot see (not following)
    request = factory.get(f'/api/v1/users/{charlie.id}/')
    force_authenticate(request, user=alice)
    response = view(request, id=charlie.id)
    if response.status_code == 403:
        print("PASS: Friends profile denied (not following).")
    else:
        print(f"FAIL: Friends profile accessible (not following). {response.status_code}")

    # 4. Test Follow Action
    request = factory.post(f'/api/v1/users/{charlie.id}/follow/')
    force_authenticate(request, user=alice)
    follow_view = FollowUserView.as_view()
    response = follow_view(request, id=charlie.id)
    if response.status_code == 200 and alice.following.filter(id=charlie.id).exists():
        print("PASS: Follow action successful.")
    else:
        print(f"FAIL: Follow action failed. {response.status_code}")

    # 5. Test Friends Profile (Charlie) - Alice can see now
    request = factory.get(f'/api/v1/users/{charlie.id}/')
    force_authenticate(request, user=alice)
    response = view(request, id=charlie.id)
    if response.status_code == 200:
        print("PASS: Friends profile accessible (following).")
    else:
        print(f"FAIL: Friends profile denied (following). {response.status_code}")

    # 6. Test Block Action
    # Alice blocks Charlie
    request = factory.post(f'/api/v1/users/{charlie.id}/block/')
    force_authenticate(request, user=alice)
    block_view = BlockUserView.as_view()
    response = block_view(request, id=charlie.id)
    
    if response.status_code == 200 and alice.blocked_users.filter(id=charlie.id).exists():
        print("PASS: Block action successful.")
    else:
        print(f"FAIL: Block action failed. {response.status_code}")
        
    # Check if Alice unfollowed Charlie automatically
    if not alice.following.filter(id=charlie.id).exists():
        print("PASS: Auto-unfollow on block successful.")
    else:
        print("FAIL: Auto-unfollow on block failed.")

    # 7. Test Blocked Access
    # Charlie tries to see Alice (Alice blocked Charlie) -> Should be denied
    # Note: Alice is public, but blocked Charlie.
    request = factory.get(f'/api/v1/users/{alice.id}/')
    force_authenticate(request, user=charlie)
    response = view(request, id=alice.id)
    if response.status_code == 403:
        print("PASS: Blocked user denied access.")
    else:
        print(f"FAIL: Blocked user accessed profile. {response.status_code}")

    # 8. Test Blocker Access (Alice sees Charlie) -> Should be allowed (to unblock)
    request = factory.get(f'/api/v1/users/{charlie.id}/')
    force_authenticate(request, user=alice)
    response = view(request, id=charlie.id)
    if response.status_code == 200:
        print("PASS: Blocker can see profile (to unblock).")
    else:
        print(f"FAIL: Blocker denied access. {response.status_code}")

if __name__ == '__main__':
    try:
        test_privacy_and_actions()
    except Exception as e:
        print(f"ERROR: {e}")
