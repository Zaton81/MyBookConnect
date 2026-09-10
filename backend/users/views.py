from django.contrib.auth import get_user_model
from django.db.models import Count, Exists, OuterRef, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from . import policies
from .serializers import UserBasicSerializer, UserCreateSerializer, UserSerializer

User = get_user_model()


class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = UserCreateSerializer


class UserProfileView(generics.RetrieveAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class UserUpdateView(generics.UpdateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


class UserDetailView(generics.RetrieveAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserSerializer
    lookup_field = 'pk'

    def get_queryset(self):
        queryset = User.objects.all().annotate(
            reviews_count=Count('reviews', distinct=True),
            books_read_count=Count('user_books', filter=Q(user_books__is_read=True), distinct=True),
            following_count=Count('following', distinct=True),
            followers_count=Count('followers', distinct=True),
        )

        if self.request.user.is_authenticated:
            queryset = queryset.annotate(
                is_following=Exists(self.request.user.following.filter(pk=OuterRef('pk'))),
                is_blocked=Exists(self.request.user.blocked_users.filter(pk=OuterRef('pk'))),
                am_i_blocked=Exists(
                    User.objects.filter(pk=self.request.user.pk, blocked_users=OuterRef('pk'))
                ),
            )
        return queryset

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user

        if not policies.can_view_profile(user, instance):
            if instance.blocked_users.filter(id=user.id).exists():
                return Response({"detail": "No puedes ver este perfil."}, status=status.HTTP_403_FORBIDDEN)
            if instance.privacy_level == 'private':
                return Response({"detail": "Este perfil es privado."}, status=status.HTTP_403_FORBIDDEN)
            return Response(
                {"detail": "Este perfil es solo para amigos."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class FollowUserView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, user_id):
        user_to_follow = get_object_or_404(User, id=user_id)
        if request.user == user_to_follow:
            return Response({"detail": "No puedes seguirte a ti mismo."}, status=status.HTTP_400_BAD_REQUEST)

        if (
            user_to_follow.blocked_users.filter(id=request.user.id).exists()
            or request.user.blocked_users.filter(id=user_to_follow.id).exists()
        ):
            return Response({"detail": "No puedes seguir a este usuario."}, status=status.HTTP_403_FORBIDDEN)

        if user_to_follow in request.user.following.all():
            return Response({"detail": "Ya sigues a este usuario."}, status=status.HTTP_400_BAD_REQUEST)

        request.user.following.add(user_to_follow)
        return Response({"detail": f"Ahora sigues a {user_to_follow.username}"}, status=status.HTTP_200_OK)


class UnfollowUserView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, user_id):
        user_to_unfollow = get_object_or_404(User, id=user_id)
        request.user.following.remove(user_to_unfollow)
        return Response({"detail": f"Dejaste de seguir a {user_to_unfollow.username}"}, status=status.HTTP_200_OK)


class BlockUserView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, user_id):
        user_to_block = get_object_or_404(User, id=user_id)
        if request.user == user_to_block:
            return Response({"detail": "No puedes bloquearte a ti mismo."}, status=status.HTTP_400_BAD_REQUEST)

        request.user.blocked_users.add(user_to_block)
        # Ruptura bidireccional inmediata del seguimiento
        request.user.following.remove(user_to_block)
        user_to_block.following.remove(request.user)
        return Response({"detail": f"Has bloqueado a {user_to_block.username}"}, status=status.HTTP_200_OK)


class UnblockUserView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, user_id):
        user_to_unblock = get_object_or_404(User, id=user_id)
        request.user.blocked_users.remove(user_to_unblock)
        return Response({"detail": f"Has desbloqueado a {user_to_unblock.username}"}, status=status.HTTP_200_OK)


class UserSearchListView(generics.ListAPIView):
    """Búsqueda de usuarios filtrando aquellos bloqueados o que bloquearon al solicitante."""
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserBasicSerializer

    def get_queryset(self):
        query = self.request.query_params.get('q', '').strip()
        if not query:
            return User.objects.none()
        queryset = User.objects.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        ).distinct()
        return policies.filter_visible_users(self.request.user, queryset)


class UserFollowingListView(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserBasicSerializer

    def get_queryset(self):
        return self.request.user.following.all()


class UserFollowersListView(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserBasicSerializer

    def get_queryset(self):
        return self.request.user.followers.all()


class CheckFollowStatusView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, user_id):
        target_user = get_object_or_404(User, id=user_id)
        is_following = target_user in request.user.following.all()
        is_follower = request.user in target_user.following.all()

        return Response({
            "is_following": is_following,
            "is_follower": is_follower,
            "is_mutual": is_following and is_follower,
        })


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def toggle_editor(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_editor = not getattr(user, 'is_editor', False)
    user.save(update_fields=['is_editor'])
    return Response({'id': user.id, 'is_editor': user.is_editor})


class LogoutView(APIView):
    """
    Invalida el refresh token provisto añadiéndolo a la lista negra (Blacklist).
    """
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'detail': 'El token refresh es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            from rest_framework_simplejwt.tokens import RefreshToken
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'detail': 'Sesión cerrada exitosamente.'}, status=status.HTTP_200_OK)
        except Exception:
            return Response({'detail': 'Token inválido o ya revocado.'}, status=status.HTTP_400_BAD_REQUEST)

