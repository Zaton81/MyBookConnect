"""
Database Routers para MyBookConnect (Fase 30 — Escalabilidad).
Permite la segregación de lecturas y escrituras hacia réplicas de PostgreSQL
manteniendo la consistencia y transaccionalidad con la base de datos primaria.
"""
from typing import Any

from django.conf import settings


class PrimaryReplicaRouter:
    """
    Enruta las operaciones de lectura hacia la base de datos réplica (si está configurada)
    y todas las operaciones de escritura hacia la base de datos primaria ('default').
    """

    def db_for_read(self, model: Any, **hints: Any) -> str:
        """
        Dirige las lecturas a 'replica' si existe en settings.DATABASES,
        de lo contrario utiliza 'default'.
        """
        if 'replica' in getattr(settings, 'DATABASES', {}):
            return 'replica'
        return 'default'

    def db_for_write(self, model: Any, **hints: Any) -> str:
        """
        Todas las operaciones de escritura deben ejecutarse siempre en la base de datos primaria.
        """
        return 'default'

    def allow_relation(self, obj1: Any, obj2: Any, **hints: Any) -> bool:
        """
        Permite relaciones entre objetos siempre que ambas bases de datos formen parte
        del conjunto maestro-réplica ('default' y 'replica').
        """
        db_set = {'default', 'replica'}
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return None

    def allow_migrate(self, db: str, app_label: str, model_name: str | None = None, **hints: Any) -> bool:
        """
        Las migraciones de esquema sólo deben ejecutarse en la base de datos primaria ('default').
        Las réplicas se sincronizan mediante replicación física por streaming (WAL) de PostgreSQL.
        """
        return db == 'default'
