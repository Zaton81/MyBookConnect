"""
Clase base para herramientas ejecutables del asistente de IA (AITool).

Define el contrato para Function Calling seguro mediado exclusivamente por el backend.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class ToolExecutionError(Exception):
    """Excepción lanzada cuando ocurre un error controlado al ejecutar una herramienta."""
    pass


class ToolPermissionDeniedError(ToolExecutionError):
    """Excepción lanzada cuando el usuario carece de permisos para invocar la herramienta."""
    pass


class AITool(ABC):
    """
    Herramienta segura invocable por el asistente de IA con mediación y validación del backend.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre único de la herramienta en snake_case (ej: 'catalog_search')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Descripción concisa de la función para el modelo de lenguaje."""
        pass

    @property
    @abstractmethod
    def parameters_schema(self) -> dict[str, Any]:
        """Esquema JSON Schema que describe los argumentos aceptados."""
        pass

    @property
    def requires_auth(self) -> bool:
        """Indica si la herramienta requiere que el usuario esté autenticado."""
        return True

    @property
    def required_role(self) -> str | None:
        """Rol requerido opcional ('staff', 'editor', None)."""
        return None

    def validate_permissions(self, user: Any) -> None:
        """
        Comprueba que el usuario tenga los permisos necesarios antes de ejecutar la herramienta.

        :param user: Instancia del usuario que realiza la petición.
        :raises ToolPermissionDeniedError: Si el usuario no cumple los requisitos de seguridad.
        """
        if self.requires_auth:
            if not user or not getattr(user, 'is_authenticated', False):
                raise ToolPermissionDeniedError(
                    f"La herramienta '{self.name}' requiere autenticación previa."
                )

        if self.required_role == 'staff':
            if not getattr(user, 'is_staff', False):
                raise ToolPermissionDeniedError(
                    f"La herramienta '{self.name}' requiere permisos de administración (staff)."
                )
        elif self.required_role == 'editor':
            is_editor = getattr(user, 'is_editor', False) or getattr(user, 'is_staff', False)
            if not is_editor:
                raise ToolPermissionDeniedError(
                    f"La herramienta '{self.name}' requiere rol de editor o staff."
                )

    @abstractmethod
    def execute(self, user: Any, **kwargs: Any) -> dict[str, Any]:
        """
        Ejecuta la lógica de la herramienta de forma segura en el backend.

        :param user: Usuario autenticado.
        :param kwargs: Argumentos validados provistos para la herramienta.
        :return: Diccionario con los datos resultantes de la ejecución.
        """
        pass

    def to_openai_tool(self) -> dict[str, Any]:
        """
        Genera la definición de la herramienta en formato compatible con OpenAI Function Calling.

        :return: Diccionario con la estructura de Tool de OpenAI.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            },
        }
