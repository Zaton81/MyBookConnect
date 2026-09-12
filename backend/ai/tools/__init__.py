"""
Módulo de herramientas seguras (Function / Tool Calling) para el asistente de IA.
"""

from ai.tools.base import (
    AITool,
    ToolExecutionError,
    ToolPermissionDeniedError,
)
from ai.tools.registry import (
    AddToWishlistTool,
    BookDetailTool,
    CatalogSearchTool,
    UserReadingStatusTool,
    execute_tool,
    get_registered_tools,
    get_tools_definitions,
)

__all__ = [
    'AITool',
    'ToolExecutionError',
    'ToolPermissionDeniedError',
    'CatalogSearchTool',
    'BookDetailTool',
    'UserReadingStatusTool',
    'AddToWishlistTool',
    'execute_tool',
    'get_registered_tools',
    'get_tools_definitions',
]
