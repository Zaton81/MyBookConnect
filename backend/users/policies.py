from typing import Any, Optional

from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet

from users.models import PrivacyChoices

User = get_user_model()


def can_view_profile(viewer: Optional[Any], target: Any) -> bool:
    """
    Determina si `viewer` tiene permiso para ver el perfil de `target`.
    Reglas:
    - Mismo usuario: siempre True.
    - Staff/Superuser: siempre True.
    - Si target bloqueó a viewer: False.
    - Si viewer bloqueó a target: True (permite ver cabecera mínima y botón de desbloqueo).
    - Si viewer es anónimo: solo si target.privacy_level == PrivacyChoices.PUBLIC.
    - Privacidad target:
      - 'private': False.
      - 'friends': True solo si viewer sigue a target.
      - 'public': True.
    """
    if not target:
        return False
    if viewer and viewer.is_authenticated:
        if viewer.id == target.id or getattr(viewer, "is_staff", False) or getattr(viewer, "is_superuser", False):
            return True
        # Si target ha bloqueado a viewer -> Denegado
        if target.blocked_users.filter(id=viewer.id).exists():
            return False
        # Si viewer ha bloqueado a target -> Permitir ver para opción de desbloqueo
        if viewer.blocked_users.filter(id=target.id).exists():
            return True
        if target.privacy_level == PrivacyChoices.PRIVATE:
            return False
        if target.privacy_level == PrivacyChoices.FRIENDS:
            return viewer.following.filter(id=target.id).exists()
        return True
    else:
        return target.privacy_level == PrivacyChoices.PUBLIC


def can_view_review(viewer: Optional[Any], review: Any) -> bool:
    """
    Determina si `viewer` puede ver la reseña dada.
    Reglas:
    - Si review.user es el mismo que viewer: True.
    - Staff / Superuser: True.
    - Si viewer o review.user tienen un bloqueo mutuo o unidireccional: False.
    - Si review.user tiene perfil privado y viewer != review.user: False.
    - Si review.user tiene privacidad 'friends': True solo si viewer sigue a review.user.
    - Si review.user es 'public': True.
    """
    if not review or not getattr(review, "user", None):
        return False
    author = review.user
    if viewer and viewer.is_authenticated:
        if viewer.id == author.id or getattr(viewer, "is_staff", False) or getattr(viewer, "is_superuser", False):
            return True
        # Bloqueo mutuo o unidireccional oculta la reseña
        if author.blocked_users.filter(id=viewer.id).exists() or viewer.blocked_users.filter(id=author.id).exists():
            return False
        if author.privacy_level == PrivacyChoices.PRIVATE:
            return False
        if author.privacy_level == PrivacyChoices.FRIENDS:
            return viewer.following.filter(id=author.id).exists()
        return True
    else:
        return author.privacy_level == PrivacyChoices.PUBLIC


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
    """
    Determina si `user` puede enviar un mensaje a `target`.
    Reglas:
    - Ambos deben existir y user != target.
    - Ninguno de los dos debe tener bloqueado al otro.
    - Relación de seguimiento (user sigue a target o target sigue a user) o permisos de administración.
    """
    if not user or not user.is_authenticated or not target:
        return False
    if user.id == target.id:
        return False
    # Verificación de bloqueo bidireccional
    if user.blocked_users.filter(id=target.id).exists() or target.blocked_users.filter(id=user.id).exists():
        return False
    # Verificación de seguimiento: user sigue a target o target sigue a user
    is_following = user.following.filter(id=target.id).exists() or target.following.filter(id=user.id).exists()
    return is_following or getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)


def filter_visible_reviews(viewer: Optional[Any], queryset: QuerySet) -> QuerySet:
    """
    Filtra un queryset de Review para excluir reseñas según las políticas de privacidad:
    - Si el viewer es anónimo: solo reseñas de usuarios con perfil público.
    - Si el viewer está autenticado:
      - Excluye autores que el viewer haya bloqueado o que hayan bloqueado al viewer.
      - Excluye autores con perfil privado (salvo las propias reseñas del viewer).
      - Autores con perfil 'friends': solo si el viewer sigue al autor (o es el propio viewer).
    """
    if not viewer or not viewer.is_authenticated:
        return queryset.filter(user__privacy_level=PrivacyChoices.PUBLIC)

    blocked_by_viewer = viewer.blocked_users.values_list("id", flat=True)
    blocking_viewer = viewer.blocked_by.values_list("id", flat=True)
    excluded_user_ids = set(blocked_by_viewer).union(set(blocking_viewer))

    if excluded_user_ids:
        queryset = queryset.exclude(user_id__in=excluded_user_ids)

    following_ids = viewer.following.values_list("id", flat=True)

    privacy_condition = (
        Q(user=viewer)
        | Q(user__privacy_level=PrivacyChoices.PUBLIC)
        | (Q(user__privacy_level=PrivacyChoices.FRIENDS) & Q(user_id__in=following_ids))
    )

    return queryset.filter(privacy_condition)


def filter_visible_users(viewer: Optional[Any], queryset: QuerySet) -> QuerySet:
    """
    Filtra un queryset de User para listados y búsquedas:
    - Excluye usuarios inactivos si el viewer no es staff.
    - Si el viewer está autenticado:
      - Excluye a los usuarios que el viewer haya bloqueado y a los que hayan bloqueado al viewer.
    """
    if not viewer or not getattr(viewer, "is_staff", False):
        queryset = queryset.filter(is_active=True)

    if viewer and viewer.is_authenticated:
        blocked_by_viewer = viewer.blocked_users.values_list("id", flat=True)
        blocking_viewer = viewer.blocked_by.values_list("id", flat=True)
        excluded_ids = set(blocked_by_viewer).union(set(blocking_viewer))
        if excluded_ids:
            queryset = queryset.exclude(id__in=excluded_ids)

    return queryset
