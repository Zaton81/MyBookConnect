from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

User = get_user_model()

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_staff', 'is_private')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_private')
    fieldsets = UserAdmin.fieldsets + (
        ('Perfil', {'fields': ('bio', 'avatar', 'is_private')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Perfil', {'fields': ('email', 'bio', 'avatar', 'is_private')}),
    )
