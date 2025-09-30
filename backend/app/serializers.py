from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'birth_date', 'location', 'privacy_level', 'avatar')
        read_only_fields = ('id',)

class UserUpdateSerializer(serializers.ModelSerializer):
    birth_date = serializers.DateField(required=False)
    location = serializers.CharField(required=False, allow_blank=True)
    privacy_level = serializers.ChoiceField(choices=User.PRIVACY_CHOICES, required=False)
    avatar = serializers.ImageField(required=False)

    class Meta:
        model = User
        fields = ('birth_date', 'location', 'privacy_level', 'avatar')