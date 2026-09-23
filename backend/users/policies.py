from typing import Any, Optional

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from users.privacy_service import PrivacyService

User = get_user_model()


def are_mutually_blocked(user_a: Optional[Any], user_b: Optional[Any]) -> bool:
    return PrivacyService.are_mutually_blocked(user_a, user_b)


def can_view_profile(viewer: Optional[Any], target: Any) -> bool:
    return PrivacyService.can_view_profile(viewer, target)


def can_view_reading_activity(viewer: Optional[Any], target: Any) -> bool:
    return PrivacyService.can_view_reading_activity(viewer, target)


def can_view_activity(viewer: Optional[Any], target: Any) -> bool:
    return PrivacyService.can_view_activity(viewer, target)


def apply_profile_field_visibility(viewer: Optional[Any], target: Any, data_dict: dict) -> dict:
    return PrivacyService.apply_profile_field_visibility(viewer, target, data_dict)


def can_view_review(viewer: Optional[Any], review: Any) -> bool:
    return PrivacyService.can_view_review(viewer, review)


def can_view_list(viewer: Optional[Any], reading_list: Any) -> bool:
    return PrivacyService.can_view_list(viewer, reading_list)


def can_view_followers(viewer: Optional[Any], target: Any) -> bool:
    return PrivacyService.can_view_followers(viewer, target)


def can_view_following(viewer: Optional[Any], target: Any) -> bool:
    return PrivacyService.can_view_following(viewer, target)


def can_view_statistics(viewer: Optional[Any], target: Any) -> bool:
    return PrivacyService.can_view_statistics(viewer, target)


def can_match(viewer: Optional[Any], target: Any) -> bool:
    return PrivacyService.can_match(viewer, target)


def can_recommend(viewer: Optional[Any], target: Any) -> bool:
    return PrivacyService.can_recommend(viewer, target)


def can_interact(viewer: Optional[Any], target: Any) -> bool:
    return PrivacyService.can_interact(viewer, target)


def can_edit_review(user: Optional[Any], review: Any) -> bool:
    """
    Determina si `user` puede editar o eliminar `review`.
    Solo el autor original, staff o superuser pueden modificarla.
    """
    if not user or not user.is_authenticated or not review:
        return False
    return (
        review.user_id == user.id
        or getattr(user, "is_staff", False)
        or getattr(user, "is_superuser", False)
    )


def can_access_conversation(user: Optional[Any], conversation: Any) -> bool:
    """
    Determina si `user` tiene acceso de lectura/escritura a la conversación dada.
    Debe estar autenticado y ser participante.
    """
    if not user or not user.is_authenticated or not conversation:
        return False
    return conversation.participants.filter(id=user.id).exists()


def can_message(user: Optional[Any], target: Any) -> bool:
    return PrivacyService.can_message(user, target)


def can_moderate(user: Optional[Any]) -> bool:
    return PrivacyService.can_moderate(user)


def can_edit_catalog(user: Optional[Any]) -> bool:
    """
    Determina si un usuario tiene permisos editoriales para modificar libros, autores o erratas.
    Aplica a roles EDITOR, MODERATOR, ADMIN, usuarios con is_editor=True, o staff/superuser.
    """
    if not user or not user.is_authenticated:
        return False
    from users.models import UserRole
    user_role = getattr(user, "role", UserRole.USER)
    return (
        user_role in (UserRole.EDITOR, UserRole.MODERATOR, UserRole.ADMIN)
        or getattr(user, "is_editor", False)
        or getattr(user, "is_staff", False)
        or getattr(user, "is_superuser", False)
    )


def is_user_muted_by_moderation(user: Optional[Any]) -> bool:
    return PrivacyService.is_user_muted_by_moderation(user)


def filter_visible_reviews(viewer: Optional[Any], queryset: QuerySet) -> QuerySet:
    return PrivacyService.filter_visible_reviews(viewer, queryset)


def filter_visible_users(viewer: Optional[Any], queryset: QuerySet) -> QuerySet:
    return PrivacyService.filter_visible_users(viewer, queryset)


def filter_visible_activities(viewer: Optional[Any], queryset: QuerySet) -> QuerySet:
    return PrivacyService.filter_visible_activities(viewer, queryset)


def filter_visible_reading_lists(viewer: Optional[Any], queryset: QuerySet) -> QuerySet:
    return PrivacyService.filter_visible_reading_lists(viewer, queryset)


def filter_visible_user_books(viewer: Optional[Any], queryset: QuerySet) -> QuerySet:
    return PrivacyService.filter_visible_user_books(viewer, queryset)
