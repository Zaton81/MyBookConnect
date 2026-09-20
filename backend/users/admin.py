from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone

from .models import Activity, Notification, Report, ReportStatus, UserRole

User = get_user_model()


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'id',
        'username',
        'email',
        'role',
        'is_staff',
        'is_editor',
        'is_active',
        'privacy_level',
        'date_joined',
    )
    list_filter = ('role', 'is_staff', 'is_editor', 'is_active', 'privacy_level', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    fieldsets = UserAdmin.fieldsets + (
        ('Perfil Extendido', {
            'fields': (
                'role',
                'is_editor',
                'bio',
                'avatar',
                'birth_date',
                'location',
                'privacy_level',
                'gamification_enabled',
            )
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Perfil Extendido', {
            'fields': (
                'email',
                'role',
                'is_editor',
                'bio',
                'avatar',
                'birth_date',
                'location',
                'privacy_level',
                'gamification_enabled',
            )
        }),
    )
    actions = ('ban_users', 'unban_users', 'make_editor', 'remove_editor')

    @admin.action(description="🚫 Bloquear cuentas seleccionadas (is_active=False)")
    def ban_users(self, request, queryset):
        # Evitar bloquearse a sí mismo
        protected = queryset.filter(id=request.user.id)
        valid = queryset.exclude(id=request.user.id)
        count = valid.update(is_active=False)
        msg = f"{count} usuario(s) bloqueados."
        if protected.exists():
            msg += " Se omitió tu propia cuenta por seguridad."
        self.message_user(request, msg)

    @admin.action(description="✅ Desbloquear cuentas seleccionadas (is_active=True)")
    def unban_users(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} usuario(s) reactivados.")

    @admin.action(description="✍️ Asignar rol de Editor de Catálogo")
    def make_editor(self, request, queryset):
        count = queryset.update(is_editor=True, role=UserRole.EDITOR)
        self.message_user(request, f"{count} usuario(s) promovidos a Editor.")

    @admin.action(description="👤 Revocar rol de Editor (volver a Usuario estándar)")
    def remove_editor(self, request, queryset):
        count = queryset.filter(role=UserRole.EDITOR).update(is_editor=False, role=UserRole.USER)
        self.message_user(request, f"{count} usuario(s) devueltos a Usuario estándar.")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'reporter',
        'content_type',
        'object_id',
        'reason',
        'status',
        'created_at',
        'resolved_by',
        'resolved_at',
    )
    list_filter = ('status', 'reason', 'created_at')
    search_fields = ('reporter__username', 'description', 'resolution_notes')
    actions = ('mark_as_resolved', 'mark_as_rejected')

    @admin.action(description="✅ Marcar denuncias como Resueltas")
    def mark_as_resolved(self, request, queryset):
        updated = queryset.update(
            status=ReportStatus.RESOLVED,
            resolved_by=request.user,
            resolved_at=timezone.now(),
        )
        self.message_user(request, f"{updated} denuncia(s) resueltas.")

    @admin.action(description="❌ Marcar denuncias como Rechazadas")
    def mark_as_rejected(self, request, queryset):
        updated = queryset.update(
            status=ReportStatus.REJECTED,
            resolved_by=request.user,
            resolved_at=timezone.now(),
        )
        self.message_user(request, f"{updated} denuncia(s) desestimadas/rechazadas.")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipient', 'actor', 'type', 'title', 'read', 'created_at')
    list_filter = ('type', 'read', 'created_at')
    search_fields = ('recipient__username', 'actor__username', 'title', 'message')
    actions = ('mark_as_read', 'mark_as_unread')

    @admin.action(description="👁️ Marcar notificaciones como leídas")
    def mark_as_read(self, request, queryset):
        updated = queryset.update(read=True)
        self.message_user(request, f"{updated} notificación(es) marcadas como leídas.")

    @admin.action(description="✉️ Marcar notificaciones como no leídas")
    def mark_as_unread(self, request, queryset):
        updated = queryset.update(read=False)
        self.message_user(request, f"{updated} notificación(es) marcadas como pendientes.")


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'type', 'book', 'review', 'target_user', 'created_at')
    list_filter = ('type', 'created_at')
    search_fields = ('user__username', 'book__title')
