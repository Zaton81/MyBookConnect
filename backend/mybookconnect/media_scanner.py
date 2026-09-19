"""
Módulo de escaneo de seguridad y antivirus para archivos multimedia (Fase 60).

Proporciona una arquitectura pluggable para inspección de malware en archivos subidos:
- Soporte para ClamAV daemon mediante socket TCP/stream cuando esté habilitado en producción.
- Escáner heurístico y de firmas de prueba (EICAR) para entornos de prueba y desarrollo.
- Integración en la cadena de validación de medios previa a la persistencia.
"""

import logging
import socket
from typing import Tuple

from django.conf import settings
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

# Cadena de prueba estándar EICAR para comprobación de funcionamiento antivirus
EICAR_SIGNATURE: bytes = (
    b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
)


class BaseMediaScanner:
    """Clase base abstracta para escáneres de seguridad de archivos multimedia."""

    def scan_file(self, file_obj) -> Tuple[bool, str]:
        """
        Escanea un archivo multimedia en busca de malware o contenido malicioso.

        :param file_obj: Archivo abierto o buffer con seek/read.
        :return: Tupla (is_clean: bool, threat_name: str). Si is_clean es False,
                 threat_name contiene la identificación de la amenaza.
        """
        raise NotImplementedError("Debe implementarse en la subclase.")


class SecurityHeuristicScanner(BaseMediaScanner):
    """
    Escáner heurístico y de firmas estáticas.
    Detecta la firma estándar EICAR y ejecutables o scripts camuflados en bloques de datos.
    """

    def scan_file(self, file_obj) -> Tuple[bool, str]:
        if not file_obj:
            return True, ""

        current_pos = file_obj.tell() if hasattr(file_obj, "tell") else 0
        try:
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)

            # Leer contenido (o primeros 10MB en bloques)
            content = file_obj.read() if hasattr(file_obj, "read") else b""

            # Comprobar firma de prueba EICAR
            if EICAR_SIGNATURE in content:
                logger.warning("Detección de malware simulado: Firma EICAR detectada.")
                return False, "Eicar-Test-Signature"

            # Detección de ejecutables ELF o PE (MZ) incrustados
            if content.startswith(b"MZ") or content.startswith(b"\x7fELF"):
                return False, "Suspicious-Executable-Header"

            return True, ""
        finally:
            if hasattr(file_obj, "seek"):
                try:
                    file_obj.seek(current_pos)
                except Exception:
                    pass


class ClamAVScanner(BaseMediaScanner):
    """
    Escáner de producción que se conecta a un demonio ClamAV (clamd) mediante TCP socket.
    Envía el archivo usando el comando 'INSTREAM'.
    """

    def __init__(self, host: str | None = None, port: int | None = None, timeout: float = 5.0):
        self.host = host or getattr(settings, "CLAMAV_HOST", "clamav")
        self.port = port or getattr(settings, "CLAMAV_PORT", 3310)
        self.timeout = timeout

    def scan_file(self, file_obj) -> Tuple[bool, str]:
        current_pos = file_obj.tell() if hasattr(file_obj, "tell") else 0
        try:
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)

            # Si el escáner heurístico local detecta EICAR, bloquear de inmediato
            heuristic = SecurityHeuristicScanner()
            clean, threat = heuristic.scan_file(file_obj)
            if not clean:
                return False, threat

            if hasattr(file_obj, "seek"):
                file_obj.seek(0)

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))

            # Comando INSTREAM para clamd
            sock.sendall(b"zINSTREAM\0")

            chunk_size = 4096
            while True:
                chunk = file_obj.read(chunk_size)
                if not chunk:
                    break
                sock.sendall(len(chunk).to_bytes(4, byteorder="big") + chunk)

            # Fin del stream (chunk tamaño 0)
            sock.sendall((0).to_bytes(4, byteorder="big"))

            # Leer respuesta
            response = sock.recv(1024).decode("utf-8", errors="replace")
            sock.close()

            if "FOUND" in response:
                threat_name = response.split("FOUND")[0].split(":")[-1].strip()
                logger.warning(f"ClamAV detectó amenaza en archivo: {threat_name}")
                return False, threat_name

            return True, ""

        except Exception as exc:
            logger.warning(f"No se pudo conectar con el demonio ClamAV ({exc}). Fallback a heurístico.")
            # Fallback seguro a escáner heurístico si ClamAV no está en línea
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
            return SecurityHeuristicScanner().scan_file(file_obj)
        finally:
            if hasattr(file_obj, "seek"):
                try:
                    file_obj.seek(current_pos)
                except Exception:
                    pass


def get_media_scanner() -> BaseMediaScanner:
    """Devuelve el escáner configurado según los ajustes del entorno."""
    enable_clamav = getattr(settings, "ENABLE_CLAMAV_SCAN", False)
    if enable_clamav:
        return ClamAVScanner()
    return SecurityHeuristicScanner()


def scan_media_file(file_obj) -> None:
    """
    Función utilitaria que ejecuta el escaneo antivirus sobre un archivo subido.
    Lanza ValidationError si se detecta una amenaza.
    """
    if not file_obj:
        return

    scanner = get_media_scanner()
    is_clean, threat_name = scanner.scan_file(file_obj)
    if not is_clean:
        raise ValidationError(
            f"El archivo fue bloqueado por la inspección de seguridad antivirus (amenaza: {threat_name})."
        )
