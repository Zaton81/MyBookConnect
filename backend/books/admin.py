from django.contrib import admin

from .models import Author, Book, Errata, LegalDocument, Review, UserBook


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
    list_display = ('user', 'book', 'rating', 'created_at')


@admin.register(Errata)
class ErrataAdmin(admin.ModelAdmin):
    list_display = ('type', 'status', 'user', 'book', 'author', 'created_at')
    list_filter = ('status', 'type')


@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'updated_at', 'updated_by')
