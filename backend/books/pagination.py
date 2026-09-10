from rest_framework.pagination import CursorPagination, PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """
    Paginador estándar para listas basadas en páginas.
    Tamaño por defecto: 20 elementos.
    Soporta personalización mediante el parámetro 'page_size' hasta un máximo de 100 elementos.
    """
    page_size = 20
    page_size_query_param = 'page_size'
    page_query_param = 'page'
    max_page_size = 100


class StandardCursorPagination(CursorPagination):
    """
    Paginador por cursor para feeds y secuencias en tiempo real (mensajes, notificaciones).
    Evita saltos o duplicados ante inserciones concurrentes.
    Ordenación por defecto: cronológica ascendente por fecha de creación.
    """
    page_size = 20
    page_size_query_param = 'page_size'
    cursor_query_param = 'cursor'
    max_page_size = 100
    ordering = 'created_at'
