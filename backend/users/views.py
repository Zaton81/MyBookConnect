from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from .serializers import UserSerializer, UserCreateSerializer

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
    queryset = User.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserSerializer
    lookup_field = 'id'

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user

        # Allow user to see their own profile
        if instance == user:
            serializer = self.get_serializer(instance)
            return Response(serializer.data)

        # Check if blocked
        # if user.blocked_users.filter(id=instance.id).exists():
        #    return Response({"detail": "Has bloqueado a este usuario."}, status=status.HTTP_403_FORBIDDEN)
        
        # Check if blocked by target (I am blocked)
        if instance.blocked_users.filter(id=user.id).exists():
            return Response({"detail": "No puedes ver este perfil."}, status=status.HTTP_403_FORBIDDEN)

        # Check if I blocked them (Allow access to unblock, bypass privacy?)
        has_blocked = user.blocked_users.filter(id=instance.id).exists()
        
        if not has_blocked:
            # Check privacy
            if instance.privacy_level == 'private':
                return Response({"detail": "Este perfil es privado."}, status=status.HTTP_403_FORBIDDEN)
            
            if instance.privacy_level == 'friends':
                # Must be following to see
                if not user.following.filter(id=instance.id).exists():
                    return Response({"detail": "Este perfil es solo para amigos."}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

class FollowUserView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, id):
        user_to_follow = get_object_or_404(User, id=id)
        if request.user == user_to_follow:
            return Response({"detail": "No puedes seguirte a ti mismo."}, status=status.HTTP_400_BAD_REQUEST)
        
        if user_to_follow.blocked_users.filter(id=request.user.id).exists():
             return Response({"detail": "No puedes seguir a este usuario."}, status=status.HTTP_403_FORBIDDEN)

        request.user.following.add(user_to_follow)
        return Response({"detail": f"Ahora sigues a {user_to_follow.username}"}, status=status.HTTP_200_OK)

class UnfollowUserView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, id):
        user_to_unfollow = get_object_or_404(User, id=id)
        request.user.following.remove(user_to_unfollow)
        return Response({"detail": f"Dejaste de seguir a {user_to_unfollow.username}"}, status=status.HTTP_200_OK)

class BlockUserView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, id):
        user_to_block = get_object_or_404(User, id=id)
        if request.user == user_to_block:
             return Response({"detail": "No puedes bloquearte a ti mismo."}, status=status.HTTP_400_BAD_REQUEST)

        request.user.blocked_users.add(user_to_block)
        # Also unfollow if blocking
        request.user.following.remove(user_to_block)
        # And remove from their followers (if symmetrical friendship was implied, but here following is one-way)
        # If they follow me, should I remove them? Maybe not strictly required by model but good practice.
        # user_to_block.following.remove(request.user) 
        
        return Response({"detail": f"Has bloqueado a {user_to_block.username}"}, status=status.HTTP_200_OK)

class UnblockUserView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, id):
        user_to_unblock = get_object_or_404(User, id=id)
        request.user.blocked_users.remove(user_to_unblock)
        return Response({"detail": f"Has desbloqueado a {user_to_unblock.username}"}, status=status.HTTP_200_OK)
