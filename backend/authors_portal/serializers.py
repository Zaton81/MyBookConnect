from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from books.media_utils import build_media_url

from .models import (
    AuthorAnnouncement,
    AuthorClaim,
    AuthorClaimStatus,
    AuthorEvent,
    AuthorEventAttendee,
    AuthorNewsletter,
    AuthorNewsletterIssue,
    AuthorNewsletterSubscriber,
    AuthorProfile,
)


class AuthorProfileSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    author_name = serializers.CharField(source='author.name', read_only=True, allow_null=True)

    class Meta:
        model = AuthorProfile
        fields = (
            'id',
            'user',
            'user_username',
            'author',
            'author_name',
            'pen_name',
            'bio',
            'website',
            'twitter',
            'instagram',
            'is_verified',
            'verification_notes',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'user', 'user_username', 'is_verified', 'created_at', 'updated_at')


class AuthorAnnouncementSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_photo = serializers.SerializerMethodField()
    book_title = serializers.CharField(source='book.title', read_only=True, allow_null=True)
    book_cover = serializers.SerializerMethodField()
    publication_type_display = serializers.CharField(source='get_publication_type_display', read_only=True)

    class Meta:
        model = AuthorAnnouncement
        fields = (
            'id',
            'author_profile',
            'author',
            'author_name',
            'author_photo',
            'book',
            'book_title',
            'book_cover',
            'title',
            'content',
            'excerpt',
            'publication_type',
            'publication_type_display',
            'has_spoilers',
            'spoiler_warning',
            'estimated_reading_time',
            'is_pinned',
            'is_draft',
            'is_paid',
            'price',
            'is_moderated',
            'moderation_reason',
            'moderated_at',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'author_profile',
            'author_name',
            'author_photo',
            'book_title',
            'book_cover',
            'publication_type_display',
            'is_moderated',
            'moderation_reason',
            'moderated_at',
            'created_at',
            'updated_at',
        )

    def get_author_name(self, obj) -> str:
        if obj.author:
            return obj.author.name
        if obj.author_profile.pen_name:
            return obj.author_profile.pen_name
        if obj.author_profile.author:
            return obj.author_profile.author.name
        return obj.author_profile.user.username

    def get_author_photo(self, obj):
        request = self.context.get('request')
        photo = None
        if obj.author and obj.author.photo:
            photo = obj.author.photo
        elif obj.author_profile and obj.author_profile.author and obj.author_profile.author.photo:
            photo = obj.author_profile.author.photo
        if photo:
            return build_media_url(photo, request=request)
        return None

    def get_book_cover(self, obj):
        request = self.context.get('request')
        if obj.book and obj.book.cover:
            return build_media_url(obj.book.cover, request=request)
        return None


class AuthorAnnouncementCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthorAnnouncement
        fields = (
            'id',
            'author',
            'book',
            'title',
            'content',
            'excerpt',
            'publication_type',
            'has_spoilers',
            'spoiler_warning',
            'estimated_reading_time',
            'is_pinned',
            'is_draft',
            'is_paid',
            'price',
            'is_moderated',
            'moderation_reason',
        )

    def validate(self, attrs):
        title = attrs.get('title')
        content = attrs.get('content')
        price = attrs.get('price')
        if title is not None and not title.strip():
            raise serializers.ValidationError({'title': 'El título no puede estar vacío.'})
        if content is not None and not content.strip():
            raise serializers.ValidationError({'content': 'El contenido no puede estar vacío.'})
        if price is not None and price < 0:
            raise serializers.ValidationError({'price': 'El precio no puede ser negativo.'})

        # Solo administradores o moderadores pueden alterar directamente el estado de moderación/censura
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        is_admin = user and (user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR'))
        if not is_admin:
            attrs.pop('is_moderated', None)
            attrs.pop('moderation_reason', None)

        return attrs


class AuthorClaimCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthorClaim
        fields = ('id', 'proof_description', 'contact_email', 'supporting_link')

    def validate(self, attrs):
        author = self.context.get('author')
        user = self.context.get('user')
        if not author:
            raise serializers.ValidationError('Autor no especificado.')
        if author.claimed_by is not None and author.claimed_by != user:
            raise serializers.ValidationError('Esta página de autor ya ha sido reclamada y verificada.')
        existing_pending = AuthorClaim.objects.filter(
            author=author,
            user=user,
            status=AuthorClaimStatus.PENDING,
        ).exists()
        if existing_pending:
            raise serializers.ValidationError('Ya tienes una solicitud de reclamación pendiente para este autor.')
        return attrs

    def create(self, validated_data):
        author = self.context['author']
        user = self.context['user']
        return AuthorClaim.objects.create(
            author=author,
            user=user,
            **validated_data
        )


class AuthorClaimAdminSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.name', read_only=True)
    author_id = serializers.IntegerField(source='author.id', read_only=True)
    author_photo = serializers.SerializerMethodField()
    username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = AuthorClaim
        fields = (
            'id', 'author_id', 'author_name', 'author_photo',
            'user', 'username', 'user_email', 'status',
            'proof_description', 'contact_email', 'supporting_link',
            'moderation_notes', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_author_photo(self, obj):
        request = self.context.get('request')
        if obj.author and obj.author.photo:
            return build_media_url(obj.author.photo, request=request)
        return None


class AuthorEventAttendeeSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_avatar = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = AuthorEventAttendee
        fields = (
            'id', 'event', 'user', 'username', 'user_avatar',
            'status', 'status_display', 'notes', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'status_display')

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_user_avatar(self, obj):
        request = self.context.get('request')
        avatar = getattr(obj.user, 'avatar', None)
        if avatar:
            return build_media_url(avatar, request=request)
        return None


class AuthorEventSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.name', read_only=True)
    author_photo = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    book_title = serializers.CharField(source='book.title', read_only=True, allow_null=True)
    book_cover = serializers.SerializerMethodField()
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    event_format_display = serializers.CharField(source='get_event_format_display', read_only=True)
    registered_count = serializers.IntegerField(read_only=True)
    waitlist_count = serializers.IntegerField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    user_registration_status = serializers.SerializerMethodField()
    is_user_registered = serializers.SerializerMethodField()
    user_notes = serializers.SerializerMethodField()

    class Meta:
        model = AuthorEvent
        fields = (
            'id', 'author', 'author_name', 'author_photo', 'author_profile',
            'created_by', 'created_by_username', 'book', 'book_title', 'book_cover',
            'title', 'description', 'event_type', 'event_type_display',
            'event_format', 'event_format_display', 'start_time', 'end_time',
            'event_timezone', 'location_name', 'location_address', 'online_url',
            'max_attendees', 'is_cancelled', 'registered_count', 'waitlist_count',
            'is_full', 'user_registration_status', 'is_user_registered', 'user_notes',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at')

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_author_photo(self, obj):
        request = self.context.get('request')
        if obj.author and obj.author.photo:
            return build_media_url(obj.author.photo, request=request)
        return None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_book_cover(self, obj):
        request = self.context.get('request')
        if obj.book and obj.book.cover:
            return build_media_url(obj.book.cover, request=request)
        return None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_user_registration_status(self, obj):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return None
        attendee = obj.attendees.filter(user=request.user).first()
        return attendee.status if attendee else None

    @extend_schema_field(serializers.BooleanField)
    def get_is_user_registered(self, obj):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        return obj.attendees.filter(user=request.user, status=AuthorEventAttendee.AttendeeStatus.REGISTERED).exists()

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_user_notes(self, obj):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return None
        attendee = obj.attendees.filter(user=request.user).first()
        return attendee.notes if attendee else None


class AuthorEventCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthorEvent
        fields = (
            'author', 'book', 'title', 'description',
            'event_type', 'event_format', 'start_time', 'end_time',
            'event_timezone', 'location_name', 'location_address',
            'online_url', 'max_attendees', 'is_cancelled'
        )

    def validate(self, attrs):
        start_time = attrs.get('start_time') or (self.instance.start_time if self.instance else None)
        end_time = attrs.get('end_time') if 'end_time' in attrs else (self.instance.end_time if self.instance else None)

        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError({"end_time": "La fecha y hora de finalización debe ser posterior al inicio."})

        request = self.context.get('request')
        author = attrs.get('author') or (self.instance.author if self.instance else None)
        if request and author:
            user = request.user
            is_claimed_owner = (author.claimed_by_id == user.id)
            is_profile_owner = hasattr(user, 'author_profile') and user.author_profile.author_id == author.id and user.author_profile.is_verified
            is_staff = user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
            if not (is_claimed_owner or is_profile_owner or is_staff):
                raise serializers.ValidationError({"author": "No tienes permisos para organizar eventos para este autor."})

        return attrs


class AuthorNewsletterSubscriberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_avatar = serializers.SerializerMethodField()

    class Meta:
        model = AuthorNewsletterSubscriber
        fields = (
            'id', 'newsletter', 'user', 'username', 'user_avatar',
            'is_active', 'subscribed_at', 'unsubscribed_at'
        )
        read_only_fields = ('id', 'subscribed_at', 'unsubscribed_at')

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_user_avatar(self, obj):
        request = self.context.get('request')
        avatar = getattr(obj.user, 'avatar', None)
        if avatar:
            return build_media_url(avatar, request=request)
        return None


class AuthorNewsletterIssueSerializer(serializers.ModelSerializer):
    newsletter_title = serializers.CharField(source='newsletter.title', read_only=True)
    author_name = serializers.CharField(source='newsletter.author.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = AuthorNewsletterIssue
        fields = (
            'id', 'newsletter', 'newsletter_title', 'author_name',
            'title', 'subject', 'content', 'status', 'status_display',
            'scheduled_for', 'sent_at', 'recipients_count', 'views_count',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'sent_at', 'recipients_count', 'views_count', 'created_at', 'updated_at')


class AuthorNewsletterIssueCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthorNewsletterIssue
        fields = (
            'id', 'newsletter', 'title', 'subject', 'content', 'status', 'scheduled_for',
            'sent_at', 'recipients_count', 'views_count', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'sent_at', 'recipients_count', 'views_count', 'created_at', 'updated_at')

    def validate(self, attrs):
        request = self.context.get('request')
        newsletter = attrs.get('newsletter') or (self.instance.newsletter if self.instance else None)
        if request and newsletter:
            user = request.user
            author = newsletter.author
            is_claimed_owner = (author.claimed_by_id == user.id)
            is_profile_owner = hasattr(user, 'author_profile') and user.author_profile.author_id == author.id and user.author_profile.is_verified
            is_staff = user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
            if not (is_claimed_owner or is_profile_owner or is_staff):
                raise serializers.ValidationError({"newsletter": "No tienes permisos para redactar o emitir boletines para este autor."})
        return attrs


class AuthorNewsletterSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.name', read_only=True)
    author_photo = serializers.SerializerMethodField()
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    active_subscribers_count = serializers.IntegerField(read_only=True)
    sent_issues_count = serializers.IntegerField(read_only=True)
    is_subscribed = serializers.SerializerMethodField()
    latest_issues = serializers.SerializerMethodField()

    class Meta:
        model = AuthorNewsletter
        fields = (
            'id', 'author', 'author_name', 'author_photo', 'author_profile',
            'title', 'description', 'frequency', 'frequency_display',
            'is_active', 'active_subscribers_count', 'sent_issues_count',
            'is_subscribed', 'latest_issues', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_author_photo(self, obj):
        request = self.context.get('request')
        if obj.author and obj.author.photo:
            return build_media_url(obj.author.photo, request=request)
        return None

    @extend_schema_field(serializers.BooleanField)
    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        return obj.subscribers.filter(user=request.user, is_active=True).exists()

    @extend_schema_field(AuthorNewsletterIssueSerializer(many=True))
    def get_latest_issues(self, obj):
        issues = obj.issues.filter(status=AuthorNewsletterIssue.IssueStatus.SENT)[:5]
        return AuthorNewsletterIssueSerializer(issues, many=True, context=self.context).data


class AuthorNewsletterCreateUpdateSerializer(serializers.ModelSerializer):
    active_subscribers_count = serializers.IntegerField(read_only=True)
    sent_issues_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = AuthorNewsletter
        fields = (
            'id', 'author', 'title', 'description', 'frequency', 'is_active',
            'active_subscribers_count', 'sent_issues_count', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'active_subscribers_count', 'sent_issues_count', 'created_at', 'updated_at')

    def validate(self, attrs):
        request = self.context.get('request')
        author = attrs.get('author') or (self.instance.author if self.instance else None)
        if request and author:
            user = request.user
            is_claimed_owner = (author.claimed_by_id == user.id)
            is_profile_owner = hasattr(user, 'author_profile') and user.author_profile.author_id == author.id and user.author_profile.is_verified
            is_staff = user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
            if not (is_claimed_owner or is_profile_owner or is_staff):
                raise serializers.ValidationError({"author": "No tienes permisos para configurar el boletín de este autor."})
        return attrs
