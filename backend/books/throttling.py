"""
Clases de throttling especializadas para el dominio editorial y catálogo de libros (Fase A3).
Protege endpoints de alto consumo computacional y llamadas a APIs de terceros.
"""
from mybookconnect.throttling import ResilientUserRateThrottle


class BookImportThrottle(ResilientUserRateThrottle):
    """
    Limita la tasa de importaciones de bibliotecas (CSV) o sincronizaciones masivas.
    Tasa estándar: 10/hora por usuario autenticado.
    """
    scope = 'book_import'


class EnrichmentThrottle(ResilientUserRateThrottle):
    """
    Limita la tasa de enriquecimiento y sincronización externa bajo demanda.
    Tasa estándar: 20/hora por usuario autenticado.
    """
    scope = 'enrichment'


class AuthorClaimThrottle(ResilientUserRateThrottle):
    """
    Limita el envío de reclamos de perfil de autor para prevenir spam y sobrecarga a moderadores.
    Tasa estándar: 5/hora por usuario autenticado.
    """
    scope = 'author_claims'
