from typing import Any, Optional

from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet
from django.utils import timezone

from users.models import MessagePrivacyChoices, PrivacyChoices

User = get_user_model()


class PrivacyService:
    """
    Servicio centralizado y reutilizable para la evaluación de políticas de privacidad,
    visibilidad de perfiles y recursos, y bloqueos bidireccionales (Fase 2 — Privacy Core).
    """

    @classmethod
    def are_mutually_blocked(cls, user_a: Optional[Any], user_b: Optional[Any]) -> bool:
        """
        Determina si existe un bloqueo activo en cualquiera de las dos direcciones:
        - user_a bloquea a user_b
        - user_b bloquea a user_a
        Retorna False si alguno de los dos usuarios es nulo o anónimo.
        """
        if not user_a or not user_b:
            return False
        if not getattr(user_a, "is_authenticated", False) or not getattr(user_b, "is_authenticated", False):
            return False
        if user_a.id == user_b.id:
            return False

        a_blocks_b = user_a.blocked_users.filter(id=user_b.id).exists()
        b_blocks_a = user_b.blocked_users.filter(id=user_a.id).exists()
        return a_blocks_b or b_blocks_a

    @classmethod
    def can_view_profile(cls, viewer: Optional[Any], target: Any) -> bool:
        """
        Determina si `viewer` tiene permiso para ver el perfil de `target`.
        Reglas:
        - Target inexistente -> False.
        - Mismo usuario -> True.
        - Staff / Superuser -> True.
        - Si target bloqueó a viewer -> False.
        - Si viewer bloqueó a target -> True (permite ver cabecera mínima y botón de desbloqueo).
        - Si target no está activo -> False (salvo staff).
        - Si viewer es anónimo -> solo si target.privacy_level == PrivacyChoices.PUBLIC.
        - Si viewer es autenticado:
          - 'private': False.
          - 'friends': True solo si viewer sigue a target.
          - 'public': True.
        """
        if not target:
            return False
        if not getattr(target, "is_active", True):
            return bool(viewer and (getattr(viewer, "is_staff", False) or getattr(viewer, "is_superuser", False)))

        if viewer and getattr(viewer, "is_authenticated", False):
            if viewer.id == target.id or getattr(viewer, "is_staff", False) or getattr(viewer, "is_superuser", False):
                return True
            # Si target ha bloqueado a viewer -> denegado
            if target.blocked_users.filter(id=viewer.id).exists():
                return False
            # Si viewer ha bloqueado a target -> permitir ver cabecera para opción de desbloqueo
            if viewer.blocked_users.filter(id=target.id).exists():
                return True
            if target.privacy_level == PrivacyChoices.PRIVATE:
                return False
            if target.privacy_level == PrivacyChoices.FRIENDS:
                return viewer.following.filter(id=target.id).exists()
            return True
        else:
            return target.privacy_level == PrivacyChoices.PUBLIC

    @classmethod
    def can_view_reading_activity(cls, viewer: Optional[Any], target: Any) -> bool:
        """
        Determina si `viewer` puede ver el historial o estantería de lectura de `target`.
        Reglas:
        - Mismo usuario o staff -> True.
        - Bloqueo bidireccional -> False.
        - Target no activo -> False (salvo staff).
        - Techo máximo: privacy_level del perfil. Si es PRIVATE, la lectura es PRIVATE.
        - Si el perfil es FRIENDS: la lectura es FRIENDS como máximo.
        - reading_privacy_level: PUBLIC, FRIENDS, PRIVATE.
        """
        if not target:
            return False
        if viewer and getattr(viewer, "is_authenticated", False):
            if viewer.id == target.id or getattr(viewer, "is_staff", False) or getattr(viewer, "is_superuser", False):
                return True
            if cls.are_mutually_blocked(viewer, target):
                return False
            if not getattr(target, "is_active", True):
                return False

            effective_privacy = target.privacy_level
            if effective_privacy == PrivacyChoices.PRIVATE:
                return False

            reading_privacy = getattr(target, "reading_privacy_level", PrivacyChoices.PUBLIC)
            if reading_privacy == PrivacyChoices.PRIVATE:
                return False

            if effective_privacy == PrivacyChoices.FRIENDS or reading_privacy == PrivacyChoices.FRIENDS:
                return viewer.following.filter(id=target.id).exists()

            return True
        else:
            if not getattr(target, "is_active", True):
                return False
            if target.privacy_level != PrivacyChoices.PUBLIC:
                return False
            reading_privacy = getattr(target, "reading_privacy_level", PrivacyChoices.PUBLIC)
            return reading_privacy == PrivacyChoices.PUBLIC

    @classmethod
    def can_view_activity(cls, viewer: Optional[Any], target: Any) -> bool:
        """
        Determina si `viewer` puede ver la actividad social (feed) de `target`.
        """
        if not target:
            return False
        if viewer and getattr(viewer, "is_authenticated", False):
            if viewer.id == target.id or getattr(viewer, "is_staff", False) or getattr(viewer, "is_superuser", False):
                return True
            if cls.are_mutually_blocked(viewer, target):
                return False
            if not getattr(target, "is_active", True):
                return False

            effective_privacy = target.privacy_level
            if effective_privacy == PrivacyChoices.PRIVATE:
                return False

            activity_privacy = getattr(target, "activity_privacy_level", PrivacyChoices.PUBLIC)
            if activity_privacy == PrivacyChoices.PRIVATE:
                return False

            if effective_privacy == PrivacyChoices.FRIENDS or activity_privacy == PrivacyChoices.FRIENDS:
                return viewer.following.filter(id=target.id).exists()

            return True
        else:
            if not getattr(target, "is_active", True):
                return False
            if target.privacy_level != PrivacyChoices.PUBLIC:
                return False
            activity_privacy = getattr(target, "activity_privacy_level", PrivacyChoices.PUBLIC)
            return activity_privacy == PrivacyChoices.PUBLIC

    @classmethod
    def can_view_review(cls, viewer: Optional[Any], review: Any) -> bool:
        """
        Determina si `viewer` puede ver la reseña dada.
        Reglas:
        - Reseña inexistente o sin autor -> False.
        - Reseña eliminada lógicamente -> solo staff/superuser.
        - Reseña moderada (is_moderated) -> solo moderadores o staff.
        - Autor es el viewer o staff/superuser -> True.
        - Bloqueo bidireccional entre viewer y autor -> False.
        - Autor no activo -> False (salvo staff).
        - Si viewer es anónimo: solo si author.privacy_level == PrivacyChoices.PUBLIC.
        - Si viewer está autenticado:
          - 'private': False.
          - 'friends': True solo si viewer sigue a author.
          - 'public': True.
        """
        if not review or not getattr(review, "user", None):
            return False
        author = review.user

        # Eliminación lógica
        if getattr(review, "deleted_at", None) is not None or getattr(review, "is_deleted", False):
            if not (viewer and getattr(viewer, "is_authenticated", False) and (getattr(viewer, "is_staff", False) or getattr(viewer, "is_superuser", False))):
                return False

        # Moderación
        if getattr(review, "is_moderated", False):
            if not cls.can_moderate(viewer):
                return False

        if viewer and getattr(viewer, "is_authenticated", False):
            if viewer.id == author.id or getattr(viewer, "is_staff", False) or getattr(viewer, "is_superuser", False):
                return True
            if cls.are_mutually_blocked(viewer, author):
                return False
            if not getattr(author, "is_active", True):
                return False
            if author.privacy_level == PrivacyChoices.PRIVATE:
                return False
            if author.privacy_level == PrivacyChoices.FRIENDS:
                return viewer.following.filter(id=author.id).exists()
            return True
        else:
            if not getattr(author, "is_active", True):
                return False
            return author.privacy_level == PrivacyChoices.PUBLIC

    @classmethod
    def can_view_list(cls, viewer: Optional[Any], reading_list: Any) -> bool:
        """
        Determina si `viewer` tiene acceso para ver la lista de lectura `reading_list`.
        Reglas:
        - Lista inexistente -> False.
        - Creador o staff/superuser -> True.
        - Bloqueo bidireccional entre creador y visor -> False.
        - Creador inactivo -> False (salvo staff).
        - Privacidad de la lista:
          - 'private': False.
          - 'followers': True solo si viewer está autenticado y sigue al creador.
          - 'public': True, siempre que el perfil del creador no esté en 'private'.
        """
        if not reading_list or not getattr(reading_list, "user", None):
            return False
        creator = reading_list.user

        if viewer and getattr(viewer, "is_authenticated", False):
            if viewer.id == creator.id or getattr(viewer, "is_staff", False) or getattr(viewer, "is_superuser", False):
                return True
            if cls.are_mutually_blocked(viewer, creator):
                return False
            if not getattr(creator, "is_active", True):
                return False

            list_privacy = getattr(reading_list, "privacy", "public")
            if list_privacy == "private":
                return False
            if list_privacy == "followers":
                return viewer.following.filter(id=creator.id).exists()
            # list_privacy == 'public'
            if creator.privacy_level == PrivacyChoices.PRIVATE:
                return False
            return True
        else:
            if not getattr(creator, "is_active", True):
                return False
            list_privacy = getattr(reading_list, "privacy", "public")
            if list_privacy != "public":
                return False
            return creator.privacy_level == PrivacyChoices.PUBLIC

    @classmethod
    def can_view_followers(cls, viewer: Optional[Any], target: Any) -> bool:
        """Determina si `viewer` puede ver la lista de seguidores de `target`."""
        return cls.can_view_profile(viewer, target)

    @classmethod
    def can_view_following(cls, viewer: Optional[Any], target: Any) -> bool:
        """Determina si `viewer` puede ver los usuarios seguidos por `target`."""
        return cls.can_view_profile(viewer, target)

    @classmethod
    def can_view_statistics(cls, viewer: Optional[Any], target: Any) -> bool:
        """Determina si `viewer` puede ver las estadísticas de lectura de `target`."""
        return cls.can_view_reading_activity(viewer, target)

    @classmethod
    def can_match(cls, viewer: Optional[Any], target: Any) -> bool:
        """
        Determina si `viewer` puede calcular afinidad lectora (Reading Match) con `target`.
        Reglas:
        - Ambos deben ser usuarios válidos y autenticados.
        - Mismo usuario -> True (match consigo mismo = 100%).
        - Bloqueo bidireccional -> False.
        - Target inactivo -> False.
        - Si la biblioteca de target no es visible para viewer -> False.
        """
        if not viewer or not getattr(viewer, "is_authenticated", False) or not target:
            return False
        if viewer.id == target.id:
            return True
        if getattr(viewer, "is_staff", False) or getattr(viewer, "is_superuser", False):
            return True
        if cls.are_mutually_blocked(viewer, target):
            return False
        if not getattr(target, "is_active", True):
            return False
        return cls.can_view_reading_activity(viewer, target)

    @classmethod
    def can_recommend(cls, viewer: Optional[Any], target: Any) -> bool:
        """
        Determina si los datos de `target` pueden ser usados para generar recomendaciones
        o sugerencias sociales (lectores afines) para `viewer`.
        """
        if not viewer or not target or viewer.id == target.id:
            return False
        if cls.are_mutually_blocked(viewer, target):
            return False
        if not getattr(target, "is_active", True):
            return False
        return cls.can_view_reading_activity(viewer, target)

    @classmethod
    def can_interact(cls, viewer: Optional[Any], target: Any) -> bool:
        """
        Determina si `viewer` puede interactuar socialmente (seguir, likear, comentar) con `target`.
        """
        if not viewer or not getattr(viewer, "is_authenticated", False) or not target:
            return False
        if viewer.id == target.id:
            return False
        if cls.are_mutually_blocked(viewer, target):
            return False
        if not getattr(target, "is_active", True):
            return False
        if cls.is_user_muted_by_moderation(viewer):
            return False
        return True

    @classmethod
    def can_message(cls, user: Optional[Any], target: Any) -> bool:
        """
        Determina si `user` puede enviar un mensaje directo a `target`.
        Reglas:
        - Ambos deben ser autenticados y user != target.
        - Bloqueo bidireccional -> False.
        - Target inactivo -> False.
        - User silenciado por moderación -> False.
        - Staff / superusuario -> True.
        - Política allow_messages_from de target:
          - NOBODY -> False.
          - EVERYONE -> True.
          - FOLLOWED -> True si target sigue a user o user sigue a target.
        """
        if not user or not getattr(user, "is_authenticated", False) or not target:
            return False
        if user.id == target.id:
            return False
        if cls.are_mutually_blocked(user, target):
            return False
        if not getattr(target, "is_active", True):
            return False
        if cls.is_user_muted_by_moderation(user):
            return False

        if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
            return True

        target_policy = getattr(target, "allow_messages_from", MessagePrivacyChoices.FOLLOWED)
        if target_policy == MessagePrivacyChoices.NOBODY:
            return False

        if target_policy == MessagePrivacyChoices.EVERYONE:
            return True

        # FOLLOWED: target sigue a user o user sigue a target
        is_following = user.following.filter(id=target.id).exists() or target.following.filter(id=user.id).exists()
        return is_following

    @classmethod
    def can_moderate(cls, user: Optional[Any]) -> bool:
        """Determina si un usuario tiene permisos de moderación o administración."""
        if not user or not getattr(user, "is_authenticated", False):
            return False
        from users.models import UserRole
        user_role = getattr(user, "role", UserRole.USER)
        return (
            user_role in (UserRole.MODERATOR, UserRole.ADMIN)
            or getattr(user, "is_staff", False)
            or getattr(user, "is_superuser", False)
        )

    @classmethod
    def is_user_muted_by_moderation(cls, user: Optional[Any]) -> bool:
        """Determina si un usuario se encuentra bajo sanción activa de silenciamiento."""
        if not user or not getattr(user, "is_authenticated", False):
            return False
        muted_until = getattr(user, "muted_until", None)
        if not muted_until:
            return False
        return muted_until > timezone.now()

    @classmethod
    def apply_profile_field_visibility(cls, viewer: Optional[Any], target: Any, data_dict: dict) -> dict:
        """
        Ofusca o redacta campos sensibles en la representación serializada de un usuario
        según las preferencias de privacidad del usuario y los permisos del visor.
        """
        data = dict(data_dict)
        is_self = viewer and getattr(viewer, "is_authenticated", False) and viewer.id == target.id
        is_staff = viewer and getattr(viewer, "is_authenticated", False) and (
            getattr(viewer, "is_staff", False) or getattr(viewer, "is_superuser", False)
        )

        if is_self or is_staff:
            return data

        # Ocultar campos internos de configuración de privacidad a terceros
        private_settings_fields = [
            "reading_privacy_level",
            "activity_privacy_level",
            "allow_messages_from",
            "show_email",
            "show_birth_date",
            "show_location",
            "show_bio",
        ]
        for f in private_settings_fields:
            data.pop(f, None)

        # Reglas por campo
        target_privacy = getattr(target, "privacy_level", PrivacyChoices.PUBLIC)

        # Email
        if not (getattr(target, "show_email", False) and target_privacy == PrivacyChoices.PUBLIC):
            data["email"] = ""

        # Fecha de nacimiento
        if not (getattr(target, "show_birth_date", False) and target_privacy == PrivacyChoices.PUBLIC):
            data["birth_date"] = None

        # Ubicación
        if not (getattr(target, "show_location", True) and target_privacy == PrivacyChoices.PUBLIC):
            data["location"] = ""

        # Biografía
        if not (getattr(target, "show_bio", True) and target_privacy == PrivacyChoices.PUBLIC):
            data["bio"] = ""

        # Estadísticas de lectura
        if not cls.can_view_statistics(viewer, target):
            data["books_read_count"] = 0
            data["reviews_count"] = 0

        # Listas de seguidores / seguidos
        if not cls.can_view_followers(viewer, target):
            data["followers"] = []
            data["followers_count"] = 0

        if not cls.can_view_following(viewer, target):
            data["following"] = []
            data["following_count"] = 0

        return data

    # --- Métodos de Filtrado de QuerySets ---

    @classmethod
    def filter_visible_users(cls, viewer: Optional[Any], queryset: QuerySet) -> QuerySet:
        """
        Filtra un queryset de usuarios:
        - Excluye usuarios inactivos (salvo staff).
        - Si el visor está autenticado, excluye usuarios bloqueados y bloqueadores.
        """
        if not viewer or not getattr(viewer, "is_staff", False):
            queryset = queryset.filter(is_active=True)

        if viewer and getattr(viewer, "is_authenticated", False):
            blocked_by_viewer = viewer.blocked_users.values_list("id", flat=True)
            blocking_viewer = viewer.blocked_by.values_list("id", flat=True)
            excluded_ids = set(blocked_by_viewer).union(set(blocking_viewer))
            if excluded_ids:
                queryset = queryset.exclude(id__in=excluded_ids)

        return queryset

    @classmethod
    def filter_visible_reviews(cls, viewer: Optional[Any], queryset: QuerySet) -> QuerySet:
        """
        Filtra un queryset de Review para excluir reseñas según privacidad y moderación.
        """
        queryset = queryset.filter(deleted_at__isnull=True)

        if not cls.can_moderate(viewer):
            queryset = queryset.filter(is_moderated=False)

        # Excluir autores inactivos
        if not viewer or not getattr(viewer, "is_staff", False):
            queryset = queryset.filter(user__is_active=True)

        if not viewer or not getattr(viewer, "is_authenticated", False):
            return queryset.filter(user__privacy_level=PrivacyChoices.PUBLIC)

        blocked_by_viewer = viewer.blocked_users.values_list("id", flat=True)
        blocking_viewer = viewer.blocked_by.values_list("id", flat=True)
        muted_by_viewer = viewer.muted_users.values_list("id", flat=True) if hasattr(viewer, "muted_users") else []
        excluded_user_ids = set(blocked_by_viewer).union(set(blocking_viewer)).union(set(muted_by_viewer))

        if excluded_user_ids:
            queryset = queryset.exclude(user_id__in=excluded_user_ids)

        following_ids = viewer.following.values_list("id", flat=True)

        privacy_condition = (
            Q(user=viewer)
            | Q(user__privacy_level=PrivacyChoices.PUBLIC)
            | (Q(user__privacy_level=PrivacyChoices.FRIENDS) & Q(user_id__in=following_ids))
        )

        return queryset.filter(privacy_condition)

    @classmethod
    def filter_visible_activities(cls, viewer: Optional[Any], queryset: QuerySet) -> QuerySet:
        """
        Filtra un queryset de Activity para el feed social, asegurando que solo incluya:
        - Autores y usuarios objetivo activos.
        - Sin bloqueos bidireccionales con el visor (tanto en user como en target_user).
        - Actividad pública para el visor respetando activity_privacy_level y privacy_level.
        """
        if not viewer or not getattr(viewer, "is_authenticated", False):
            # Visor anónimo solo ve actividades de usuarios públicos
            return queryset.filter(
                user__is_active=True,
                user__privacy_level=PrivacyChoices.PUBLIC,
                user__activity_privacy_level=PrivacyChoices.PUBLIC,
            )

        # Excluir autores inactivos
        if not getattr(viewer, "is_staff", False):
            queryset = queryset.filter(user__is_active=True)

        # Bloqueos bidireccionales
        blocked_by_viewer = set(viewer.blocked_users.values_list("id", flat=True))
        blocking_viewer = set(viewer.blocked_by.values_list("id", flat=True))
        muted_by_viewer = set(viewer.muted_users.values_list("id", flat=True)) if hasattr(viewer, "muted_users") else set()
        excluded_ids = blocked_by_viewer.union(blocking_viewer).union(muted_by_viewer)

        if excluded_ids:
            queryset = queryset.exclude(user_id__in=excluded_ids)
            queryset = queryset.exclude(target_user_id__in=excluded_ids)

        following_ids = set(viewer.following.values_list("id", flat=True))

        visibility_condition = (
            Q(user=viewer)
            | (
                Q(user__privacy_level=PrivacyChoices.PUBLIC)
                & Q(user__activity_privacy_level=PrivacyChoices.PUBLIC)
            )
            | (
                (
                    Q(user__privacy_level=PrivacyChoices.FRIENDS)
                    | Q(user__activity_privacy_level=PrivacyChoices.FRIENDS)
                )
                & ~Q(user__privacy_level=PrivacyChoices.PRIVATE)
                & ~Q(user__activity_privacy_level=PrivacyChoices.PRIVATE)
                & Q(user_id__in=following_ids)
            )
        )

        return queryset.filter(visibility_condition)

    @classmethod
    def filter_visible_reading_lists(cls, viewer: Optional[Any], queryset: QuerySet) -> QuerySet:
        """
        Filtra un queryset de ReadingList según los permisos de visibilidad del visor.
        """
        if not viewer or not getattr(viewer, "is_staff", False):
            queryset = queryset.filter(user__is_active=True)

        if not viewer or not getattr(viewer, "is_authenticated", False):
            return queryset.filter(
                privacy="public",
                user__privacy_level=PrivacyChoices.PUBLIC,
            )

        blocked_by_viewer = set(viewer.blocked_users.values_list("id", flat=True))
        blocking_viewer = set(viewer.blocked_by.values_list("id", flat=True))
        excluded_ids = blocked_by_viewer.union(blocking_viewer)

        if excluded_ids:
            queryset = queryset.exclude(user_id__in=excluded_ids)

        following_ids = set(viewer.following.values_list("id", flat=True))

        condition = (
            Q(user=viewer)
            | (Q(privacy="public") & ~Q(user__privacy_level=PrivacyChoices.PRIVATE))
            | (Q(privacy="followers") & Q(user_id__in=following_ids))
        )
        return queryset.filter(condition).distinct()

    @classmethod
    def filter_visible_user_books(cls, viewer: Optional[Any], queryset: QuerySet) -> QuerySet:
        """
        Filtra un queryset de UserBook (lecturas/biblioteca) según permisos de visibilidad.
        """
        if not viewer or not getattr(viewer, "is_staff", False):
            queryset = queryset.filter(user__is_active=True)

        if not viewer or not getattr(viewer, "is_authenticated", False):
            return queryset.filter(
                user__privacy_level=PrivacyChoices.PUBLIC,
                user__reading_privacy_level=PrivacyChoices.PUBLIC,
            )

        blocked_by_viewer = set(viewer.blocked_users.values_list("id", flat=True))
        blocking_viewer = set(viewer.blocked_by.values_list("id", flat=True))
        excluded_ids = blocked_by_viewer.union(blocking_viewer)

        if excluded_ids:
            queryset = queryset.exclude(user_id__in=excluded_ids)

        following_ids = set(viewer.following.values_list("id", flat=True))

        condition = (
            Q(user=viewer)
            | (
                Q(user__privacy_level=PrivacyChoices.PUBLIC)
                & Q(user__reading_privacy_level=PrivacyChoices.PUBLIC)
            )
            | (
                (
                    Q(user__privacy_level=PrivacyChoices.FRIENDS)
                    | Q(user__reading_privacy_level=PrivacyChoices.FRIENDS)
                )
                & ~Q(user__privacy_level=PrivacyChoices.PRIVATE)
                & ~Q(user__reading_privacy_level=PrivacyChoices.PRIVATE)
                & Q(user_id__in=following_ids)
            )
        )
        return queryset.filter(condition)
