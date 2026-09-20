"""
Fase 43: Utilidades de perfilado de rendimiento y EXPLAIN ANALYZE para PostgreSQL.
Permite inspeccionar planes de ejecución reales, tiempos de planificación/ejecución,
uso de búferes de memoria y verificación de uso de índices frente a escaneos secuenciales.
"""
import json
import logging
from typing import Any, Dict, List, Optional, Union

from django.db import connection
from django.db.models import QuerySet

logger = logging.getLogger('mybookconnect.performance')


class QueryProfiler:
    """
    Herramienta de análisis de rendimiento para consultas PostgreSQL usando EXPLAIN ANALYZE.
    """

    @staticmethod
    def explain_analyze(
        query_or_queryset: Union[QuerySet, str],
        params: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """
        Ejecuta EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) sobre un QuerySet de Django o una consulta SQL cruda.

        Retorna un diccionario con:
        - raw_plan: El plan de ejecución completo devuelto por PostgreSQL en JSON.
        - execution_time_ms: Tiempo de ejecución en milisegundos.
        - planning_time_ms: Tiempo de planificación en milisegundos.
        - total_cost: Coste estimado total.
        - root_node_type: Tipo del nodo raíz (p. ej. 'Sort', 'Bitmap Heap Scan', 'Seq Scan').
        - index_scans_used: Lista de nombres de índices empleados en los nodos del árbol.
        - uses_seq_scan: Booleano indicando si algún nodo del plan recurrió a escaneo secuencial.
        """
        if isinstance(query_or_queryset, QuerySet):
            sql, sql_params = query_or_queryset.query.sql_with_params()
        else:
            sql = query_or_queryset
            sql_params = params or []

        explain_sql = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}"

        with connection.cursor() as cursor:
            cursor.execute(explain_sql, sql_params)
            result = cursor.fetchall()

        # En PostgreSQL con FORMAT JSON, el resultado viene como un string JSON o estructura en la primera columna
        raw_output = result[0][0]
        if isinstance(raw_output, str):
            plan_data = json.loads(raw_output)[0]
        elif isinstance(raw_output, list):
            plan_data = raw_output[0]
        else:
            plan_data = raw_output

        plan_node = plan_data.get('Plan', {})
        planning_time = plan_data.get('Planning Time', 0.0)
        execution_time = plan_data.get('Execution Time', 0.0)

        index_names: List[str] = []
        seq_scan_found = False

        def traverse_nodes(node: Dict[str, Any]):
            nonlocal seq_scan_found
            node_type = node.get('Node Type', '')
            if 'Seq Scan' in node_type:
                seq_scan_found = True
            if 'Index' in node_type:
                idx = node.get('Index Name')
                if idx and idx not in index_names:
                    index_names.append(idx)
            for child in node.get('Plans', []):
                traverse_nodes(child)

        traverse_nodes(plan_node)

        return {
            'execution_time_ms': execution_time,
            'planning_time_ms': planning_time,
            'total_cost': plan_node.get('Total Cost', 0.0),
            'root_node_type': plan_node.get('Node Type', ''),
            'index_scans_used': index_names,
            'uses_seq_scan': seq_scan_found,
            'plan': plan_node,
        }

    @classmethod
    def profile_book_search(cls, search_term: str) -> Dict[str, Any]:
        """Perfila la consulta de búsqueda de libros por término o trigrama."""
        from books.models import Book
        qs = Book.objects.filter(title__icontains=search_term).select_related('author')
        return cls.explain_analyze(qs)

    @classmethod
    def profile_user_library(cls, user_id: int) -> Dict[str, Any]:
        """Perfila la consulta de la biblioteca personal de un usuario."""
        from books.models import UserBook
        qs = (
            UserBook.objects.filter(user_id=user_id)
            .select_related('book', 'book__author')
            .order_by('-updated_at')
        )
        return cls.explain_analyze(qs)

    @classmethod
    def profile_book_reviews(cls, book_id: int) -> Dict[str, Any]:
        """Perfila la consulta de reseñas de un libro con sus usuarios."""
        from books.models import Review
        qs = (
            Review.objects.filter(book_id=book_id)
            .select_related('user', 'book', 'book__author')
            .order_by('-created_at')
        )
        return cls.explain_analyze(qs)
