from django.contrib import admin
from django.db.models import Q
from django.utils import timezone

from .models import (
    Author,
    Book,
    Category,
    Errata,
    ErrataStatus,
    LegalDocument,
    Review,
    ReviewComment,
    UserBook,
)
from .tasks import enrich_book_task, refresh_author_task


class ProviderListFilter(admin.SimpleListFilter):
    title = 'Proveedor / Fuente externa'
    parameter_name = 'provider'

    def lookups(self, request, model_admin):
        return (
            ('google', 'Google Books'),
            ('openlibrary', 'OpenLibrary'),
            ('isbn', 'Con ISBN'),
            ('none', 'Sin identificador externo'),
        )

    def queryset(self, request, queryset):
        val = self.value()
        if val == 'google':
            return queryset.filter(google_volume_id__isnull=False).exclude(google_volume_id='')
        if val == 'openlibrary':
            return queryset.filter(
                Q(openlibrary_work_id__isnull=False) | Q(openlibrary_edition_id__isnull=False)
            ).exclude(openlibrary_work_id='', openlibrary_edition_id='')
        if val == 'isbn':
            return queryset.filter(isbn__isnull=False).exclude(isbn='')
        if val == 'none':
            return queryset.filter(
                Q(google_volume_id__isnull=True) | Q(google_volume_id=''),
                Q(openlibrary_work_id__isnull=True) | Q(openlibrary_work_id=''),
                Q(openlibrary_edition_id__isnull=True) | Q(openlibrary_edition_id=''),
                Q(isbn__isnull=True) | Q(isbn=''),
            )
        return queryset


class RatingRangeFilter(admin.SimpleListFilter):
    title = 'Puntuación promedio'
    parameter_name = 'rating_range'

    def lookups(self, request, model_admin):
        return (
            ('high', '⭐ 4.0 o superior'),
            ('mid', '⭐ 2.5 a 3.9'),
            ('low', '⭐ Menos de 2.5'),
            ('unrated', 'Sin valoraciones'),
        )

    def queryset(self, request, queryset):
        val = self.value()
        if val == 'high':
            return queryset.filter(average_rating__gte=4.0)
        if val == 'mid':
            return queryset.filter(average_rating__gte=2.5, average_rating__lt=4.0)
        if val == 'low':
            return queryset.filter(average_rating__lt=2.5, average_rating__isnull=False)
        if val == 'unrated':
            return queryset.filter(average_rating__isnull=True)
        return queryset


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'enrichment_attempted')
    search_fields = ('name', 'biography')
    list_filter = ('enrichment_attempted',)
    actions = ('re_enrich_authors',)

    @admin.action(description="⚡ Re-enriquecer autores seleccionados (Wikipedia/APIs)")
    def re_enrich_authors(self, request, queryset):
        count = 0
        for author in queryset:
            author.enrichment_attempted = False
            author.save(update_fields=['enrichment_attempted'])
            refresh_author_task.delay(author.id)
            count += 1
        self.message_user(request, f"{count} autor(es) encolados para re-enriquecimiento.")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'author',
        'isbn',
        'average_rating',
        'published_date',
        'enrichment_attempted',
        'created_at',
    )
    list_filter = (
        ProviderListFilter,
        RatingRangeFilter,
        'enrichment_attempted',
        'categories',
        'created_at',
    )
    search_fields = ('title', 'isbn', 'author__name', 'description')
    autocomplete_fields = ('author',)
    filter_horizontal = ('categories',)
    actions = ('re_enrich_books', 'rebuild_embeddings')

    @admin.action(description="⚡ Re-enriquecer libros seleccionados (Google Books/OpenLibrary)")
    def re_enrich_books(self, request, queryset):
        count = 0
        for book in queryset:
            book.enrichment_attempted = False
            book.save(update_fields=['enrichment_attempted'])
            enrich_book_task.delay(book.id)
            count += 1
        self.message_user(request, f"{count} libro(s) encolados para re-enriquecimiento de metadatos.")

    @admin.action(description="🤖 Reconstruir vectores de embedding semántico")
    def rebuild_embeddings(self, request, queryset):
        count = 0
        for book in queryset:
            try:
                from ai.embedding_service import generate_book_embedding
                book.embedding = generate_book_embedding(book)
                book.save(update_fields=['embedding'])
            except Exception:
                # Si el servicio de IA no está disponible, mantenemos el registro
                pass
            count += 1
        self.message_user(request, f"{count} libro(s) procesados para reconstrucción de embedding.")


@admin.register(UserBook)
class UserBookAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'book', 'status', 'is_read', 'rating', 'owned', 'wishlist', 'updated_at')
    list_filter = ('status', 'is_read', 'owned', 'wishlist', 'rating')
    search_fields = ('user__username', 'book__title', 'book__isbn')
    autocomplete_fields = ('book',)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'book', 'rating', 'created_at', 'deleted_at', 'is_moderated')
    list_filter = ('is_moderated', 'rating', 'created_at', 'deleted_at')
    search_fields = ('user__username', 'book__title', 'title', 'text')
    actions = ('mark_as_moderated', 'unmark_as_moderated', 'soft_delete_reviews', 'restore_reviews')

    @admin.action(description="🛡️ Marcar como moderadas (ocultar de la vista pública)")
    def mark_as_moderated(self, request, queryset):
        updated = queryset.update(is_moderated=True)
        self.message_user(request, f"{updated} reseña(s) marcadas como moderadas.")

    @admin.action(description="✅ Desmarcar moderación (restablecer a pública)")
    def unmark_as_moderated(self, request, queryset):
        updated = queryset.update(is_moderated=False)
        self.message_user(request, f"{updated} reseña(s) restablecidas.")

    @admin.action(description="🗑️ Borrado suave (soft delete)")
    def soft_delete_reviews(self, request, queryset):
        updated = queryset.update(deleted_at=timezone.now())
        self.message_user(request, f"{updated} reseña(s) eliminadas suavemente.")

    @admin.action(description="♻️ Restaurar reseñas eliminadas suavemente")
    def restore_reviews(self, request, queryset):
        updated = queryset.update(deleted_at=None)
        self.message_user(request, f"{updated} reseña(s) restauradas.")


@admin.register(ReviewComment)
class ReviewCommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'review', 'created_at', 'deleted_at')
    list_filter = ('created_at', 'deleted_at')
    search_fields = ('user__username', 'content')


@admin.register(Errata)
class ErrataAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'status', 'user', 'book', 'author', 'editor', 'created_at')
    list_filter = ('status', 'type', 'created_at')
    search_fields = ('text', 'book__title', 'author__name', 'user__username')
    actions = ('approve_erratas', 'reject_erratas')

    @admin.action(description="✅ Aprobar erratas seleccionadas")
    def approve_erratas(self, request, queryset):
        updated = queryset.update(status=ErrataStatus.APPROVED, editor=request.user)
        self.message_user(request, f"{updated} errata(s) aprobadas.")

    @admin.action(description="❌ Rechazar erratas seleccionadas")
    def reject_erratas(self, request, queryset):
        updated = queryset.update(status=ErrataStatus.REJECTED, editor=request.user)
        self.message_user(request, f"{updated} errata(s) rechazadas.")


@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'slug', 'updated_at', 'updated_by')
    search_fields = ('title', 'slug', 'content')
