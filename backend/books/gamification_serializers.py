from rest_framework import serializers

from books.gamification_models import (
    Badge,
    DailyReadingLog,
    ReadingChallenge,
    ReadingGoal,
    UserChallenge,
)


class ReadingGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadingGoal
        fields = ('id', 'year', 'target_books', 'target_pages', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_target_books(self, value):
        if value < 1:
            raise serializers.ValidationError("El objetivo anual debe ser de al menos 1 libro.")
        if value > 1000:
            raise serializers.ValidationError("El objetivo anual no puede superar los 1000 libros.")
        return value

    def validate_year(self, value):
        if value < 2000 or value > 2100:
            raise serializers.ValidationError("Año inválido para el objetivo de lectura.")
        return value


class DailyReadingLogSerializer(serializers.ModelSerializer):
    book_id = serializers.IntegerField(required=False, write_only=True, allow_null=True)

    class Meta:
        model = DailyReadingLog
        fields = ('id', 'date', 'pages_read', 'minutes_read', 'book_id', 'created_at')
        read_only_fields = ('id', 'created_at')

    def validate_pages_read(self, value):
        if value < 0:
            raise serializers.ValidationError("El número de páginas leídas no puede ser negativo.")
        return value

    def validate_minutes_read(self, value):
        if value < 0:
            raise serializers.ValidationError("Los minutos de lectura no pueden ser negativos.")
        return value


class BadgeSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    unlocked = serializers.BooleanField(default=False, read_only=True)
    awarded_at = serializers.DateTimeField(default=None, read_only=True, allow_null=True)

    class Meta:
        model = Badge
        fields = (
            'id',
            'slug',
            'name',
            'description',
            'icon',
            'category',
            'category_display',
            'points',
            'unlocked',
            'awarded_at',
        )


class ReadingChallengeSerializer(serializers.ModelSerializer):
    is_joined = serializers.SerializerMethodField()
    current_progress = serializers.SerializerMethodField()
    is_completed = serializers.SerializerMethodField()
    badge_reward_icon = serializers.CharField(source='badge_reward.icon', read_only=True, default=None)
    badge_reward_name = serializers.CharField(source='badge_reward.name', read_only=True, default=None)

    class Meta:
        model = ReadingChallenge
        fields = (
            'id',
            'slug',
            'title',
            'description',
            'challenge_type',
            'target_count',
            'start_date',
            'end_date',
            'is_active',
            'is_joined',
            'current_progress',
            'is_completed',
            'badge_reward_icon',
            'badge_reward_name',
        )

    def get_is_joined(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return UserChallenge.objects.filter(user=request.user, challenge=obj).exists()

    def get_current_progress(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
        uc = UserChallenge.objects.filter(user=request.user, challenge=obj).first()
        return uc.current_progress if uc else 0

    def get_is_completed(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        uc = UserChallenge.objects.filter(user=request.user, challenge=obj).first()
        return uc.is_completed if uc else False


class GamificationPreferenceSerializer(serializers.Serializer):
    gamification_enabled = serializers.BooleanField()
