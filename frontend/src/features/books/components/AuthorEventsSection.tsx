import React, { useEffect, useState } from 'react';
import { Spinner, Modal, Button } from 'flowbite-react';
import {
  HiOutlineLocationMarker,
  HiOutlineVideoCamera,
  HiOutlineUsers,
  HiOutlinePlus,
  HiOutlineCheck,
  HiOutlineClock,
  HiOutlineChatAlt2,
  HiOutlineX,
} from 'react-icons/hi';
import { useAuthStore } from '../../../store/auth';

export interface AuthorEventItem {
  id: number;
  author: number;
  author_name: string;
  author_photo?: string | null;
  created_by: number;
  created_by_username: string;
  book?: number | null;
  book_title?: string | null;
  book_cover?: string | null;
  title: string;
  description: string;
  event_type: 'BOOK_LAUNCH' | 'SIGNING' | 'QA_SESSION' | 'READING' | 'WORKSHOP' | 'OTHER';
  event_type_display: string;
  event_format: 'ONLINE' | 'IN_PERSON' | 'HYBRID';
  event_format_display: string;
  start_time: string;
  end_time?: string | null;
  event_timezone: string;
  location_name?: string;
  location_address?: string;
  online_url?: string;
  max_attendees?: number | null;
  is_cancelled: boolean;
  registered_count: number;
  waitlist_count: number;
  is_full: boolean;
  user_registration_status?: 'REGISTERED' | 'WAITLIST' | 'CANCELLED' | null;
  is_user_registered: boolean;
  user_notes?: string | null;
  created_at: string;
}

export interface AttendeeDetail {
  id: number;
  event: number;
  user: number;
  username: string;
  user_avatar?: string | null;
  status: 'REGISTERED' | 'WAITLIST' | 'CANCELLED';
  status_display: string;
  notes: string;
  created_at: string;
}

interface AuthorEventsSectionProps {
  authorId: number;
  authorName: string;
  isAuthorOwner: boolean;
  books: { id: number; title: string; cover?: string }[];
}

export const AuthorEventsSection: React.FC<AuthorEventsSectionProps> = ({
  authorId,
  authorName,
  isAuthorOwner,
  books,
}) => {
  const { token } = useAuthStore();
  const [events, setEvents] = useState<AuthorEventItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterMode, setFilterMode] = useState<'upcoming' | 'past'>('upcoming');
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);

  // Modal Inscribirse
  const [selectedEventForRegister, setSelectedEventForRegister] = useState<AuthorEventItem | null>(null);
  const [registerNotes, setRegisterNotes] = useState('');
  const [submittingRegister, setSubmittingRegister] = useState(false);

  // Modal Crear Evento
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [createForm, setCreateForm] = useState({
    title: '',
    description: '',
    book: '',
    event_type: 'BOOK_LAUNCH',
    event_format: 'ONLINE',
    start_time: '',
    end_time: '',
    event_timezone: 'Europe/Madrid',
    location_name: '',
    location_address: '',
    online_url: '',
    max_attendees: '',
  });
  const [submittingCreate, setSubmittingCreate] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Modal Ver Asistentes
  const [viewingAttendeesEvent, setViewingAttendeesEvent] = useState<AuthorEventItem | null>(null);
  const [attendeesList, setAttendeesList] = useState<AttendeeDetail[]>([]);
  const [loadingAttendees, setLoadingAttendees] = useState(false);

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  const loadEvents = async () => {
    try {
      setLoading(true);
      const headers: Record<string, string> = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const upcomingParam = filterMode === 'upcoming' ? 'upcoming=true' : 'past=true';
      const res = await fetch(`${apiUrl}/api/v1/books/author-events/?author=${authorId}&${upcomingParam}`, {
        headers,
      });
      if (res.ok) {
        const data = await res.json();
        const list = Array.isArray(data) ? data : data.results || [];
        setEvents(list);
      }
    } catch (e) {
      console.error('Error al cargar eventos del autor:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvents();
  }, [authorId, filterMode, token]);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !selectedEventForRegister) return;

    try {
      setSubmittingRegister(true);
      const res = await fetch(`${apiUrl}/api/v1/books/author-events/${selectedEventForRegister.id}/register/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ notes: registerNotes.trim() }),
      });
      if (res.ok) {
        setSelectedEventForRegister(null);
        setRegisterNotes('');
        await loadEvents();
      } else {
        const err = await res.json();
        alert(err.detail || 'Error al registrarte');
      }
    } catch (e) {
      console.error(e);
      alert('Error de conexión');
    } finally {
      setSubmittingRegister(false);
    }
  };

  const handleCancelRegistration = async (eventId: number) => {
    if (!token) return;
    if (!confirm('¿Deseas cancelar tu inscripción a este evento?')) return;

    try {
      setActionLoadingId(eventId);
      const res = await fetch(`${apiUrl}/api/v1/books/author-events/${eventId}/cancel_registration/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.ok) {
        await loadEvents();
      } else {
        const err = await res.json();
        alert(err.detail || 'Error al cancelar la inscripción');
      }
    } catch (e) {
      console.error(e);
      alert('Error de conexión');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleOpenAttendees = async (event: AuthorEventItem) => {
    setViewingAttendeesEvent(event);
    setLoadingAttendees(true);
    try {
      const headers: Record<string, string> = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const res = await fetch(`${apiUrl}/api/v1/books/author-events/${event.id}/attendees/`, { headers });
      if (res.ok) {
        const data = await res.json();
        setAttendeesList(Array.isArray(data) ? data : data.results || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingAttendees(false);
    }
  };

  const handleCreateEvent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;

    if (!createForm.title.trim() || !createForm.description.trim() || !createForm.start_time) {
      setCreateError('Por favor completa el título, descripción y fecha/hora de inicio.');
      return;
    }

    try {
      setSubmittingCreate(true);
      setCreateError(null);

      const payload: any = {
        author: authorId,
        title: createForm.title.trim(),
        description: createForm.description.trim(),
        event_type: createForm.event_type,
        event_format: createForm.event_format,
        start_time: new Date(createForm.start_time).toISOString(),
        event_timezone: createForm.event_timezone || 'Europe/Madrid',
      };

      if (createForm.end_time) {
        payload.end_time = new Date(createForm.end_time).toISOString();
      }
      if (createForm.book) {
        payload.book = Number(createForm.book);
      }
      if (createForm.location_name.trim()) {
        payload.location_name = createForm.location_name.trim();
      }
      if (createForm.location_address.trim()) {
        payload.location_address = createForm.location_address.trim();
      }
      if (createForm.online_url.trim()) {
        payload.online_url = createForm.online_url.trim();
      }
      if (createForm.max_attendees.trim()) {
        payload.max_attendees = Number(createForm.max_attendees);
      }

      const res = await fetch(`${apiUrl}/api/v1/books/author-events/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        setIsCreateModalOpen(false);
        setCreateForm({
          title: '',
          description: '',
          book: '',
          event_type: 'BOOK_LAUNCH',
          event_format: 'ONLINE',
          start_time: '',
          end_time: '',
          event_timezone: 'Europe/Madrid',
          location_name: '',
          location_address: '',
          online_url: '',
          max_attendees: '',
        });
        await loadEvents();
      } else {
        const errData = await res.json();
        const msg = Object.entries(errData)
          .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(' ') : v}`)
          .join('\n');
        setCreateError(msg || 'No se pudo crear el evento.');
      }
    } catch (e: any) {
      setCreateError(e.message || 'Error de conexión');
    } finally {
      setSubmittingCreate(false);
    }
  };

  const formatEventDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('es-ES', {
        weekday: 'short',
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  const getFormatBadge = (fmt: string) => {
    switch (fmt) {
      case 'ONLINE':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
            <HiOutlineVideoCamera className="w-3.5 h-3.5" /> Virtual
          </span>
        );
      case 'IN_PERSON':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
            <HiOutlineLocationMarker className="w-3.5 h-3.5" /> Presencial
          </span>
        );
      case 'HYBRID':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
            🔀 Híbrido
          </span>
        );
      default:
        return null;
    }
  };

  const getTypeBadge = (t: string) => {
    const map: Record<string, { label: string; icon: string }> = {
      BOOK_LAUNCH: { label: 'Presentación', icon: '🚀' },
      SIGNING: { label: 'Firma de libros', icon: '✍️' },
      QA_SESSION: { label: 'Preguntas y Respuestas (Q&A)', icon: '💬' },
      READING: { label: 'Lectura pública', icon: '📖' },
      WORKSHOP: { label: 'Taller literario', icon: '🛠️' },
      OTHER: { label: 'Encuentro', icon: '📅' },
    };
    const info = map[t] || { label: t, icon: '📅' };
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200">
        <span>{info.icon}</span>
        <span>{info.label}</span>
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header de la sección de eventos */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200/80 dark:border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <span>🎟️</span>
            <span>Encuentros y Eventos Literarios</span>
            <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-teal-100 text-teal-800 dark:bg-teal-900/40 dark:text-teal-300">
              {events.length}
            </span>
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Presentaciones en vivo, firmas de ejemplares y sesiones de preguntas con {authorName}.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Selector de Próximos / Pasados */}
          <div className="bg-slate-100 dark:bg-slate-800 p-1 rounded-xl flex items-center gap-1 text-xs font-semibold">
            <button
              onClick={() => setFilterMode('upcoming')}
              className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                filterMode === 'upcoming'
                  ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                  : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
            >
              Próximos
            </button>
            <button
              onClick={() => setFilterMode('past')}
              className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                filterMode === 'past'
                  ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                  : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
            >
              Histórico
            </button>
          </div>

          {/* Botón Crear Evento para el Autor */}
          {isAuthorOwner && (
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs px-3.5 py-2 rounded-xl transition-all shadow-sm hover:shadow flex items-center gap-1.5 cursor-pointer"
            >
              <HiOutlinePlus className="w-4 h-4" />
              <span>Crear Evento</span>
            </button>
          )}
        </div>
      </div>

      {/* Listado de Eventos */}
      {loading ? (
        <div className="py-12 flex justify-center">
          <Spinner size="lg" color="teal" />
        </div>
      ) : events.length === 0 ? (
        <div className="text-center p-8 bg-white dark:bg-slate-900 rounded-3xl border border-slate-200/80 dark:border-slate-800 text-slate-500 text-sm space-y-2">
          <div className="text-3xl">🗓️</div>
          <p className="font-semibold text-slate-700 dark:text-slate-300">
            {filterMode === 'upcoming'
              ? 'No hay eventos programados próximamente para este autor.'
              : 'No hay eventos pasados en el historial.'}
          </p>
          <p className="text-xs text-slate-400">
            {isAuthorOwner
              ? 'Puedes programar una presentación o sesión de preguntas para interactuar con tus lectores.'
              : 'Sigue a este autor para recibir notificaciones cuando programe una nueva firma o presentación.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {events.map((event) => {
            const isRegistered = event.user_registration_status === 'REGISTERED';
            const isWaitlist = event.user_registration_status === 'WAITLIST';

            return (
              <div
                key={event.id}
                className="bg-white dark:bg-slate-900 rounded-3xl p-5 border border-slate-200/80 dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between space-y-4"
              >
                <div className="space-y-3">
                  {/* Fila superior: Badges */}
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      {getTypeBadge(event.event_type)}
                      {getFormatBadge(event.event_format)}
                    </div>
                    {event.is_cancelled && (
                      <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300">
                        Cancelado
                      </span>
                    )}
                  </div>

                  {/* Título y descripción */}
                  <div>
                    <h3 className="text-base font-bold text-slate-900 dark:text-white leading-snug">
                      {event.title}
                    </h3>
                    <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 line-clamp-3">
                      {event.description}
                    </p>
                  </div>

                  {/* Libro relacionado si aplica */}
                  {event.book_title && (
                    <div className="flex items-center gap-2 p-2 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 text-xs">
                      {event.book_cover ? (
                        <img
                          src={event.book_cover}
                          alt={event.book_title}
                          className="w-7 h-10 object-cover rounded shadow-sm shrink-0"
                        />
                      ) : (
                        <div className="w-7 h-10 bg-teal-700 text-white flex items-center justify-center text-[10px] font-bold rounded shrink-0">
                          📖
                        </div>
                      )}
                      <div className="truncate">
                        <span className="text-[10px] text-slate-400 block font-semibold">Libro presentado:</span>
                        <span className="font-bold text-slate-800 dark:text-slate-200 truncate block">
                          {event.book_title}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Fecha, Hora y Ubicación */}
                  <div className="space-y-1.5 text-xs text-slate-600 dark:text-slate-300">
                    <div className="flex items-center gap-2">
                      <HiOutlineClock className="w-4 h-4 text-teal-600 shrink-0" />
                      <span className="font-semibold">{formatEventDate(event.start_time)}</span>
                      <span className="text-[11px] text-slate-400 font-normal">({event.event_timezone})</span>
                    </div>

                    {event.location_name && (
                      <div className="flex items-center gap-2">
                        <HiOutlineLocationMarker className="w-4 h-4 text-rose-500 shrink-0" />
                        <span className="truncate">{event.location_name}</span>
                        {event.location_address && (
                          <span className="text-slate-400 truncate">• {event.location_address}</span>
                        )}
                      </div>
                    )}

                    {event.online_url && (
                      <div className="flex items-center gap-2">
                        <HiOutlineVideoCamera className="w-4 h-4 text-sky-500 shrink-0" />
                        <a
                          href={event.online_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-teal-600 hover:underline font-semibold truncate"
                        >
                          Enlace a la sesión virtual
                        </a>
                      </div>
                    )}

                    {/* Capacidad y Aforo */}
                    <div className="flex items-center gap-2 pt-1">
                      <HiOutlineUsers className="w-4 h-4 text-indigo-500 shrink-0" />
                      {event.max_attendees ? (
                        <span>
                          <strong className="text-slate-900 dark:text-white">{event.registered_count}</strong> / {event.max_attendees} plazas reservadas
                          {event.waitlist_count > 0 && (
                            <span className="text-amber-600 dark:text-amber-400 ml-1.5 font-semibold">
                              ({event.waitlist_count} en lista de espera)
                            </span>
                          )}
                        </span>
                      ) : (
                        <span>
                          <strong className="text-slate-900 dark:text-white">{event.registered_count}</strong> inscritos (sin aforo limitado)
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Barra de Acciones */}
                <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    {/* Botón de inscripción si no es el autor organizador */}
                    {isRegistered ? (
                      <div className="flex items-center gap-2">
                        <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-bold bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300">
                          <HiOutlineCheck className="w-4 h-4 text-emerald-600" />
                          Inscrito
                        </span>
                        <button
                          onClick={() => handleCancelRegistration(event.id)}
                          disabled={actionLoadingId === event.id}
                          className="text-xs font-semibold text-rose-600 hover:text-rose-700 dark:text-rose-400 hover:underline cursor-pointer"
                        >
                          {actionLoadingId === event.id ? 'Cancelando...' : 'Cancelar plaza'}
                        </button>
                      </div>
                    ) : isWaitlist ? (
                      <div className="flex items-center gap-2">
                        <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-bold bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300">
                          ⏳ Lista de espera
                        </span>
                        <button
                          onClick={() => handleCancelRegistration(event.id)}
                          disabled={actionLoadingId === event.id}
                          className="text-xs font-semibold text-rose-600 hover:text-rose-700 dark:text-rose-400 hover:underline cursor-pointer"
                        >
                          {actionLoadingId === event.id ? 'Cancelando...' : 'Salir de lista'}
                        </button>
                      </div>
                    ) : (
                      token &&
                      !event.is_cancelled && (
                        <button
                          onClick={() => {
                            setSelectedEventForRegister(event);
                            setRegisterNotes(event.user_notes || '');
                          }}
                          className={`font-bold text-xs px-4 py-2 rounded-xl transition-all shadow-sm flex items-center gap-1.5 cursor-pointer ${
                            event.is_full
                              ? 'bg-amber-500 hover:bg-amber-600 text-white'
                              : 'bg-teal-600 hover:bg-teal-700 text-white'
                          }`}
                        >
                          <span>{event.is_full ? '⏳' : '🎟️'}</span>
                          <span>{event.is_full ? 'Unirme a lista de espera' : 'Inscribirme al evento'}</span>
                        </button>
                      )
                    )}

                    {!token && (
                      <span className="text-xs text-slate-400 italic">
                        Inicia sesión para reservar tu plaza
                      </span>
                    )}
                  </div>

                  {/* Acciones de Autor / Moderador */}
                  {isAuthorOwner && (
                    <button
                      onClick={() => handleOpenAttendees(event)}
                      className="text-xs font-bold text-slate-700 dark:text-slate-300 hover:text-teal-600 dark:hover:text-teal-400 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 px-3 py-1.5 rounded-xl transition-colors cursor-pointer flex items-center gap-1"
                    >
                      <HiOutlineUsers className="w-3.5 h-3.5" />
                      <span>Ver Asistentes ({event.registered_count})</span>
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal 1: Inscribirse al Evento con Pregunta opcional */}
      <Modal
        show={Boolean(selectedEventForRegister)}
        onClose={() => setSelectedEventForRegister(null)}
        size="md"
      >
        <div className="p-6 space-y-4 bg-white dark:bg-slate-900 rounded-3xl">
          <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
            <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <span>🎟️</span>
              <span>Confirmar Inscripción</span>
            </h3>
            <button
              onClick={() => setSelectedEventForRegister(null)}
              className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1"
            >
              <HiOutlineX className="w-5 h-5" />
            </button>
          </div>

          {selectedEventForRegister && (
            <div className="space-y-3">
              <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-2xl border border-slate-200/60 dark:border-slate-800 text-xs space-y-1">
                <div className="font-bold text-slate-900 dark:text-white">
                  {selectedEventForRegister.title}
                </div>
                <div className="text-slate-500">
                  {formatEventDate(selectedEventForRegister.start_time)}
                </div>
                {selectedEventForRegister.is_full && (
                  <div className="text-amber-600 dark:text-amber-400 font-semibold pt-1">
                    ⚠️ Aforo completado: pasarás a la lista de espera automática.
                  </div>
                )}
              </div>

              <form onSubmit={handleRegister} className="space-y-3">
                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                    ¿Quieres enviar una pregunta al autor o nota previa? (Opcional)
                  </label>
                  <textarea
                    rows={3}
                    value={registerNotes}
                    onChange={(e) => setRegisterNotes(e.target.value)}
                    placeholder="Escribe tu pregunta para el coloquio o una dedicatoria solicitada..."
                    className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 p-3 text-slate-900 dark:text-white focus:ring-teal-500"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <Button
                    color="gray"
                    size="sm"
                    onClick={() => setSelectedEventForRegister(null)}
                  >
                    Cancelar
                  </Button>
                  <Button
                    color="teal"
                    size="sm"
                    type="submit"
                    disabled={submittingRegister}
                  >
                    {submittingRegister ? 'Confirmando...' : 'Confirmar Reserva'}
                  </Button>
                </div>
              </form>
            </div>
          )}
        </div>
      </Modal>

      {/* Modal 2: Crear Evento de Autor */}
      <Modal
        show={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        size="lg"
      >
        <div className="p-6 space-y-4 bg-white dark:bg-slate-900 rounded-3xl max-h-[90vh] overflow-y-auto">
          <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
            <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <span>✍️</span>
              <span>Programar Nuevo Evento Literario</span>
            </h3>
            <button
              onClick={() => setIsCreateModalOpen(false)}
              className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1"
            >
              <HiOutlineX className="w-5 h-5" />
            </button>
          </div>

          {createError && (
            <div className="p-3 bg-rose-50 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300 rounded-xl text-xs whitespace-pre-line font-semibold">
              {createError}
            </div>
          )}

          <form onSubmit={handleCreateEvent} className="space-y-4 text-xs">
            <div>
              <label className="block font-bold text-slate-700 dark:text-slate-300 mb-1">
                Título del Evento *
              </label>
              <input
                type="text"
                required
                value={createForm.title}
                onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
                placeholder="Ej. Presentación y firma de ejemplares de mi nueva novela"
                className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 py-2 px-3 text-slate-900 dark:text-white focus:ring-teal-500"
              />
            </div>

            <div>
              <label className="block font-bold text-slate-700 dark:text-slate-300 mb-1">
                Descripción y Programa *
              </label>
              <textarea
                rows={3}
                required
                value={createForm.description}
                onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                placeholder="Explica a tus lectores en qué consistirá el encuentro, temas a tratar..."
                className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 p-3 text-slate-900 dark:text-white focus:ring-teal-500"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block font-bold text-slate-700 dark:text-slate-300 mb-1">
                  Tipo de Evento
                </label>
                <select
                  value={createForm.event_type}
                  onChange={(e) => setCreateForm({ ...createForm, event_type: e.target.value })}
                  className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 py-2 px-3 text-slate-900 dark:text-white focus:ring-teal-500"
                >
                  <option value="BOOK_LAUNCH">Lanzamiento / Presentación</option>
                  <option value="SIGNING">Firma de ejemplares</option>
                  <option value="QA_SESSION">Sesión de preguntas (Q&A)</option>
                  <option value="READING">Lectura pública</option>
                  <option value="WORKSHOP">Taller literario</option>
                  <option value="OTHER">Otro evento</option>
                </select>
              </div>

              <div>
                <label className="block font-bold text-slate-700 dark:text-slate-300 mb-1">
                  Formato
                </label>
                <select
                  value={createForm.event_format}
                  onChange={(e) => setCreateForm({ ...createForm, event_format: e.target.value })}
                  className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 py-2 px-3 text-slate-900 dark:text-white focus:ring-teal-500"
                >
                  <option value="ONLINE">Virtual / Streaming</option>
                  <option value="IN_PERSON">Presencial</option>
                  <option value="HYBRID">Híbrido</option>
                </select>
              </div>
            </div>

            {/* Selector de libro vinculado */}
            {books.length > 0 && (
              <div>
                <label className="block font-bold text-slate-700 dark:text-slate-300 mb-1">
                  Libro Vinculado (Opcional)
                </label>
                <select
                  value={createForm.book}
                  onChange={(e) => setCreateForm({ ...createForm, book: e.target.value })}
                  className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 py-2 px-3 text-slate-900 dark:text-white focus:ring-teal-500"
                >
                  <option value="">Ninguno / Encuentro general</option>
                  {books.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.title}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Fecha y hora */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block font-bold text-slate-700 dark:text-slate-300 mb-1">
                  Fecha y Hora de Inicio *
                </label>
                <input
                  type="datetime-local"
                  required
                  value={createForm.start_time}
                  onChange={(e) => setCreateForm({ ...createForm, start_time: e.target.value })}
                  className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 py-2 px-3 text-slate-900 dark:text-white focus:ring-teal-500"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 dark:text-slate-300 mb-1">
                  Fecha y Hora de Fin (Opcional)
                </label>
                <input
                  type="datetime-local"
                  value={createForm.end_time}
                  onChange={(e) => setCreateForm({ ...createForm, end_time: e.target.value })}
                  className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 py-2 px-3 text-slate-900 dark:text-white focus:ring-teal-500"
                />
              </div>
            </div>

            {/* Ubicación y aforo */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block font-bold text-slate-700 dark:text-slate-300 mb-1">
                  Lugar o Plataforma
                </label>
                <input
                  type="text"
                  value={createForm.location_name}
                  onChange={(e) => setCreateForm({ ...createForm, location_name: e.target.value })}
                  placeholder="Ej. Librería Rafael Alberti / Zoom"
                  className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 py-2 px-3 text-slate-900 dark:text-white focus:ring-teal-500"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 dark:text-slate-300 mb-1">
                  Aforo Máximo (Plazas)
                </label>
                <input
                  type="number"
                  min="1"
                  value={createForm.max_attendees}
                  onChange={(e) => setCreateForm({ ...createForm, max_attendees: e.target.value })}
                  placeholder="Dejar vacío si no hay límite"
                  className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 py-2 px-3 text-slate-900 dark:text-white focus:ring-teal-500"
                />
              </div>
            </div>

            {createForm.event_format !== 'ONLINE' && (
              <div>
                <label className="block font-bold text-slate-700 dark:text-slate-300 mb-1">
                  Dirección Física
                </label>
                <input
                  type="text"
                  value={createForm.location_address}
                  onChange={(e) => setCreateForm({ ...createForm, location_address: e.target.value })}
                  placeholder="Ej. Calle Tutor 57, 28008 Madrid"
                  className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 py-2 px-3 text-slate-900 dark:text-white focus:ring-teal-500"
                />
              </div>
            )}

            {createForm.event_format !== 'IN_PERSON' && (
              <div>
                <label className="block font-bold text-slate-700 dark:text-slate-300 mb-1">
                  Enlace Virtual / Streaming
                </label>
                <input
                  type="url"
                  value={createForm.online_url}
                  onChange={(e) => setCreateForm({ ...createForm, online_url: e.target.value })}
                  placeholder="https://meet.google.com/... o enlace de YouTube"
                  className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 py-2 px-3 text-slate-900 dark:text-white focus:ring-teal-500"
                />
              </div>
            )}

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
              <Button
                color="gray"
                size="sm"
                onClick={() => setIsCreateModalOpen(false)}
              >
                Cancelar
              </Button>
              <Button
                color="teal"
                size="sm"
                type="submit"
                disabled={submittingCreate}
              >
                {submittingCreate ? 'Publicando...' : 'Publicar Evento'}
              </Button>
            </div>
          </form>
        </div>
      </Modal>

      {/* Modal 3: Lista de Asistentes y Preguntas (Solo para el Autor) */}
      <Modal
        show={Boolean(viewingAttendeesEvent)}
        onClose={() => setViewingAttendeesEvent(null)}
        size="lg"
      >
        <div className="p-6 space-y-4 bg-white dark:bg-slate-900 rounded-3xl max-h-[85vh] overflow-y-auto">
          <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <span>👥</span>
                <span>Asistentes e Inscripciones</span>
              </h3>
              {viewingAttendeesEvent && (
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {viewingAttendeesEvent.title}
                </p>
              )}
            </div>
            <button
              onClick={() => setViewingAttendeesEvent(null)}
              className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1"
            >
              <HiOutlineX className="w-5 h-5" />
            </button>
          </div>

          {loadingAttendees ? (
            <div className="py-8 flex justify-center">
              <Spinner size="md" color="teal" />
            </div>
          ) : attendeesList.length === 0 ? (
            <div className="text-center py-6 text-slate-500 text-xs">
              Aún no hay lectores inscritos en este evento.
            </div>
          ) : (
            <div className="space-y-3">
              {attendeesList.map((att) => (
                <div
                  key={att.id}
                  className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-2xl border border-slate-200/60 dark:border-slate-800 flex flex-col space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {att.user_avatar ? (
                        <img
                          src={att.user_avatar}
                          alt={att.username}
                          className="w-7 h-7 rounded-full object-cover"
                        />
                      ) : (
                        <div className="w-7 h-7 rounded-full bg-teal-600 text-white flex items-center justify-center text-xs font-bold">
                          {att.username[0]?.toUpperCase()}
                        </div>
                      )}
                      <span className="text-xs font-bold text-slate-800 dark:text-slate-200">
                        @{att.username}
                      </span>
                    </div>

                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        att.status === 'REGISTERED'
                          ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                          : att.status === 'WAITLIST'
                          ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                          : 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-300'
                      }`}
                    >
                      {att.status_display}
                    </span>
                  </div>

                  {att.notes && (
                    <div className="bg-white dark:bg-slate-900 p-2.5 rounded-xl border border-slate-100 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-300 flex items-start gap-2">
                      <HiOutlineChatAlt2 className="w-4 h-4 text-teal-600 shrink-0 mt-0.5" />
                      <div className="italic">"{att.notes}"</div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
};
