import secrets
from typing import Any, Dict

from beta.models import BetaInvitation


class ReferralService:
    """
    Servicio de referidos virales entre lectores para la Beta Pública (Fase 37).
    Permite a los usuarios generar su propio código de invitación y monitorizar
    cuántos amigos o lectores han ingresado con él.
    """
    REFERRAL_PREFIX = "REF-"
    DEFAULT_MAX_USES = 50

    @classmethod
    def get_or_create_referral_code(cls, user) -> BetaInvitation:
        """
        Obtiene el código de referido activo del usuario o crea uno nuevo si no existe.
        Garantiza que el código no exceda los 32 caracteres permitidos en el modelo.
        """
        existing = BetaInvitation.objects.filter(
            created_by=user,
            code__startswith=cls.REFERRAL_PREFIX,
            is_active=True
        ).first()

        if existing and existing.is_valid():
            return existing

        # Sanitizar username para el código (alfanumérico, hasta 10 chars)
        clean_user = "".join(c for c in user.username if c.isalnum())[:10].upper()
        if not clean_user:
            clean_user = f"USER{user.id}"

        # Sufijo aleatorio criptográfico
        random_suffix = secrets.token_hex(4).upper()  # 8 chars
        code = f"{cls.REFERRAL_PREFIX}{clean_user}-{random_suffix}"[:32]

        # Garantizar unicidad
        while BetaInvitation.objects.filter(code=code).exists():
            random_suffix = secrets.token_hex(4).upper()
            code = f"{cls.REFERRAL_PREFIX}{clean_user}-{random_suffix}"[:32]

        invitation = BetaInvitation.objects.create(
            code=code,
            created_by=user,
            max_uses=cls.DEFAULT_MAX_USES,
            is_active=True
        )
        return invitation

    @classmethod
    def get_referral_stats(cls, user) -> Dict[str, Any]:
        """
        Calcula las estadísticas del programa de referidos para el usuario.
        """
        invitation = cls.get_or_create_referral_code(user)
        remaining = max(0, invitation.max_uses - invitation.uses_count)

        return {
            "code": invitation.code,
            "referral_url": f"/register?ref={invitation.code}",
            "uses_count": invitation.uses_count,
            "max_uses": invitation.max_uses,
            "remaining_uses": remaining,
            "is_active": invitation.is_active and remaining > 0,
            "created_at": invitation.created_at.isoformat() if invitation.created_at else None,
        }
