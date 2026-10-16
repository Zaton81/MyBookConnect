from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from books.models import Book

from .models import BookBuyLink, Publisher
from .services import MarketplaceService


class BookMarketplaceView(APIView):
    """
    Retorna las opciones de compra agregadas multitienda para una obra (librerías locales,
    tiendas online, formatos digital/audiolibro y venta directa oficial).
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        book = get_object_or_404(
            Book.objects.select_related('author', 'publisher'),
            pk=pk,
        )
        data = MarketplaceService.get_book_marketplace_offers(book, user=request.user)
        return Response(data, status=status.HTTP_200_OK)


class BookMarketplaceClickView(APIView):
    """
    Registra de forma anónima el clic hacia una tienda o librería para estadísticas de conversión,
    garantizando neutralidad editorial y cumplimiento RGPD sin almacenar PII.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, pk):
        merchant_name = request.data.get('merchant_name', 'Tienda')
        format_type = request.data.get('format', 'paperback')
        buy_link_id = request.data.get('buy_link_id')

        try:
            click = MarketplaceService.record_marketplace_click(
                book_id=pk,
                merchant_name=merchant_name,
                format_type=format_type,
                buy_link_id=buy_link_id,
            )
            return Response(
                {
                    'status': 'recorded',
                    'click_id': click.id,
                    'merchant_name': click.merchant_name,
                    'format': click.format,
                },
                status=status.HTTP_201_CREATED,
            )
        except Book.DoesNotExist:
            return Response({'detail': 'Libro no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BookMarketplaceLinksView(APIView):
    """
    Permite al autor verificado de la obra o a un administrador añadir o modificar
    un enlace oficial de compra o preventa.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            link = MarketplaceService.create_or_update_buy_link(
                book_id=pk,
                user=request.user,
                data=request.data,
            )
            return Response(
                {
                    'id': link.id,
                    'merchant_name': link.merchant_name,
                    'merchant_type': link.merchant_type,
                    'format': link.format,
                    'url': link.url,
                    'price': float(link.price) if link.price else None,
                    'currency': link.currency,
                    'is_official': link.is_official,
                },
                status=status.HTTP_201_CREATED,
            )
        except Book.DoesNotExist:
            return Response({'detail': 'Libro no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BookMarketplaceLinkDetailView(APIView):
    """
    Elimina un enlace de compra oficial gestionado por un autor verificado o administrador.
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, link_id):
        try:
            MarketplaceService.delete_buy_link(buy_link_id=link_id, user=request.user)
            return Response({'status': 'deleted'}, status=status.HTTP_204_NO_CONTENT)
        except BookBuyLink.DoesNotExist:
            return Response({'detail': 'Enlace no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PublisherListView(APIView):
    """
    Catálogo y buscador público de editoriales.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        search = request.query_params.get('search')
        country = request.query_params.get('country')
        publishers = MarketplaceService.get_publishers_catalog(search=search, country=country)
        return Response({'results': publishers, 'count': len(publishers)}, status=status.HTTP_200_OK)


class PublisherDetailView(APIView):
    """
    Ficha pública detallada de una editorial con su catálogo de publicaciones destacadas.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, identifier):
        try:
            pub_data = MarketplaceService.get_publisher_detail(identifier)
            return Response(pub_data, status=status.HTTP_200_OK)
        except Publisher.DoesNotExist:
            return Response({'detail': 'Editorial no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
