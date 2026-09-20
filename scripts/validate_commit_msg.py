#!/usr/bin/env python3
"""
validate_commit_msg.py - Validador de Conventional Commits 1.0.0 para MyBookConnect.

Puede invocarse:
1. Directamente con un mensaje:
   python scripts/validate_commit_msg.py "feat(books): anadir filtro por categorias"
2. Como hook de Git commit-msg:
   python scripts/validate_commit_msg.py .git/COMMIT_EDITMSG
"""

import re
import sys
from pathlib import Path
from typing import Tuple

VALID_TYPES = {
    "feat",
    "fix",
    "refactor",
    "test",
    "docs",
    "perf",
    "security",
    "chore",
    "ci",
    "build",
    "style",
    "revert",
}

# Expresión regular para el encabezado de Conventional Commits 1.0.0
COMMIT_HEADER_REGEX = re.compile(
    r"^(?P<type>[a-zA-Z0-9]+)(?:\((?P<scope>[a-zA-Z0-9_\-\/.]+)\))?(?P<breaking>!)?:(?P<space> )?(?P<desc>.*)$"
)

# Prefijos permitidos generados por Git automáticamente
IGNORED_PREFIXES = (
    "Merge branch ",
    "Merge pull request ",
    "Merge remote-tracking ",
    "fixup! ",
    "squash! ",
    "amend! ",
)


def validate_commit_message(msg: str) -> Tuple[bool, str]:
    """
    Valida un mensaje de commit según Conventional Commits 1.0.0.
    Retorna una tupla (es_valido: bool, motivo_o_exito: str).
    """
    # Limpiar líneas comentadas (Git suele incluir comentarios iniciados con #)
    lines = [line.rstrip() for line in msg.splitlines() if not line.strip().startswith("#")]
    non_empty = [line for line in lines if line.strip()]

    if not non_empty:
        return False, "El mensaje de commit no puede estar vacío."

    header = non_empty[0]

    # Ignorar mensajes automáticos de merge o rebases interactivos de Git
    if any(header.startswith(prefix) for prefix in IGNORED_PREFIXES):
        return True, "Mensaje de merge/rebase automático ignorado."

    # 1. Validación de longitud máxima de la cabecera
    if len(header) > 100:
        return (
            False,
            f"La cabecera del commit excede los 100 caracteres (tiene {len(header)} caracteres).\n"
            f"Cabecera: '{header}'",
        )

    # 2. Validación de estructura con regex
    match = COMMIT_HEADER_REGEX.match(header)
    if not match:
        return (
            False,
            "La cabecera no sigue el formato '<tipo>[ámbito][!]: <descripción>'.\n"
            f"Cabecera recibida: '{header}'\n\n"
            "Ejemplo válido:\n"
            "  feat(books): anadir busqueda por trigramas\n"
            "  fix(reviews): redondear promedio de ratings\n"
            "  security(auth): revocar tokens en lista negra",
        )

    commit_type = match.group("type")
    has_space = match.group("space") is not None
    desc = match.group("desc")

    # 3. Comprobar que el tipo esté en minúsculas
    if commit_type != commit_type.lower():
        return (
            False,
            f"El tipo de commit '{commit_type}' debe estar estrictamente en minúsculas (ej. '{commit_type.lower()}').",
        )

    # 4. Validación de tipo permitido
    if commit_type not in VALID_TYPES:
        types_list = ", ".join(sorted(VALID_TYPES))
        return (
            False,
            f"Tipo de commit '{commit_type}' no reconocido.\n"
            f"Tipos permitidos: {types_list}",
        )

    # 5. Comprobar que la descripción no esté vacía
    if not desc.strip():
        return False, "La descripción del commit no puede estar vacía."

    # 6. Comprobar espacio tras los dos puntos
    if not has_space:
        return (
            False,
            "Falta el espacio obligatorio después de los dos puntos (': ').",
        )

    # 7. Comprobar que la descripción no termine en punto
    if desc.endswith("."):
        return (
            False,
            "La descripción del commit no debe terminar con un punto final ('.').",
        )

    return True, f"Commit válido: [{commit_type}] {desc}"


def main() -> int:
    # Asegurar compatibilidad de salida en terminales Windows
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    if len(sys.argv) < 2:
        print("Uso: python validate_commit_msg.py <mensaje_o_ruta_a_archivo>")
        return 1

    arg = sys.argv[1]
    path = Path(arg)

    if path.exists() and path.is_file():
        commit_text = path.read_text(encoding="utf-8")
    else:
        commit_text = arg

    is_valid, reason = validate_commit_message(commit_text)
    if is_valid:
        print(f"[OK] {reason}")
        return 0
    else:
        print(f"[ERROR] Error en convención de commit:\n{reason}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
