from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import os

from .serializers import UserSerializer, UserUpdateSerializer
from .models import User

@api_view(['POST'])
def register_user(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profile(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    # Manejar la carga del archivo de avatar si está presente
    avatar_file = request.FILES.get('avatar')
    
    # Preparar los datos para el serializador
    data = request.data.dict() if hasattr(request.data, 'dict') else request.data.copy()
    
    if avatar_file:
        # Generar un nombre único para el archivo
        filename = f"avatars/user_{request.user.id}_{avatar_file.name}"
        
        # Guardar el archivo usando el sistema de almacenamiento por defecto
        file_path = default_storage.save(filename, ContentFile(avatar_file.read()))
        
        # Actualizar la ruta del avatar en los datos
        data['avatar'] = file_path
        
        # Si el usuario ya tenía un avatar, eliminar el anterior
        if request.user.avatar:
            try:
                old_avatar_path = os.path.join(settings.MEDIA_ROOT, request.user.avatar.name)
                if os.path.isfile(old_avatar_path):
                    os.remove(old_avatar_path)
            except Exception as e:
                print(f"Error eliminando avatar anterior: {e}")

    serializer = UserUpdateSerializer(request.user, data=data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(UserSerializer(request.user).data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomTokenObtainPairView(TokenObtainPairView):
    pass

obtain_token = CustomTokenObtainPairView.as_view()