import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models


class AIUsageLog(models.Model):
    """
    Registro inmutable de observabilidad, auditoría y presupuesto de consumo de IA.
    Registra cada interacción con proveedores externos o locales (tokens, latencia, coste).
    """

    # Tarifas estimadas por millón de tokens (USD)
    PRICING_TABLE = {
        'openai': {
            'gpt-4o-mini': {'prompt_per_m': Decimal('0.15'), 'completion_per_m': Decimal('0.60')},
            'gpt-4o': {'prompt_per_m': Decimal('2.50'), 'completion_per_m': Decimal('10.00')},
            'text-embedding-3-small': {'prompt_per_m': Decimal('0.02'), 'completion_per_m': Decimal('0.00')},
            'default': {'prompt_per_m': Decimal('0.50'), 'completion_per_m': Decimal('1.50')},
        },
        'openrouter': {
            'default': {'prompt_per_m': Decimal('0.50'), 'completion_per_m': Decimal('1.50')},
        },
        'ollama': {
            'default': {'prompt_per_m': Decimal('0.00'), 'completion_per_m': Decimal('0.00')},
        },
    }

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_usage_logs',
        verbose_name='Usuario solicitante',
    )
    request_id = models.CharField(max_length=64, db_index=True, verbose_name='ID de petición')
    provider = models.CharField(max_length=64, db_index=True, verbose_name='Proveedor de IA')
    model = models.CharField(max_length=128, verbose_name='Modelo utilizado')
    prompt_tokens = models.PositiveIntegerField(default=0, verbose_name='Tokens de entrada (Prompt)')
    completion_tokens = models.PositiveIntegerField(default=0, verbose_name='Tokens de salida (Respuesta)')
    total_tokens = models.PositiveIntegerField(default=0, verbose_name='Tokens totales')
    estimated_cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=Decimal('0.000000'),
        verbose_name='Coste estimado (USD)',
    )
    duration_ms = models.PositiveIntegerField(default=0, verbose_name='Duración (milisegundos)')
    success = models.BooleanField(default=True, verbose_name='Llamada exitosa')
    error = models.TextField(blank=True, default='', verbose_name='Detalle de error si falló')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Fecha y hora')

    class Meta:
        verbose_name = 'Registro de uso de IA'
        verbose_name_plural = 'Registros de uso de IA'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at'], name='idx_ai_user_created'),
            models.Index(fields=['provider', 'created_at'], name='idx_ai_prov_created'),
        ]

    def __str__(self) -> str:
        user_str = self.user.username if self.user else 'anon'
        status_str = 'OK' if self.success else 'ERROR'
        return f"[{self.provider}:{self.model}] {user_str} - {self.total_tokens} tokens ({status_str})"

    @classmethod
    def calculate_cost(
        cls,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> Decimal:
        """
        Calcula el coste estimado en USD a partir de la tabla de precios del modelo.
        """
        prov_key = provider.lower().strip()
        provider_pricing = cls.PRICING_TABLE.get(prov_key, cls.PRICING_TABLE.get('openrouter', {}))

        model_key = model.lower().strip()
        pricing = provider_pricing.get(model_key, provider_pricing.get('default', {
            'prompt_per_m': Decimal('0.00'),
            'completion_per_m': Decimal('0.00'),
        }))

        prompt_cost = (Decimal(prompt_tokens) / Decimal(1_000_000)) * pricing['prompt_per_m']
        completion_cost = (Decimal(completion_tokens) / Decimal(1_000_000)) * pricing['completion_per_m']
        return (prompt_cost + completion_cost).quantize(Decimal('0.000001'))

    @classmethod
    def log_usage(
        cls,
        user=None,
        request_id: str | None = None,
        provider: str = 'unknown',
        model: str = 'unknown',
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        duration_ms: int = 0,
        success: bool = True,
        error: str = '',
    ) -> 'AIUsageLog':
        """
        Método de factoría seguro para registrar el uso de IA de forma atómica y no bloqueante.
        """
        req_id = request_id or str(uuid.uuid4())
        total_tokens = prompt_tokens + completion_tokens
        cost = cls.calculate_cost(provider, model, prompt_tokens, completion_tokens)

        # Si el usuario es anónimo o no es instancia de User, dejar como None
        actual_user = user if (user and getattr(user, 'is_authenticated', False)) else None

        return cls.objects.create(
            user=actual_user,
            request_id=req_id,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=cost,
            duration_ms=duration_ms,
            success=success,
            error=error,
        )
