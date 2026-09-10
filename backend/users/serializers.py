from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

User = get_user_model()

class UserBasicSerializer(serializers.ModelSerializer):
    """Serializador para información básica de usuario (para listados de amigos)"""
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'avatar', 'bio')
        read_only_fields = fields


class UserSerializer(serializers.ModelSerializer):
    birth_date = serializers.DateField(format='%Y-%m-%d', input_formats=['%Y-%m-%d'], required=False)
    reviews_count = serializers.SerializerMethodField()
    books_read_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    followers_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    is_blocked = serializers.SerializerMethodField()
    am_i_blocked = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'first_name', 'last_name', 'email', 'bio', 'avatar',
            'birth_date', 'location', 'privacy_level',
            'show_email', 'show_birth_date', 'show_location', 'show_bio',
            'following', 'followers', 'is_editor', 'is_staff', 'is_superuser',
            'reviews_count', 'books_read_count', 'following_count', 'followers_count',
            'is_following', 'is_blocked', 'am_i_blocked'
        )
        read_only_fields = ('id', 'followers', 'is_editor', 'is_staff', 'is_superuser')

    def get_reviews_count(self, obj):
        return getattr(obj, 'reviews_count', obj.reviews.count())

    def get_books_read_count(self, obj):
        if hasattr(obj, 'books_read_count'):
            return obj.books_read_count
        return obj.user_books.filter(is_read=True).count()

    def get_following_count(self, obj):
        return getattr(obj, 'following_count', obj.following.count())

    def get_followers_count(self, obj):
        return getattr(obj, 'followers_count', obj.followers.count())

    def get_is_following(self, obj):
        if hasattr(obj, 'is_following'):
            return obj.is_following
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user.following.filter(id=obj.id).exists()
        return False

    def get_is_blocked(self, obj):
        if hasattr(obj, 'is_blocked'):
            return obj.is_blocked
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user.blocked_users.filter(id=obj.id).exists()
        return False

    def get_am_i_blocked(self, obj):
        if hasattr(obj, 'am_i_blocked'):
            return obj.am_i_blocked
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.blocked_users.filter(id=request.user.id).exists()
        return False

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'password2', 'email', 'bio', 'first_name', 'last_name')

    email = serializers.EmailField(required=True, validators=[UniqueValidator(queryset=User.objects.all())])

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Las contraseñas no coinciden"})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


class NotificationSerializer(serializers.ModelSerializer):
    actor = UserBasicSerializer(read_only=True)

    class Meta:
        from .models import Notification
        model = Notification
        fields = ('id', 'type', 'title', 'message', 'link', 'read', 'created_at', 'actor')
        read_only_fields = ('id', 'type', 'title', 'message', 'link', 'created_at', 'actor')


class ActivityBookSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)
    author_name = serializers.CharField(source='author.name', default=None, read_only=True)
    cover = serializers.ImageField(read_only=True)
    average_rating = serializers.FloatField(read_only=True)


class ActivityReviewSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    rating = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)
    text = serializers.CharField(read_only=True)


class ActivitySerializer(serializers.ModelSerializer):
    user = UserBasicSerializer(read_only=True)
    target_user = UserBasicSerializer(read_only=True)
    book = ActivityBookSerializer(read_only=True)
    review = ActivityReviewSerializer(read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)

    class Meta:
        from .models import Activity
        model = Activity
        fields = (
            'id',
            'user',
            'type',
            'type_display',
            'book',
            'review',
            'target_user',
            'metadata',
            'created_at',
        )

