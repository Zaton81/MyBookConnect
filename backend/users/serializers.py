from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from mybookconnect.html_sanitizer import sanitize_html, sanitize_plain_text

User = get_user_model()

class UserBasicSerializer(serializers.ModelSerializer):
    """Serializador para información básica de usuario (para listados de amigos)"""
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'avatar', 'bio')
        read_only_fields = fields

    def to_representation(self, instance):
        """Normaliza la URL pública del avatar."""
        ret = super().to_representation(instance)
        request = self.context.get('request') if hasattr(self, 'context') else None
        from books.media_utils import build_media_url
        if instance.avatar:
            ret['avatar'] = build_media_url(instance.avatar, request=request)
        return ret


class UserSerializer(serializers.ModelSerializer):
    birth_date = serializers.DateField(format='%Y-%m-%d', input_formats=['%Y-%m-%d'], required=False)
    reviews_count = serializers.SerializerMethodField()
    books_read_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    followers_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    is_blocked = serializers.SerializerMethodField()
    am_i_blocked = serializers.SerializerMethodField()
    is_muted = serializers.SerializerMethodField()
    is_disciplinary_muted = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'first_name', 'last_name', 'email', 'is_email_verified', 'bio', 'avatar',
            'birth_date', 'location', 'privacy_level',
            'show_email', 'show_birth_date', 'show_location', 'show_bio',
            'following', 'followers', 'is_editor', 'is_staff', 'is_superuser', 'role',
            'reviews_count', 'books_read_count', 'following_count', 'followers_count',
            'is_following', 'is_blocked', 'am_i_blocked', 'is_muted', 'is_disciplinary_muted', 'muted_until'
        )
        read_only_fields = ('id', 'followers', 'is_editor', 'is_staff', 'is_superuser', 'role', 'is_email_verified', 'muted_until')

    def validate_avatar(self, value):
        """
        Valida y sanitiza el avatar de usuario.
        Asegura formato permitido, dimensiones, cuota <= 5MB y elimina metadatos EXIF.
        """
        if not value:
            return value
        from django.core.exceptions import ValidationError as DjangoValidationError

        from mybookconnect.media_security import AVATAR_PRESET, sanitize_image, validate_avatar_image

        try:
            validate_avatar_image(value)
            return sanitize_image(value, max_dimensions=AVATAR_PRESET)
        except DjangoValidationError as err:
            msg = err.messages if hasattr(err, 'messages') else str(err)
            raise serializers.ValidationError(msg) from err

    def validate_bio(self, value):
        from mybookconnect.html_sanitizer import sanitize_html
        return sanitize_html(value)

    def validate_location(self, value):
        from mybookconnect.html_sanitizer import sanitize_plain_text
        return sanitize_plain_text(value)

    def validate_first_name(self, value):
        from mybookconnect.html_sanitizer import sanitize_plain_text
        return sanitize_plain_text(value)

    def validate_last_name(self, value):
        from mybookconnect.html_sanitizer import sanitize_plain_text
        return sanitize_plain_text(value)

    def to_representation(self, instance):
        """Normaliza la URL pública del avatar."""
        ret = super().to_representation(instance)
        request = self.context.get('request') if hasattr(self, 'context') else None
        from books.media_utils import build_media_url
        if instance.avatar:
            ret['avatar'] = build_media_url(instance.avatar, request=request)
        return ret

    @extend_schema_field(serializers.IntegerField)
    def get_reviews_count(self, obj):
        return getattr(obj, 'reviews_count', obj.reviews.filter(deleted_at__isnull=True, is_moderated=False).count())

    @extend_schema_field(serializers.IntegerField)
    def get_books_read_count(self, obj):
        if hasattr(obj, 'books_read_count'):
            return obj.books_read_count
        return obj.user_books.filter(is_read=True).count()

    @extend_schema_field(serializers.IntegerField)
    def get_following_count(self, obj):
        return getattr(obj, 'following_count', obj.following.count())

    @extend_schema_field(serializers.IntegerField)
    def get_followers_count(self, obj):
        return getattr(obj, 'followers_count', obj.followers.count())

    @extend_schema_field(serializers.BooleanField)
    def get_is_following(self, obj):
        if hasattr(obj, 'is_following'):
            return obj.is_following
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user.following.filter(id=obj.id).exists()
        return False

    @extend_schema_field(serializers.BooleanField)
    def get_is_blocked(self, obj):
        if hasattr(obj, 'is_blocked'):
            return obj.is_blocked
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user.blocked_users.filter(id=obj.id).exists()
        return False

    @extend_schema_field(serializers.BooleanField)
    def get_am_i_blocked(self, obj):
        if hasattr(obj, 'am_i_blocked'):
            return obj.am_i_blocked
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.blocked_users.filter(id=request.user.id).exists()
        return False

    @extend_schema_field(serializers.BooleanField)
    def get_is_muted(self, obj):
        if hasattr(obj, 'is_muted_val'):
            return obj.is_muted_val
        request = self.context.get('request')
        if request and request.user.is_authenticated and hasattr(request.user, 'muted_users'):
            return request.user.muted_users.filter(id=obj.id).exists()
        return False

    @extend_schema_field(serializers.BooleanField)
    def get_is_disciplinary_muted(self, obj):
        return getattr(obj, 'is_disciplinary_muted', False)

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
        temp_user = User(
            username=attrs.get('username'),
            email=attrs.get('email'),
            first_name=attrs.get('first_name'),
            last_name=attrs.get('last_name'),
        )
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            validate_password(attrs['password'], user=temp_user)
        except DjangoValidationError as err:
            raise serializers.ValidationError({"password": list(err.messages)}) from err
        attrs['bio'] = sanitize_html(attrs.get('bio', ''))
        if attrs.get('first_name'):
            attrs['first_name'] = sanitize_plain_text(attrs['first_name'])
        if attrs.get('last_name'):
            attrs['last_name'] = sanitize_plain_text(attrs['last_name'])
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


class NotificationCreateSerializer(serializers.ModelSerializer):
    recipient_id = serializers.IntegerField(required=False, allow_null=True)
    type = serializers.CharField(required=False, default='SYSTEM')

    class Meta:
        from .models import Notification
        model = Notification
        fields = ('id', 'recipient_id', 'type', 'title', 'message', 'link')

    def validate_type(self, value):
        from .models import NotificationType

        if not value:
            return NotificationType.SYSTEM
        val_upper = str(value).upper().strip()
        if val_upper in NotificationType.values:
            return val_upper
        raise serializers.ValidationError(f"'{value}' no es un tipo de notificación válido.")

    def create(self, validated_data):
        from .models import Notification, NotificationType, User
        recipient_id = validated_data.pop('recipient_id', None)
        request = self.context.get('request')
        actor = request.user if request and request.user.is_authenticated else None

        if recipient_id:
            recipient = User.objects.filter(id=recipient_id).first()
            if not recipient:
                raise serializers.ValidationError({'recipient_id': 'El usuario destinatario no existe.'})
        else:
            recipient = actor

        notif_type = validated_data.get('type', NotificationType.SYSTEM)
        return Notification.objects.create(
            recipient=recipient,
            actor=actor,
            type=notif_type,
            title=validated_data.get('title', ''),
            message=validated_data.get('message', ''),
            link=validated_data.get('link', ''),
        )



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
    score = serializers.SerializerMethodField()
    feed_signal = serializers.SerializerMethodField()
    timestamp = serializers.DateTimeField(source='created_at', read_only=True)

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
            'score',
            'feed_signal',
            'created_at',
            'timestamp',
        )

    def get_score(self, obj):
        return getattr(obj, 'score', None)

    def get_feed_signal(self, obj):
        return getattr(obj, 'feed_signal', None)


class PasswordChangeSerializer(serializers.Serializer):
    """Serializador para cambio de contraseña por usuario autenticado."""
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    new_password2 = serializers.CharField(write_only=True, required=True)
    revoke_other_sessions = serializers.BooleanField(default=True, required=False)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("La contraseña actual no es correcta.")
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({"new_password": "Las nuevas contraseñas no coinciden."})
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError({"new_password": "La nueva contraseña debe ser distinta a la anterior."})
        user = self.context['request'].user
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            validate_password(attrs['new_password'], user=user)
        except DjangoValidationError as err:
            raise serializers.ValidationError({"new_password": list(err.messages)}) from err
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializador para solicitar el restablecimiento de contraseña vía email."""
    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializador para confirmar el cambio de contraseña con token efímero."""
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    new_password2 = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({"new_password": "Las contraseñas no coinciden."})
        return attrs


class EmailVerifyConfirmSerializer(serializers.Serializer):
    """Serializador para validación de token de confirmación de email."""
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)


class GoogleOAuthSerializer(serializers.Serializer):
    """Serializador para autenticación social con credenciales de Google OAuth."""
    id_token = serializers.CharField(required=True, help_text="Token JWT provisto por Google Sign-In SDK")


