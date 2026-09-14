"""
Módulo base para soporte de borrado lógico (Soft Delete) en MyBookConnect (Fase 31).

Provee:
- SoftDeleteQuerySet: consultas con métodos auxiliares .active() y .deleted().
- SoftDeleteManager: manager para filtrado y restauración.
- SoftDeleteModel: clase abstracta con deleted_at, soft_delete(), restore() e is_deleted.
"""

from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet con operaciones especializadas para modelos con borrado lógico."""

    def active(self):
        """Filtra únicamente los registros activos (no eliminados)."""
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        """Filtra únicamente los registros marcados como eliminados."""
        return self.filter(deleted_at__isnull=False)

    def soft_delete(self):
        """Marca en lote los registros como eliminados con la fecha y hora actual."""
        return self.update(deleted_at=timezone.now())

    def restore(self):
        """Restaura en lote los registros eliminados limpiando deleted_at."""
        return self.update(deleted_at=None)


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Manager que expone métodos de SoftDeleteQuerySet."""
    pass


class SoftDeleteModel(models.Model):
    """
    Clase abstracta para entidades que soportan borrado lógico (Fase 31).
    """
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Fecha y hora de eliminación lógica. Si es null, el registro está activo.",
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    @property
    def is_deleted(self) -> bool:
        """Indica si el registro ha sido eliminado lógicamente."""
        return self.deleted_at is not None

    def soft_delete(self):
        """Marca el registro como eliminado lógicamente."""
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def restore(self):
        """Restaura el registro eliminado lógicamente."""
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])

    def delete(self, using=None, keep_parents=False, hard=False):
        """
        Sobrescribe delete para aplicar borrado lógico por defecto.
        Si se pasa hard=True, se ejecuta el borrado físico real de la base de datos.
        """
        if hard:
            return super().delete(using=using, keep_parents=keep_parents)
        return self.soft_delete()
