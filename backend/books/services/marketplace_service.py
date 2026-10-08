"""
Servicio de Marketplace, Red de Librerías y Enlaces Editoriales.
Sprint 19 — RoadmapV3 (Sección 30: Marketplace / Editoriales).
Implementa agregación multitienda, apoyo a librerías locales, venta directa editorial
y telemetría de conversión ética y anonimizada sin almacenar PII.
"""
import urllib.parse
from decimal import Decimal
from django.conf import settings
from django.db.models import Count
from django.core.exceptions import PermissionDenied, ValidationError

from books.models import (
    Book,
    Publisher,
    BookBuyLink,
    MarketplaceClick,
    AffiliateClick,
)
from books.services.affiliate_service import AffiliateService

ETHICAL_DISCLOSURE = (
    "MyBookConnect apoya la diversidad del ecosistema librero y el comercio de proximidad. "
    "Los enlaces a librerías independientes y tiendas oficiales se muestran con neutralidad editorial. "
    "Ciertas plataformas comerciales pueden generar una comisión de afiliación que sostiene los costes del servidor, "
    "sin ningún coste adicional para ti y sin alterar los algoritmos de recomendación."
)


class MarketplaceService:
    @classmethod
    def get_book_marketplace_offers(cls, book: Book, user=None) -> dict:
        """
        Retorna todas las opciones de adquisición disponibles para un libro, combinando
        enlaces oficiales registrados en BD con enlaces directos generados automáticamente
        para la red de librerías independientes (TodosTusLibros), grandes superficies y tiendas digitales.
        """
        clean_isbn = (book.isbn or "").replace("-", "").strip()
        author_name = book.author.name if book.author else ""
        query_text = f"{book.title} {author_name}".strip()
        encoded_query = urllib.parse.quote_plus(query_text)
        encoded_title = urllib.parse.quote_plus(book.title)

        offers = []

        # 1. Enlaces oficiales o personalizados almacenados en BD
        stored_links = BookBuyLink.objects.filter(book=book, is_active=True).select_related('created_by')
        for link in stored_links:
            offers.append({
                "id": link.id,
                "merchant_name": link.merchant_name,
                "merchant_type": link.merchant_type,
                "format": link.format,
                "format_display": link.get_format_display(),
                "url": link.url,
                "price": float(link.price) if link.price else None,
                "currency": link.currency,
                "is_official": link.is_official,
                "is_affiliate": link.is_affiliate,
                "is_custom": True,
            })

        # 2. Generación automática inteligente si no existen ofertas manuales duplicadas

        # A) Red de Librerías Independientes (TodosTusLibros - CEGAL)
        has_indie = any(o["merchant_type"] == BookBuyLink.MerchantType.INDIE_NETWORK for o in offers)
        if not has_indie:
            if clean_isbn:
                ttl_url = f"https://www.todostuslibros.com/busqueda_libros?isbn={clean_isbn}"
            else:
                ttl_url = f"https://www.todostuslibros.com/busqueda_libros?titulo={encoded_title}"

            offers.append({
                "id": None,
                "merchant_name": "TodosTusLibros",
                "merchant_type": BookBuyLink.MerchantType.INDIE_NETWORK,
                "format": BookBuyLink.BookFormat.PAPERBACK,
                "format_display": "Libro Físico (Librerías de barrio)",
                "url": ttl_url,
                "price": None,
                "currency": "EUR",
                "is_official": False,
                "is_affiliate": False,
                "is_custom": False,
                "badge": "Librerías de Proximidad",
            })

        # B) Casa del Libro (Gran cadena cultural)
        has_cdl = any("casa del libro" in o["merchant_name"].lower() for o in offers)
        if not has_cdl:
            cdl_query = clean_isbn if clean_isbn else encoded_query
            cdl_url = f"https://www.casadellibro.com/libros-busqueda?q={cdl_query}"
            offers.append({
                "id": None,
                "merchant_name": "Casa del Libro",
                "merchant_type": BookBuyLink.MerchantType.ONLINE_RETAILER,
                "format": BookBuyLink.BookFormat.PAPERBACK,
                "format_display": "Libro Físico / Impreso",
                "url": cdl_url,
                "price": None,
                "currency": "EUR",
                "is_official": False,
                "is_affiliate": False,
                "is_custom": False,
            })

        # C) Fnac España
        has_fnac = any("fnac" in o["merchant_name"].lower() for o in offers)
        if not has_fnac:
            fnac_url = f"https://www.fnac.es/SearchResult/ResultList.aspx?Search={clean_isbn or encoded_query}"
            offers.append({
                "id": None,
                "merchant_name": "Fnac",
                "merchant_type": BookBuyLink.MerchantType.ONLINE_RETAILER,
                "format": BookBuyLink.BookFormat.PAPERBACK,
                "format_display": "Libro Físico",
                "url": fnac_url,
                "price": None,
                "currency": "EUR",
                "is_official": False,
                "is_affiliate": False,
                "is_custom": False,
            })

        # D) Amazon Multiformato (Físico, Kindle, Audible) vía AffiliateService
        affiliate_data = AffiliateService.generate_affiliate_links(book)
        links_dict = affiliate_data.get("links", {})

        has_amazon_paper = any("amazon" in o["merchant_name"].lower() and o["format"] == "paperback" for o in offers)
        if not has_amazon_paper and "paperback" in links_dict:
            offers.append({
                "id": None,
                "merchant_name": "Amazon",
                "merchant_type": BookBuyLink.MerchantType.ONLINE_RETAILER,
                "format": BookBuyLink.BookFormat.PAPERBACK,
                "format_display": "Libro Físico (Amazon)",
                "url": links_dict["paperback"]["url"],
                "price": None,
                "currency": "EUR",
                "is_official": False,
                "is_affiliate": True,
                "is_custom": False,
            })

        has_kindle = any(o["format"] == "ebook" and "kindle" in o["merchant_name"].lower() for o in offers)
        if not has_kindle and "ebook" in links_dict:
            offers.append({
                "id": None,
                "merchant_name": "Amazon Kindle",
                "merchant_type": BookBuyLink.MerchantType.EBOOK_STORE,
                "format": BookBuyLink.BookFormat.EBOOK,
                "format_display": "Ebook Digital (Kindle)",
                "url": links_dict["ebook"]["url"],
                "price": None,
                "currency": "EUR",
                "is_official": False,
                "is_affiliate": True,
                "is_custom": False,
            })

        has_audible = any(o["format"] == "audiobook" for o in offers)
        if not has_audible and "audiobook" in links_dict:
            offers.append({
                "id": None,
                "merchant_name": "Audible",
                "merchant_type": BookBuyLink.MerchantType.AUDIO_STORE,
                "format": BookBuyLink.BookFormat.AUDIOBOOK,
                "format_display": "Audiolibro Narrado (Audible)",
                "url": links_dict["audiobook"]["url"],
                "price": None,
                "currency": "EUR",
                "is_official": False,
                "is_affiliate": True,
                "is_custom": False,
            })

        # E) Google Play Books (Ebook Store)
        has_google = any("google" in o["merchant_name"].lower() for o in offers)
        if not has_google:
            if book.google_volume_id:
                gbooks_url = f"https://play.google.com/store/books/details?id={book.google_volume_id}"
            else:
                gbooks_url = f"https://play.google.com/store/search?q={encoded_query}&c=books"
            offers.append({
                "id": None,
                "merchant_name": "Google Play Books",
                "merchant_type": BookBuyLink.MerchantType.EBOOK_STORE,
                "format": BookBuyLink.BookFormat.EBOOK,
                "format_display": "Ebook Digital (Google Play)",
                "url": gbooks_url,
                "price": None,
                "currency": "EUR",
                "is_official": False,
                "is_affiliate": False,
                "is_custom": False,
            })

        # F) Enlace oficial de la editorial si existe
        if book.publisher and book.publisher.website:
            has_pub = any(o["merchant_type"] == BookBuyLink.MerchantType.PUBLISHER_DIRECT for o in offers)
            if not has_pub:
                offers.append({
                    "id": None,
                    "merchant_name": f"Editorial {book.publisher.name}",
                    "merchant_type": BookBuyLink.MerchantType.PUBLISHER_DIRECT,
                    "format": BookBuyLink.BookFormat.PAPERBACK,
                    "format_display": "Web Oficial de la Editorial",
                    "url": book.publisher.website,
                    "price": None,
                    "currency": "EUR",
                    "is_official": True,
                    "is_affiliate": False,
                    "is_custom": False,
                })

        # Comprobar permisos de gestión para el usuario actual
        can_manage = False
        if user and user.is_authenticated:
            if user.is_staff or (book.author and book.author.claimed_by == user):
                can_manage = True

        # Agrupaciones para facilitar renderizado en frontend
        by_format = {
            "paperback": [o for o in offers if o["format"] in ["paperback", "hardcover"]],
            "ebook": [o for o in offers if o["format"] == "ebook"],
            "audiobook": [o for o in offers if o["format"] == "audiobook"],
        }

        by_merchant_type = {
            "indie": [o for o in offers if o["merchant_type"] == BookBuyLink.MerchantType.INDIE_NETWORK],
            "online": [o for o in offers if o["merchant_type"] in [BookBuyLink.MerchantType.ONLINE_RETAILER, BookBuyLink.MerchantType.EBOOK_STORE, BookBuyLink.MerchantType.AUDIO_STORE]],
            "publisher": [o for o in offers if o["merchant_type"] == BookBuyLink.MerchantType.PUBLISHER_DIRECT or o.get("is_official")],
        }

        return {
            "book_id": book.id,
            "book_title": book.title,
            "author_name": author_name,
            "isbn": book.isbn,
            "publisher": {
                "id": book.publisher.id,
                "name": book.publisher.name,
                "slug": book.publisher.slug,
                "website": book.publisher.website,
                "is_verified": book.publisher.is_verified,
            } if book.publisher else None,
            "can_manage": can_manage,
            "disclosure": ETHICAL_DISCLOSURE,
            "total_offers": len(offers),
            "offers": offers,
            "by_format": by_format,
            "by_merchant_type": by_merchant_type,
        }

    @classmethod
    def record_marketplace_click(
        cls,
        book_id: int,
        merchant_name: str,
        format_type: str,
        buy_link_id: int | None = None,
    ) -> MarketplaceClick:
        """
        Registra de forma anónima el clic hacia una tienda sin almacenar identificadores
        personales ni IP de usuario, garantizando privacidad estricta y cumplimiento RGPD.
        """
        book = Book.objects.get(pk=book_id)
        buy_link = None
        if buy_link_id:
            buy_link = BookBuyLink.objects.filter(pk=buy_link_id).first()

        clean_format = (format_type or "paperback").lower()
        if clean_format not in [c[0] for c in BookBuyLink.BookFormat.choices]:
            clean_format = BookBuyLink.BookFormat.PAPERBACK

        click = MarketplaceClick.objects.create(
            book=book,
            buy_link=buy_link,
            merchant_name=merchant_name or "Unknown Merchant",
            format=clean_format,
        )

        # Si el clic se dirige a Amazon, también registramos en AffiliateClick para métricas consolidadas
        if "amazon" in (merchant_name or "").lower():
            AffiliateClick.objects.create(
                book=book,
                format=clean_format,
            )

        return click

    @classmethod
    def create_or_update_buy_link(cls, book_id: int, user, data: dict) -> BookBuyLink:
        """
        Permite a un autor verificado o administrador añadir o actualizar una oferta de compra
        oficial o directa para el libro.
        """
        book = Book.objects.get(pk=book_id)
        if not user or not user.is_authenticated:
            raise PermissionDenied("Se requiere autenticación para gestionar enlaces comerciales.")

        is_author_owner = book.author and book.author.claimed_by == user
        if not (user.is_staff or is_author_owner):
            raise PermissionDenied("Solo el autor verificado o un administrador pueden gestionar enlaces oficiales.")

        merchant_name = (data.get("merchant_name") or "").strip()
        url = (data.get("url") or "").strip()
        if not merchant_name or not url:
            raise ValidationError("El nombre del comercio y la URL son campos obligatorios.")

        merchant_type = data.get("merchant_type", BookBuyLink.MerchantType.ONLINE_RETAILER)
        format_val = data.get("format", BookBuyLink.BookFormat.PAPERBACK)
        price_val = data.get("price")
        currency = data.get("currency", "EUR")

        link_id = data.get("id")
        if link_id:
            link = BookBuyLink.objects.get(pk=link_id, book=book)
            link.merchant_name = merchant_name
            link.url = url
            link.merchant_type = merchant_type
            link.format = format_val
            link.price = Decimal(str(price_val)) if price_val is not None and price_val != "" else None
            link.currency = currency
            link.save()
            return link

        return BookBuyLink.objects.create(
            book=book,
            merchant_name=merchant_name,
            merchant_type=merchant_type,
            format=format_val,
            url=url,
            price=Decimal(str(price_val)) if price_val is not None and price_val != "" else None,
            currency=currency,
            is_official=True,
            created_by=user,
        )

    @classmethod
    def delete_buy_link(cls, buy_link_id: int, user) -> bool:
        """
        Elimina un enlace oficial de compra tras verificar permisos del usuario.
        """
        link = BookBuyLink.objects.get(pk=buy_link_id)
        book = link.book
        if not user or not user.is_authenticated:
            raise PermissionDenied("Se requiere autenticación.")

        is_author_owner = book.author and book.author.claimed_by == user
        if not (user.is_staff or is_author_owner or link.created_by == user):
            raise PermissionDenied("No tienes permisos para eliminar este enlace.")

        link.delete()
        return True

    @classmethod
    def get_publishers_catalog(cls, search: str | None = None, country: str | None = None) -> list[dict]:
        """
        Retorna el listado público de editoriales con conteo de obras publicadas.
        """
        qs = Publisher.objects.annotate(books_count=Count('books')).order_by('-is_verified', 'name')
        if search:
            qs = qs.filter(name__icontains=search.strip())
        if country:
            qs = qs.filter(country__iexact=country.strip())

        results = []
        for pub in qs:
            results.append({
                "id": pub.id,
                "name": pub.name,
                "slug": pub.slug,
                "description": pub.description,
                "website": pub.website,
                "logo": pub.logo.url if pub.logo else None,
                "country": pub.country,
                "is_verified": pub.is_verified,
                "books_count": pub.books_count,
            })
        return results

    @classmethod
    def get_publisher_detail(cls, publisher_id_or_slug: int | str) -> dict:
        """
        Retorna la ficha detallada de una editorial junto con sus obras catalogadas.
        """
        if isinstance(publisher_id_or_slug, int) or (isinstance(publisher_id_or_slug, str) and publisher_id_or_slug.isdigit()):
            pub = Publisher.objects.get(pk=int(publisher_id_or_slug))
        else:
            pub = Publisher.objects.get(slug=publisher_id_or_slug)

        books_qs = pub.books.select_related('author').order_by('-average_rating', '-created_at')[:20]
        books_data = []
        for b in books_qs:
            books_data.append({
                "id": b.id,
                "title": b.title,
                "author_name": b.author.name if b.author else "Autor desconocido",
                "cover": b.cover.url if b.cover else None,
                "average_rating": b.average_rating,
                "published_date": b.published_date.isoformat() if b.published_date else None,
            })

        return {
            "id": pub.id,
            "name": pub.name,
            "slug": pub.slug,
            "description": pub.description,
            "website": pub.website,
            "logo": pub.logo.url if pub.logo else None,
            "country": pub.country,
            "is_verified": pub.is_verified,
            "total_books": pub.books.count(),
            "books": books_data,
        }
