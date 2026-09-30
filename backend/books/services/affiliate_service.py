"""
Servicio de Enlaces de Afiliación y Monetización Ética (Fase 31 — RoadmapV2).
Genera enlaces de compra directos para libros físicos, ebooks (Kindle) y audiolibros (Audible)
con el identificador de afiliado configurado, cumpliendo con las directrices de transparencia
y no manipulación de recomendaciones.
"""
import urllib.parse

from django.conf import settings

from books.models import AffiliateClick, Book

DISCLOSURE_TEXT = (
    "Enlace de afiliado: MyBookConnect puede recibir una comisión por compras "
    "cualificadas a través de estos enlaces, sin coste adicional para ti."
)


class AffiliateService:
    @classmethod
    def get_affiliate_tag(cls) -> str:
        """Obtiene el ID de afiliado de Amazon desde settings o variable de entorno."""
        return getattr(settings, 'AMAZON_AFFILIATE_TAG', 'mybooksocial-21')

    @classmethod
    def generate_affiliate_links(cls, book: Book) -> dict:
        """
        Genera enlaces canónicos para los distintos formatos de compra disponibles en Amazon.
        """
        tag = cls.get_affiliate_tag()
        author_name = book.author.name if book.author else ""
        query = f"{book.title} {author_name}".strip()
        encoded_query = urllib.parse.quote_plus(query)

        # 1. Enlace para libro físico / papel
        # Si tiene ISBN de 10 dígitos normalizado, puede redirigir directamente al producto (/dp/)
        clean_isbn = (book.isbn or "").replace("-", "").strip()
        if len(clean_isbn) == 10:
            paperback_url = f"https://www.amazon.es/dp/{clean_isbn}?tag={tag}"
        else:
            paperback_url = f"https://www.amazon.es/s?k={encoded_query}&i=stripbooks&tag={tag}"

        # 2. Enlace para Kindle (Ebook)
        ebook_url = f"https://www.amazon.es/s?k={encoded_query}&i=digital-text&tag={tag}"

        # 3. Enlace para Audible (Audiolibro)
        audiobook_url = f"https://www.amazon.es/s?k={encoded_query}&i=audible&tag={tag}"

        return {
            "book_id": book.id,
            "book_title": book.title,
            "author_name": author_name,
            "affiliate_tag": tag,
            "disclosure": DISCLOSURE_TEXT,
            "links": {
                "paperback": {
                    "format": "paperback",
                    "label": "Libro Físico (Papel)",
                    "url": paperback_url,
                    "store": "Amazon",
                },
                "ebook": {
                    "format": "ebook",
                    "label": "Ebook (Kindle)",
                    "url": ebook_url,
                    "store": "Amazon Kindle",
                },
                "audiobook": {
                    "format": "audiobook",
                    "label": "Audiolibro (Audible)",
                    "url": audiobook_url,
                    "store": "Audible",
                },
            },
        }

    @classmethod
    def record_click(cls, book: Book, format_type: str) -> AffiliateClick:
        """
        Registra un clic de forma totalmente anonimizada para estadísticas de conversión,
        cumpliendo con el RGPD y sin almacenar datos personales.
        """
        valid_formats = {choice[0] for choice in AffiliateClick.FormatChoices.choices}
        fmt = format_type.lower() if format_type else AffiliateClick.FormatChoices.PAPERBACK
        if fmt not in valid_formats:
            fmt = AffiliateClick.FormatChoices.PAPERBACK

        return AffiliateClick.objects.create(
            book=book,
            format=fmt,
        )
