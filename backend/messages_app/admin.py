from django.contrib import admin

from .models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'updated_at')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'created_at', 'deleted_at', 'read', 'is_moderated')
    list_filter = ('read', 'is_moderated')
    search_fields = ('sender__username', 'text')
