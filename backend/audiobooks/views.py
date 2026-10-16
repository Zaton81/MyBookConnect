from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services


class BookAudiobookDetailView(APIView):
    """
    Devuelve la información de pistas de audiolibro de una obra,
    muestra gratuita, duración total y progreso del usuario autenticado.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        try:
            data = services.get_book_audiobook_details(pk, user=request.user)
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_404_NOT_FOUND)


class BookAudiobookProgressView(APIView):
    """
    Sincroniza y persiste el punto de escucha del usuario:
    segundo actual, pista en curso, velocidad de reproducción y completitud.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            track_id = request.data.get('track_id')
            position_seconds = int(request.data.get('position_seconds', 0))
            playback_speed = float(request.data.get('playback_speed', 1.0))
            is_completed = bool(request.data.get('is_completed', False))

            res = services.save_audiobook_progress(
                user=request.user,
                book_id=pk,
                track_id=track_id,
                position_seconds=position_seconds,
                playback_speed=playback_speed,
                is_completed=is_completed,
            )
            return Response(res, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AudiobookCatalogView(APIView):
    """
    Explorador/catálogo público de audiolibros con filtros por categoría.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        category_id = request.query_params.get('category_id')
        limit = min(50, int(request.query_params.get('limit', 20)))
        offset = max(0, int(request.query_params.get('offset', 0)))

        cat_id_int = int(category_id) if category_id and category_id.isdigit() else None
        catalog = services.get_audiobook_catalog(
            category_id=cat_id_int,
            limit=limit,
            offset=offset,
            user=request.user,
        )
        return Response(catalog, status=status.HTTP_200_OK)


class UserAudiobookShelfView(APIView):
    """
    Devuelve los audiolibros en progreso del lector autenticado.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        limit = min(50, int(request.query_params.get('limit', 15)))
        items = services.get_user_listening_shelf(request.user, limit=limit)
        return Response({'results': items, 'count': len(items)}, status=status.HTTP_200_OK)
