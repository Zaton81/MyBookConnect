from mybookconnect.html_sanitizer import sanitize_plain_text, sanitize_html
from rest_framework import serializers
from .club_models import (
    ReadingClub,
    ReadingClubMember,
    ReadingClubBook,
    ReadingClubDiscussion,
    ReadingClubDiscussionComment,
)
from .models import Book
from django.contrib.auth import get_user_model

User = get_user_model()


class ClubUserMiniSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'avatar_url']

    def get_avatar_url(self, obj) -> str | None:
        if hasattr(obj, 'avatar') and obj.avatar:
            try:
                return obj.avatar.url
            except Exception:
                return None
        return None


class ClubBookMiniSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.name', read_only=True)
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = ['id', 'title', 'author_name', 'cover_image_url', 'average_rating']

    def get_cover_image_url(self, obj) -> str | None:
        if hasattr(obj, 'cover') and obj.cover:
            try:
                return obj.cover.url
            except Exception:
                return None
        return None


class ReadingClubMemberSerializer(serializers.ModelSerializer):
    user = ClubUserMiniSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='user',
        write_only=True,
        required=False,
    )

    class Meta:
        model = ReadingClubMember
        fields = ['id', 'club', 'user', 'user_id', 'role', 'status', 'joined_at']
        read_only_fields = ['id', 'club', 'joined_at']


class ReadingClubBookSerializer(serializers.ModelSerializer):
    book = ClubBookMiniSerializer(read_only=True)
    book_id = serializers.PrimaryKeyRelatedField(
        queryset=Book.objects.all(),
        source='book',
        write_only=True,
    )

    class Meta:
        model = ReadingClubBook
        fields = [
            'id',
            'club',
            'book',
            'book_id',
            'status',
            'start_date',
            'end_date',
            'target_milestones',
            'created_at',
        ]
        read_only_fields = ['id', 'club', 'created_at']

    def validate_target_milestones(self, value):
        if value:
            return sanitize_plain_text(value)
        return value


class ReadingClubDiscussionCommentSerializer(serializers.ModelSerializer):
    author = ClubUserMiniSerializer(read_only=True)

    class Meta:
        model = ReadingClubDiscussionComment
        fields = [
            'id',
            'discussion',
            'author',
            'content',
            'has_spoilers',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'discussion', 'author', 'created_at', 'updated_at']

    def validate_content(self, value):
        cleaned = sanitize_plain_text(value.strip())
        if not cleaned:
            raise serializers.ValidationError("El comentario no puede estar vacío.")
        return cleaned


class ReadingClubDiscussionSerializer(serializers.ModelSerializer):
    author = ClubUserMiniSerializer(read_only=True)
    book = ClubBookMiniSerializer(read_only=True)
    book_id = serializers.PrimaryKeyRelatedField(
        queryset=Book.objects.all(),
        source='book',
        write_only=True,
        required=False,
        allow_null=True,
    )
    comments_count = serializers.SerializerMethodField()
    recent_comments = serializers.SerializerMethodField()

    class Meta:
        model = ReadingClubDiscussion
        fields = [
            'id',
            'club',
            'book',
            'book_id',
            'title',
            'content',
            'author',
            'is_pinned',
            'has_spoilers',
            'comments_count',
            'recent_comments',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'club', 'author', 'created_at', 'updated_at']

    def get_comments_count(self, obj) -> int:
        return obj.comments_count

    def get_recent_comments(self, obj):
        comments = obj.comments.select_related('author').order_by('created_at')[:5]
        return ReadingClubDiscussionCommentSerializer(comments, many=True).data

    def validate_title(self, value):
        cleaned = sanitize_plain_text(value.strip())
        if not cleaned:
            raise serializers.ValidationError("El título del debate no puede estar vacío.")
        return cleaned

    def validate_content(self, value):
        cleaned = sanitize_html(value.strip())
        if not cleaned:
            raise serializers.ValidationError("El contenido no puede estar vacío.")
        return cleaned


class ReadingClubListSerializer(serializers.ModelSerializer):
    creator = ClubUserMiniSerializer(read_only=True)
    current_book = ClubBookMiniSerializer(read_only=True)
    members_count = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()

    class Meta:
        model = ReadingClub
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'cover_image',
            'creator',
            'is_private',
            'current_book',
            'members_count',
            'is_member',
            'created_at',
        ]

    def get_members_count(self, obj) -> int:
        return getattr(obj, '_annotated_members_count', obj.members_count)

    def get_is_member(self, obj) -> bool:
        user = self.context.get('request').user if self.context.get('request') else None
        if user and user.is_authenticated:
            return obj.memberships.filter(user=user, status=ReadingClubMember.Status.ACTIVE).exists()
        return False


class ReadingClubDetailSerializer(serializers.ModelSerializer):
    creator = ClubUserMiniSerializer(read_only=True)
    current_book = ClubBookMiniSerializer(read_only=True)
    current_book_id = serializers.PrimaryKeyRelatedField(
        queryset=Book.objects.all(),
        source='current_book',
        write_only=True,
        required=False,
        allow_null=True,
    )
    members_count = serializers.SerializerMethodField()
    membership = serializers.SerializerMethodField()
    reading_plan = ReadingClubBookSerializer(many=True, read_only=True)

    class Meta:
        model = ReadingClub
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'cover_image',
            'creator',
            'is_private',
            'rules',
            'current_book',
            'current_book_id',
            'members_count',
            'membership',
            'reading_plan',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'slug', 'creator', 'created_at', 'updated_at']

    def get_members_count(self, obj) -> int:
        return obj.memberships.filter(status=ReadingClubMember.Status.ACTIVE).count()

    def get_membership(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        membership = obj.memberships.filter(user=request.user).first()
        if membership:
            return {
                'role': membership.role,
                'status': membership.status,
                'joined_at': membership.joined_at,
            }
        return None

    def validate_name(self, value):
        cleaned = sanitize_plain_text(value.strip())
        if not cleaned:
            raise serializers.ValidationError("El nombre del club no puede estar vacío.")
        return cleaned

    def validate_description(self, value):
        if value:
            return sanitize_html(value.strip())
        return value

    def validate_rules(self, value):
        if value:
            return sanitize_html(value.strip())
        return value
