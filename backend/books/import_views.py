from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from books.services.csv_import_service import CSVImportService
from mybookconnect.idempotency import idempotent


class CSVImportPreviewView(APIView):
    """
    Analiza un archivo CSV (Goodreads, Calibre o estándar) y genera una previsualización
    con validaciones, detección de duplicados en catálogo y en biblioteca personal (Fase 55).
    """
    permission_classes = (permissions.IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    @extend_schema(
        summary="Previsualizar importación de biblioteca CSV",
        description="Recibe un archivo CSV de Goodreads, Calibre o estándar y devuelve la previsualización clasificada.",
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {
                        'type': 'string',
                        'format': 'binary',
                    },
                },
                'required': ['file'],
            },
        },
        responses={
            200: OpenApiResponse(description="Previsualización generada correctamente"),
            400: OpenApiResponse(description="Archivo inválido o sin datos legibles"),
        },
        tags=['Books Import'],
    )
    def post(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response(
                {'detail': 'Debe adjuntar un archivo CSV en el campo "file".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not uploaded_file.name.lower().endswith(('.csv', '.txt')):
            return Response(
                {'detail': 'Formato no soportado. El archivo debe ser de tipo CSV o texto plano delimitado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            content = uploaded_file.read()
            preview = CSVImportService.parse_and_preview_csv(content, request.user)
            return Response(preview, status=status.HTTP_200_OK)
        except ValueError as ve:
            return Response({'detail': str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {'detail': f'Error al procesar el archivo CSV: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CSVImportConfirmView(APIView):
    """
    Ejecuta la importación atómica e idempotente de los libros previsualizados (Fase 55 y 56).
    """
    permission_classes = (permissions.IsAuthenticated,)
    parser_classes = (JSONParser,)

    @extend_schema(
        summary="Confirmar y ejecutar importación masiva de biblioteca",
        description="Aplica la creación y actualización atómica en la biblioteca del usuario.",
        request=inline_serializer(
            name='CSVImportConfirmRequest',
            fields={
                'items': serializers.ListField(child=serializers.DictField()),
                'update_existing': serializers.BooleanField(default=True),
            },
        ),
        responses={
            200: OpenApiResponse(description="Importación completada con éxito"),
            400: OpenApiResponse(description="Datos de importación inválidos"),
        },
        tags=['Books Import'],
    )
    @idempotent(required=False)
    def post(self, request, *args, **kwargs):
        items = request.data.get('items')
        if not items or not isinstance(items, list):
            return Response(
                {'detail': 'Debe proporcionar una lista de elementos válidos en el campo "items".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        update_existing = bool(request.data.get('update_existing', True))

        try:
            result = CSVImportService.execute_csv_import(
                items=items,
                user=request.user,
                update_existing=update_existing,
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'detail': f'Error durante la transacción de importación: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
