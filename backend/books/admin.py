from django.contrib import admin

from .models import Author, Book, Errata, LegalDocument, Review, ReviewComment, UserBook


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'isbn', 'average_rating')
    search_fields = ('title', 'isbn')


@admin.register(UserBook)
class UserBookAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'is_read', 'rating', 'owned', 'wishlist')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'rating', 'created_at', 'deleted_at', 'is_moderated')
    list_filter = ('is_moderated', 'rating')
    search_fields = ('user__username', 'book__title', 'title', 'text')


@admin.register(ReviewComment)
class ReviewCommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'review', 'created_at', 'deleted_at')
    search_fields = ('user__username', 'content')


@admin.register(Errata)
class ErrataAdmin(admin.ModelAdmin):
    list_display = ('type', 'status', 'user', 'book', 'author', 'created_at')
    list_filter = ('status', 'type')


@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'updated_at', 'updated_by')
