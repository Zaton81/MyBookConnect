"""
Versión del proyecto MyBookConnect siguiendo Semantic Versioning 2.0.0 (SemVer).
Esquema: MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
"""

VERSION = (1, 0, 0)
PRERELEASE = None  # ej. 'rc1', 'beta', etc.
API_VERSION = "v1"


def get_version(version=None) -> str:
    """Devuelve la versión formateada en string SemVer 2.0.0 (ej. '1.0.0')."""
    if version is None:
        version = VERSION
    version_str = ".".join(str(x) for x in version[:3])
    if PRERELEASE:
        version_str = f"{version_str}-{PRERELEASE}"
    return version_str


def get_version_info() -> dict:
    """Devuelve un diccionario detallado con los metadatos de versión."""
    return {
        "version": get_version(),
        "major": VERSION[0],
        "minor": VERSION[1],
        "patch": VERSION[2],
        "prerelease": PRERELEASE,
        "api_version": API_VERSION,
        "semver": True,
    }


__version__ = get_version()
