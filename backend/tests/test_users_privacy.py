import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def users_fixture():
    alice = User.objects.create_user(username='alice', email='alice@example.com', password='password123')
    bob = User.objects.create_user(username='bob', email='bob@example.com', password='password123')
    charlie = User.objects.create_user(username='charlie', email='charlie@example.com', password='password123')

    alice.privacy_level = 'public'
    alice.save()
    bob.privacy_level = 'private'
    bob.save()
    charlie.privacy_level = 'friends'
    charlie.save()

    return {'alice': alice, 'bob': bob, 'charlie': charlie}


@pytest.mark.django_db
class TestUserPrivacyAndActions:
    def test_public_profile_accessible(self, api_client, users_fixture):
        alice = users_fixture['alice']
        bob = users_fixture['bob']
        api_client.force_authenticate(user=bob)
        response = api_client.get(f'/api/v1/users/{alice.id}/')
        assert response.status_code == 200
        assert response.data['username'] == 'alice'

    def test_private_profile_denied(self, api_client, users_fixture):
        alice = users_fixture['alice']
        bob = users_fixture['bob']
        api_client.force_authenticate(user=alice)
        response = api_client.get(f'/api/v1/users/{bob.id}/')
        assert response.status_code == 403

    def test_friends_profile_requires_following(self, api_client, users_fixture):
        alice = users_fixture['alice']
        charlie = users_fixture['charlie']
        api_client.force_authenticate(user=alice)

        # Before follow -> 403
        response = api_client.get(f'/api/v1/users/{charlie.id}/')
        assert response.status_code == 403

        # Alice follows Charlie
        follow_res = api_client.post(f'/api/v1/users/{charlie.id}/follow/')
        assert follow_res.status_code == 200
        assert alice.following.filter(id=charlie.id).exists()

        # After follow -> 200
        response_after = api_client.get(f'/api/v1/users/{charlie.id}/')
        assert response_after.status_code == 200

    def test_block_action_auto_unfollows_and_blocks_access(self, api_client, users_fixture):
        alice = users_fixture['alice']
        charlie = users_fixture['charlie']
        alice.following.add(charlie)
        assert alice.following.filter(id=charlie.id).exists()

        api_client.force_authenticate(user=alice)
        block_res = api_client.post(f'/api/v1/users/{charlie.id}/block/')
        assert block_res.status_code == 200
        assert alice.blocked_users.filter(id=charlie.id).exists()

        # Auto-unfollow
        assert not alice.following.filter(id=charlie.id).exists()

        # Charlie cannot access Alice's profile (Alice blocked Charlie)
        api_client.force_authenticate(user=charlie)
        denied_res = api_client.get(f'/api/v1/users/{alice.id}/')
        assert denied_res.status_code == 403

        # Alice can still access Charlie's profile to see unblock button
        api_client.force_authenticate(user=alice)
        allowed_res = api_client.get(f'/api/v1/users/{charlie.id}/')
        assert allowed_res.status_code == 200
