"""
Modelos para el Marketplace de Libros, Editoriales y Enlaces de Compra Multitienda.
Sprint 19 — RoadmapV3 (Sección 30: Marketplace / Editoriales).
"""
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Publisher(models.Model):
    """
    Entidad Editorial encargada de publicar obras literarias.
    Permite a sellos editoriales e independientes tener presencia verificable en la plataforma.
    """
    name = models.CharField(max_length=200, db_index=True, verbose_name="Nombre de la editorial")
    slug = models.SlugField(max_length=200, unique=True, verbose_name="Identificador URL")
    description = models.TextField(blank=True, default="", verbose_name="Descripción o reseña histórica")
    website = models.URLField(blank=True, default="", verbose_name="Sitio web oficial")
    logo = models.ImageField(upload_to="publisher_logos/", null=True, blank=True, verbose_name="Logotipo")
    country = models.CharField(max_length=100, blank=True, default="España", verbose_name="País de origen")
    is_verified = models.BooleanField(default=False, db_index=True, verbose_name="Editorial verificada")
    claimed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="claimed_publishers",
        verbose_name="Usuario representante oficial",
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Fecha de registro")

    class Meta:
        verbose_name = "Editorial"
        verbose_name_plural = "Editoriales"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            base_slug = slugify(self.name) or "editorial"
            unique_slug = base_slug
            counter = 1
            while Publisher.objects.filter(slug=unique_slug).exclude(pk=self.pk).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = unique_slug
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class BookBuyLink(models.Model):
    """
    Oferta u opción de compra comercial para un libro específico en una librería o canal digital.
    Soporta librerías independientes, grandes cadenas, tiendas de ebooks/audiolibros y venta directa.
    """
    class MerchantType(models.TextChoices):
        INDIE_NETWORK = "indie_network", "Red de Librerías Independientes (TodosTusLibros)"
        ONLINE_RETAILER = "online_retailer", "Librería Online / Gran Cadena (Casa del Libro, Fnac, Amazon)"
        PUBLISHER_DIRECT = "publisher_direct", "Editorial Directa / Web del Autor"
        EBOOK_STORE = "ebook_store", "Tienda Digital (Kindle, Kobo, Google Play)"
        AUDIO_STORE = "audio_store", "Plataforma de Audio (Audible, Storytel)"

    class BookFormat(models.TextChoices):
        PAPERBACK = "paperback", "Tapa Blanda / Bolsillo"
        HARDCOVER = "hardcover", "Tapa Dura"
        EBOOK = "ebook", "Ebook / Digital"
        AUDIOBOOK = "audiobook", "Audiolibro"

    book = models.ForeignKey(
        "books.Book",
        on_delete=models.CASCADE,
        related_name="buy_links",
        verbose_name="Libro asociado",
    )
    merchant_name = models.CharField(max_length=100, verbose_name="Nombre de la librería o plataforma")
    merchant_type = models.CharField(
        max_length=30,
        choices=MerchantType.choices,
        default=MerchantType.ONLINE_RETAILER,
        db_index=True,
        verbose_name="Tipo de comercio",
    )
    format = models.CharField(
        max_length=20,
        choices=BookFormat.choices,
        default=BookFormat.PAPERBACK,
        db_index=True,
        verbose_name="Formato del libro",
    )
    url = models.URLField(max_length=1000, verbose_name="Enlace directo a la tienda")
    price = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Precio estimado",
    )
    currency = models.CharField(max_length=10, default="EUR", verbose_name="Moneda")
    is_official = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Enlace oficial verificado por autor o editorial",
    )
    is_affiliate = models.BooleanField(
        default=False,
        verbose_name="Enlace con comisión de afiliación",
    )
    affiliate_tag = models.CharField(max_length=100, blank=True, default="", verbose_name="Etiqueta de afiliado")
    is_active = models.BooleanField(default=True, db_index=True, verbose_name="Oferta activa")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_buy_links",
        verbose_name="Creado por",
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Fecha de creación")

    class Meta:
        verbose_name = "Enlace de Compra"
        verbose_name_plural = "Enlaces de Compra"
        ordering = ["-is_official", "merchant_name"]

    def __str__(self) -> str:
        return f"{self.merchant_name} ({self.get_format_display()}) - {self.book.title}"


class MarketplaceClick(models.Model):
    """
    Registro anónimo de clics hacia tiendas y opciones de compra para telemetría y métricas
    de conversión comercial, cumpliendo estrictamente con el RGPD (sin almacenar PII de usuarios).
    """
    book = models.ForeignKey(
        "books.Book",
        on_delete=models.CASCADE,
        related_name="marketplace_clicks",
        verbose_name="Libro consultado",
    )
    buy_link = models.ForeignKey(
        BookBuyLink,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="clicks",
        verbose_name="Enlace pulsado",
    )
    merchant_name = models.CharField(max_length=100, db_index=True, verbose_name="Comercio de destino")
    format = models.CharField(max_length=20, db_index=True, verbose_name="Formato consultado")
    created_at = models.DateTimeField(default=timezone.now, db_index=True, verbose_name="Momento del clic")

    class Meta:
        verbose_name = "Clic de Marketplace"
        verbose_name_plural = "Clics de Marketplace"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Marketplace [{self.merchant_name} - {self.format}] {self.book.title} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
