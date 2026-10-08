"""
Servicio de dominio para Audiolibros, streaming y persistencia de progreso de escucha / TTS.
RoadmapV3 Sección 30 — Sprint 18: Audiolibros & TTS.
"""
from typing import Any, Dict, List, Optional
from django.db.models import Sum, Count, Q
from django.core.exceptions import ValidationError
from django.utils import timezone

from ..models import Book, AudiobookTrack, UserAudiobookProgress


def format_seconds(seconds: int) -> str:
    """Convierte segundos en formato amigable como '1 h 24 min' o '15 min 30 s'."""
    if seconds <= 0:
        return "0 min"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        if minutes > 0:
            return f"{hours} h {minutes} min"
        return f"{hours} h"
    if minutes > 0:
        if secs > 0:
            return f"{minutes} min {secs} s"
        return f"{minutes} min"
    return f"{secs} s"


def get_book_audiobook_details(book_id: int, user: Optional[Any] = None) -> Dict[str, Any]:
    """
    Recupera la ficha completa del audiolibro de una obra:
    pistas, duración total, narradores, muestra gratuita y progreso del usuario.
    """
    try:
        book = Book.objects.select_related('author').get(pk=book_id)
    except Book.DoesNotExist:
        raise ValidationError(f"No existe ningún libro con el identificador {book_id}")

    tracks_qs = AudiobookTrack.objects.filter(book=book).order_by('track_number')
    tracks_list: List[Dict[str, Any]] = []
    total_seconds = 0
    narrator_set = set()
    sample_track_info: Optional[Dict[str, Any]] = None

    for t in tracks_qs:
        total_seconds += t.duration_seconds
        if t.narrator_name:
            narrator_set.add(t.narrator_name)

        track_data = {
            'id': t.id,
            'title': t.title,
            'track_number': t.track_number,
            'duration_seconds': t.duration_seconds,
            'formatted_duration': t.formatted_duration,
            'stream_url': t.stream_url,
            'narrator_name': t.narrator_name,
            'is_sample': t.is_sample,
        }
        tracks_list.append(track_data)

        if t.is_sample and not sample_track_info:
            sample_track_info = track_data

    # Si no se marcó explícitamente ninguna muestra pero hay pistas, la primera pista sirve de muestra
    if not sample_track_info and tracks_list:
        sample_track_info = tracks_list[0]

    # Datos de accesibilidad TTS si el libro tiene sinopsis
    has_tts = bool(book.description and len(book.description.strip()) > 0)
    tts_word_count = len(book.description.split()) if book.description else 0
    # Estimación ~140 palabras por minuto en locución estándar
    estimated_tts_duration_seconds = int((tts_word_count / 140) * 60) if tts_word_count > 0 else 0

    progress_data: Optional[Dict[str, Any]] = None
    if user and getattr(user, 'is_authenticated', False):
        user_prog = UserAudiobookProgress.objects.filter(user=user, book=book).select_related('current_track').first()
        if user_prog:
            completion_pct = 0.0
            if total_seconds > 0:
                completion_pct = min(100.0, round((user_prog.position_seconds / total_seconds) * 100, 1))

            progress_data = {
                'current_track_id': user_prog.current_track_id,
                'current_track_title': user_prog.current_track.title if user_prog.current_track else None,
                'position_seconds': user_prog.position_seconds,
                'formatted_position': format_seconds(user_prog.position_seconds),
                'playback_speed': user_prog.playback_speed,
                'is_completed': user_prog.is_completed,
                'completion_percentage': completion_pct,
                'last_listened_at': user_prog.last_listened_at.isoformat() if user_prog.last_listened_at else None,
            }

    return {
        'book_id': book.id,
        'book_title': book.title,
        'author_name': book.author.name if book.author else 'Autor desconocido',
        'cover_url': book.cover.url if getattr(book, 'cover', None) and book.cover else None,
        'has_audiobook': len(tracks_list) > 0,
        'tracks_count': len(tracks_list),
        'total_duration_seconds': total_seconds,
        'formatted_total_duration': format_seconds(total_seconds),
        'narrators': sorted(list(narrator_set)),
        'sample_track': sample_track_info,
        'tracks': tracks_list,
        'progress': progress_data,
        'tts': {
            'is_available': has_tts,
            'word_count': tts_word_count,
            'estimated_duration_seconds': estimated_tts_duration_seconds,
            'formatted_estimated_duration': format_seconds(estimated_tts_duration_seconds),
            'text_content': book.description or '',
        },
    }


def save_audiobook_progress(
    user: Any,
    book_id: int,
    track_id: Optional[int] = None,
    position_seconds: int = 0,
    playback_speed: float = 1.0,
    is_completed: bool = False,
) -> Dict[str, Any]:
    """
    Sincroniza y persiste atómicamente el punto de escucha del lector.
    """
    if not user or not user.is_authenticated:
        raise ValidationError("Se requiere autenticación para guardar el progreso de escucha.")

    try:
        book = Book.objects.get(pk=book_id)
    except Book.DoesNotExist:
        raise ValidationError(f"No existe ningún libro con el identificador {book_id}")

    track: Optional[AudiobookTrack] = None
    if track_id:
        try:
            track = AudiobookTrack.objects.get(pk=track_id, book=book)
        except AudiobookTrack.DoesNotExist:
            raise ValidationError(f"La pista {track_id} no pertenece al libro {book_id}")

    # Normalización y validación de parámetros de reproducción
    safe_pos = max(0, int(position_seconds))
    safe_speed = max(0.5, min(3.0, float(playback_speed)))

    progress, _ = UserAudiobookProgress.objects.update_or_create(
        user=user,
        book=book,
        defaults={
            'current_track': track,
            'position_seconds': safe_pos,
            'playback_speed': safe_speed,
            'is_completed': bool(is_completed),
        },
    )

    total_duration = AudiobookTrack.objects.filter(book=book).aggregate(tot=Sum('duration_seconds'))['tot'] or 0
    completion_pct = 0.0
    if total_duration > 0:
        completion_pct = min(100.0, round((safe_pos / total_duration) * 100, 1))

    return {
        'status': 'saved',
        'book_id': book.id,
        'track_id': progress.current_track_id,
        'position_seconds': progress.position_seconds,
        'formatted_position': format_seconds(progress.position_seconds),
        'playback_speed': progress.playback_speed,
        'is_completed': progress.is_completed,
        'completion_percentage': completion_pct,
        'last_listened_at': progress.last_listened_at.isoformat(),
    }


def get_user_listening_shelf(user: Any, limit: int = 15) -> List[Dict[str, Any]]:
    """
    Devuelve los audiolibros escuchados recientemente por el usuario ordenados por fecha.
    """
    if not user or not user.is_authenticated:
        return []

    items = (
        UserAudiobookProgress.objects.filter(user=user)
        .select_related('book', 'book__author', 'current_track')
        .order_by('-last_listened_at')[:limit]
    )

    results = []
    for item in items:
        book = item.book
        total_seconds = AudiobookTrack.objects.filter(book=book).aggregate(tot=Sum('duration_seconds'))['tot'] or 0
        completion_pct = 0.0
        if total_seconds > 0:
            completion_pct = min(100.0, round((item.position_seconds / total_seconds) * 100, 1))

        results.append({
            'book_id': book.id,
            'book_title': book.title,
            'author_name': book.author.name if book.author else 'Autor desconocido',
            'cover_url': book.cover.url if getattr(book, 'cover', None) and book.cover else None,
            'current_track_id': item.current_track_id,
            'current_track_title': item.current_track.title if item.current_track else None,
            'position_seconds': item.position_seconds,
            'formatted_position': format_seconds(item.position_seconds),
            'total_duration_seconds': total_seconds,
            'formatted_total_duration': format_seconds(total_seconds),
            'playback_speed': item.playback_speed,
            'is_completed': item.is_completed,
            'completion_percentage': completion_pct,
            'last_listened_at': item.last_listened_at.isoformat(),
        })

    return results


def get_audiobook_catalog(
    category_id: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
    user: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Explorador/catálogo de libros que cuentan con audiolibro disponible.
    """
    qs = (
        Book.objects.filter(audio_tracks__isnull=False)
        .select_related('author')
        .prefetch_related('audio_tracks', 'categories')
        .distinct()
    )

    if category_id:
        qs = qs.filter(categories__id=category_id)

    total_count = qs.count()
    books = qs[offset : offset + limit]

    results = []
    for book in books:
        tracks = list(book.audio_tracks.all())
        total_seconds = sum(t.duration_seconds for t in tracks)
        narrators = sorted(list({t.narrator_name for t in tracks if t.narrator_name}))
        sample = next((t for t in tracks if t.is_sample), tracks[0] if tracks else None)

        user_progress: Optional[Dict[str, Any]] = None
        if user and getattr(user, 'is_authenticated', False):
            prog = UserAudiobookProgress.objects.filter(user=user, book=book).first()
            if prog:
                pct = min(100.0, round((prog.position_seconds / total_seconds) * 100, 1)) if total_seconds > 0 else 0.0
                user_progress = {
                    'position_seconds': prog.position_seconds,
                    'completion_percentage': pct,
                    'is_completed': prog.is_completed,
                }

        results.append({
            'book_id': book.id,
            'book_title': book.title,
            'author_name': book.author.name if book.author else 'Autor desconocido',
            'cover_url': book.cover.url if getattr(book, 'cover', None) and book.cover else None,
            'tracks_count': len(tracks),
            'total_duration_seconds': total_seconds,
            'formatted_total_duration': format_seconds(total_seconds),
            'narrators': narrators,
            'has_sample': sample is not None,
            'sample_url': sample.stream_url if sample else None,
            'sample_title': sample.title if sample else None,
            'sample_duration': sample.formatted_duration if sample else None,
            'user_progress': user_progress,
        })

    return {
        'total': total_count,
        'limit': limit,
        'offset': offset,
        'results': results,
    }
