import React, { useEffect, useState } from 'react';
import { Spinner, Modal, Button } from 'flowbite-react';
import {
  HiOutlineMail,
  HiOutlineUsers,
  HiOutlinePlus,
  HiOutlineCheck,
  HiOutlinePaperAirplane,
  HiOutlinePencil,
  HiOutlineClock,
  HiOutlineChevronDown,
  HiOutlineChevronUp,
  HiOutlineBookOpen,
} from 'react-icons/hi';
import { useAuthStore } from '../../../store/auth';

export interface AuthorNewsletterIssueItem {
  id: number;
  newsletter: number;
  newsletter_title: string;
  author_name: string;
  title: string;
  subject: string;
  content: string;
  status: 'DRAFT' | 'SCHEDULED' | 'SENT';
  status_display: string;
  sent_at?: string | null;
  recipients_count: number;
  views_count: number;
  created_at: string;
}

export interface AuthorNewsletterItem {
  id: number;
  author: number;
  author_name: string;
  author_photo?: string | null;
  author_profile?: number | null;
  title: string;
  description: string;
  frequency: 'WEEKLY' | 'BIWEEKLY' | 'MONTHLY' | 'OCCASIONAL';
  frequency_display: string;
  is_active: boolean;
  active_subscribers_count: number;
  sent_issues_count: number;
  is_subscribed: boolean;
  latest_issues: AuthorNewsletterIssueItem[];
  created_at: string;
  updated_at: string;
}

interface AuthorNewsletterSectionProps {
  authorId: number;
  authorName: string;
  isAuthorOwner: boolean;
}

export const AuthorNewsletterSection: React.FC<AuthorNewsletterSectionProps> = ({
  authorId,
  authorName,
  isAuthorOwner,
}) => {
  const { token } = useAuthStore();
  const [newsletter, setNewsletter] = useState<AuthorNewsletterItem | null>(null);
  const [issues, setIssues] = useState<AuthorNewsletterIssueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [subscribing, setSubscribing] = useState(false);
  const [expandedIssue, setExpandedIssue] = useState<Record<number, boolean>>({});

  // Modales
  const [isNewsletterModalOpen, setIsNewsletterModalOpen] = useState(false);
  const [newsletterForm, setNewsletterForm] = useState({
    title: '',
    description: '',
    frequency: 'MONTHLY',
  });
  const [savingNewsletter, setSavingNewsletter] = useState(false);
  const [newsletterError, setNewsletterError] = useState<string | null>(null);

  const [isIssueModalOpen, setIsIssueModalOpen] = useState(false);
  const [issueForm, setIssueForm] = useState({
    title: '',
    subject: '',
    content: '',
    sendImmediately: false,
  });
  const [savingIssue, setSavingIssue] = useState(false);
  const [issueError, setIssueError] = useState<string | null>(null);

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  const loadData = async () => {
    try {
      setLoading(true);
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      // 1. Obtener la newsletter del autor
      const res = await fetch(`${apiUrl}/api/v1/books/author-newsletters/?author=${authorId}`, {
        headers,
      });

      if (res.ok) {
        const data = await res.json();
        const results = data.results || data;
        const currentNewsletter = results.length > 0 ? results[0] : null;
        setNewsletter(currentNewsletter);

        if (currentNewsletter) {
          // 2. Obtener entregas
          const issuesRes = await fetch(
            `${apiUrl}/api/v1/books/author-newsletter-issues/?newsletter=${currentNewsletter.id}`,
            { headers }
          );
          if (issuesRes.ok) {
            const issuesData = await issuesRes.json();
            setIssues(issuesData.results || issuesData);
          }
        } else {
          setIssues([]);
        }
      }
    } catch (err) {
      console.error('Error loading newsletter data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [authorId, token]);

  const handleToggleSubscribe = async () => {
    if (!newsletter || !token) return;
    setSubscribing(true);
    try {
      const action = newsletter.is_subscribed ? 'unsubscribe' : 'subscribe';
      const res = await fetch(
        `${apiUrl}/api/v1/books/author-newsletters/${newsletter.id}/${action}/`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (res.ok) {
        const data = await res.json();
        setNewsletter((prev) =>
          prev
            ? {
                ...prev,
                is_subscribed: data.is_subscribed,
                active_subscribers_count: data.active_subscribers_count,
              }
            : null
        );
      }
    } catch (err) {
      console.error('Error toggling subscription:', err);
    } finally {
      setSubscribing(false);
    }
  };

  const handleSaveNewsletter = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setSavingNewsletter(true);
    setNewsletterError(null);

    try {
      const isEditing = !!newsletter;
      const url = isEditing
        ? `${apiUrl}/api/v1/books/author-newsletters/${newsletter.id}/`
        : `${apiUrl}/api/v1/books/author-newsletters/`;
      const method = isEditing ? 'PATCH' : 'POST';

      const payload = {
        ...newsletterForm,
        author: authorId,
      };

      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || errData.title || 'Error al guardar la newsletter');
      }

      setIsNewsletterModalOpen(false);
      await loadData();
    } catch (err: any) {
      setNewsletterError(err.message || 'Error inesperado');
    } finally {
      setSavingNewsletter(false);
    }
  };

  const handleSaveIssue = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newsletter || !token) return;
    setSavingIssue(true);
    setIssueError(null);

    try {
      const payload = {
        newsletter: newsletter.id,
        title: issueForm.title,
        subject: issueForm.subject,
        content: issueForm.content,
        status: 'DRAFT',
      };

      const res = await fetch(`${apiUrl}/api/v1/books/author-newsletter-issues/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Error al crear la entrega');
      }

      const createdIssue = await res.json();

      // Si el autor seleccionó enviar inmediatamente
      if (issueForm.sendImmediately && createdIssue.id) {
        const sendRes = await fetch(
          `${apiUrl}/api/v1/books/author-newsletter-issues/${createdIssue.id}/send_issue/`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${token}`,
            },
          }
        );
        if (!sendRes.ok) {
          console.warn('Entrega creada en borrador pero falló el envío inmediato');
        }
      }

      setIsIssueModalOpen(false);
      setIssueForm({ title: '', subject: '', content: '', sendImmediately: false });
      await loadData();
    } catch (err: any) {
      setIssueError(err.message || 'Error inesperado');
    } finally {
      setSavingIssue(false);
    }
  };

  const handleSendExistingIssue = async (issueId: number) => {
    if (!token) return;
    try {
      const res = await fetch(
        `${apiUrl}/api/v1/books/author-newsletter-issues/${issueId}/send_issue/`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
        }
      );
      if (res.ok) {
        await loadData();
      }
    } catch (err) {
      console.error('Error sending issue:', err);
    }
  };

  const toggleExpand = (id: number) => {
    setExpandedIssue((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const formatDate = (isoString: string) => {
    try {
      return new Date(isoString).toLocaleDateString('es-ES', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <section className="mt-12 bg-white dark:bg-gray-800 rounded-2xl p-6 sm:p-8 shadow-sm border border-gray-100 dark:border-gray-700 transition-all">
      {/* Cabecera de la sección */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-gray-100 dark:border-gray-700">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 bg-rose-50 dark:bg-rose-900/30 text-rose-600 dark:text-rose-400 rounded-lg">
              <HiOutlineMail className="w-6 h-6" />
            </span>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              Boletín Literario & Novedades
            </h2>
          </div>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Recibe cartas exclusivas, reflexiones y adelantos de {authorName} en tu buzón.
          </p>
        </div>

        {/* Acciones de gestión para el autor propietario */}
        {isAuthorOwner && (
          <div className="flex flex-wrap items-center gap-2">
            {newsletter ? (
              <>
                <button
                  type="button"
                  onClick={() => {
                    setNewsletterForm({
                      title: newsletter.title,
                      description: newsletter.description,
                      frequency: newsletter.frequency,
                    });
                    setIsNewsletterModalOpen(true);
                  }}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors"
                >
                  <HiOutlinePencil className="w-4 h-4" />
                  Editar boletín
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIssueForm({ title: '', subject: '', content: '', sendImmediately: false });
                    setIsIssueModalOpen(true);
                  }}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-700 rounded-lg shadow-sm transition-all"
                >
                  <HiOutlinePlus className="w-4 h-4" />
                  Nueva entrega
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={() => {
                  setNewsletterForm({
                    title: `Boletín oficial de ${authorName}`,
                    description: 'Reflexiones literarias, procesos de escritura y primicias exclusivas.',
                    frequency: 'MONTHLY',
                  });
                  setIsNewsletterModalOpen(true);
                }}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-rose-600 hover:bg-rose-700 rounded-xl shadow-sm transition-all"
              >
                <HiOutlinePlus className="w-5 h-5" />
                Configurar mi Newsletter
              </button>
            )}
          </div>
        )}
      </div>

      {loading ? (
        <div className="py-12 flex justify-center items-center">
          <Spinner size="lg" color="pink" />
        </div>
      ) : !newsletter ? (
        /* Caso: No hay newsletter configurada */
        <div className="py-12 text-center">
          <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center text-gray-400">
            <HiOutlineMail className="w-8 h-8" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            Sin boletín activo actualmente
          </h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400 max-w-md mx-auto">
            {authorName} aún no ha habilitado un boletín periódico. Vuelve más adelante para suscribirte a sus noticias.
          </p>
        </div>
      ) : (
        /* Caso: Newsletter existente */
        <div className="mt-6 space-y-8">
          {/* Tarjeta destacada de suscripción */}
          <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-rose-50 via-white to-orange-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 p-6 sm:p-8 border border-rose-100 dark:border-gray-700">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
              <div className="max-w-xl">
                <div className="flex items-center gap-2 mb-2">
                  <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300">
                    {newsletter.frequency_display || 'Frecuencia regular'}
                  </span>
                  <span className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                    <HiOutlineUsers className="w-4 h-4 text-gray-400" />
                    {newsletter.active_subscribers_count}{' '}
                    {newsletter.active_subscribers_count === 1 ? 'suscriptor' : 'suscriptores'}
                  </span>
                </div>
                <h3 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
                  {newsletter.title}
                </h3>
                <p className="mt-2 text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
                  {newsletter.description || 'Suscríbete para recibir los comunicados directos del autor.'}
                </p>
              </div>

              {/* Botón de suscripción */}
              <div className="w-full md:w-auto flex-shrink-0">
                {token ? (
                  <button
                    type="button"
                    onClick={handleToggleSubscribe}
                    disabled={subscribing}
                    className={`w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-semibold text-sm transition-all shadow-sm ${
                      newsletter.is_subscribed
                        ? 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800'
                        : 'bg-rose-600 text-white hover:bg-rose-700 hover:shadow-md'
                    }`}
                  >
                    {subscribing ? (
                      <Spinner size="sm" />
                    ) : newsletter.is_subscribed ? (
                      <>
                        <HiOutlineCheck className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                        <span>Suscrito (Cancelar)</span>
                      </>
                    ) : (
                      <>
                        <HiOutlineMail className="w-5 h-5" />
                        <span>Suscribirme con 1 clic</span>
                      </>
                    )}
                  </button>
                ) : (
                  <div className="text-xs text-gray-500 dark:text-gray-400 text-center md:text-right">
                    Inicia sesión para suscribirte al boletín
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Listado de entregas publicadas */}
          <div>
            <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <HiOutlineBookOpen className="w-5 h-5 text-gray-500" />
              <span>Entregas y números del boletín</span>
              <span className="text-xs font-normal text-gray-400">({issues.length})</span>
            </h4>

            {issues.length === 0 ? (
              <div className="py-8 text-center text-sm text-gray-500 dark:text-gray-400 border border-dashed border-gray-200 dark:border-gray-700 rounded-xl">
                Aún no hay entregas publicadas en esta newsletter.
              </div>
            ) : (
              <div className="space-y-4">
                {issues.map((issue) => {
                  const isExpanded = !!expandedIssue[issue.id];
                  const isDraft = issue.status === 'DRAFT';

                  return (
                    <article
                      key={issue.id}
                      className="rounded-xl border border-gray-100 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/40 p-5 transition-all hover:bg-gray-50 dark:hover:bg-gray-800"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2">
                            {isDraft && (
                              <span className="px-2 py-0.5 text-xs font-semibold rounded bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400">
                                Borrador
                              </span>
                            )}
                            <span className="flex items-center gap-1 text-xs text-gray-400">
                              <HiOutlineClock className="w-3.5 h-3.5" />
                              {formatDate(issue.sent_at || issue.created_at)}
                            </span>
                            {!isDraft && issue.recipients_count > 0 && (
                              <span className="text-xs text-gray-400">
                                · {issue.recipients_count} lectores
                              </span>
                            )}
                          </div>
                          <h5 className="text-base font-bold text-gray-900 dark:text-white mt-1">
                            {issue.title}
                          </h5>
                          <p className="text-xs font-medium text-rose-600 dark:text-rose-400">
                            Asunto: {issue.subject}
                          </p>
                        </div>

                        {/* Botón de envío si es borrador (solo autor) */}
                        <div className="flex items-center gap-2">
                          {isDraft && isAuthorOwner && (
                            <button
                              type="button"
                              onClick={() => handleSendExistingIssue(issue.id)}
                              className="inline-flex items-center gap-1 px-3 py-1 text-xs font-semibold rounded-lg bg-rose-600 text-white hover:bg-rose-700 transition-colors"
                            >
                              <HiOutlinePaperAirplane className="w-3.5 h-3.5" />
                              Enviar ahora
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => toggleExpand(issue.id)}
                            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors"
                          >
                            <span>{isExpanded ? 'Ocultar' : 'Leer entrega'}</span>
                            {isExpanded ? (
                              <HiOutlineChevronUp className="w-4 h-4" />
                            ) : (
                              <HiOutlineChevronDown className="w-4 h-4" />
                            )}
                          </button>
                        </div>
                      </div>

                      {/* Contenido desplegable */}
                      {isExpanded && (
                        <div className="mt-4 pt-4 border-t border-gray-200/60 dark:border-gray-700 text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-line bg-white dark:bg-gray-900/60 p-4 rounded-lg">
                          {issue.content}
                        </div>
                      )}
                    </article>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modal: Configuración de Newsletter */}
      <Modal show={isNewsletterModalOpen} onClose={() => setIsNewsletterModalOpen(false)}>
        <Modal.Header>
          {newsletter ? 'Editar Boletín Literario' : 'Configurar mi Newsletter Oficial'}
        </Modal.Header>
        <form onSubmit={handleSaveNewsletter}>
          <Modal.Body className="space-y-4">
            {newsletterError && (
              <div className="p-3 bg-red-50 text-red-700 text-sm rounded-lg dark:bg-red-900/20 dark:text-red-400">
                {newsletterError}
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-900 dark:text-white mb-1">
                Título del Boletín
              </label>
              <input
                type="text"
                required
                value={newsletterForm.title}
                onChange={(e) => setNewsletterForm({ ...newsletterForm, title: e.target.value })}
                placeholder="Ej. Cartas desde mi escritorio"
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-900 dark:text-white mb-1">
                Frecuencia estimada
              </label>
              <select
                value={newsletterForm.frequency}
                onChange={(e) => setNewsletterForm({ ...newsletterForm, frequency: e.target.value })}
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                <option value="WEEKLY">Semanal</option>
                <option value="BIWEEKLY">Quincenal</option>
                <option value="MONTHLY">Mensual</option>
                <option value="OCCASIONAL">Ocasional</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-900 dark:text-white mb-1">
                Descripción / Manifiesto para los lectores
              </label>
              <textarea
                rows={3}
                value={newsletterForm.description}
                onChange={(e) => setNewsletterForm({ ...newsletterForm, description: e.target.value })}
                placeholder="Explica a tus lectores qué contenidos y primicias compartirás con ellos..."
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>
          </Modal.Body>
          <Modal.Footer>
            <Button color="gray" onClick={() => setIsNewsletterModalOpen(false)}>
              Cancelar
            </Button>
            <Button color="pink" type="submit" disabled={savingNewsletter}>
              {savingNewsletter ? <Spinner size="sm" /> : 'Guardar boletín'}
            </Button>
          </Modal.Footer>
        </form>
      </Modal>

      {/* Modal: Nueva Entrega / Número de Newsletter */}
      <Modal show={isIssueModalOpen} onClose={() => setIsIssueModalOpen(false)} size="xl">
        <Modal.Header>Redactar Nueva Entrega</Modal.Header>
        <form onSubmit={handleSaveIssue}>
          <Modal.Body className="space-y-4">
            {issueError && (
              <div className="p-3 bg-red-50 text-red-700 text-sm rounded-lg dark:bg-red-900/20 dark:text-red-400">
                {issueError}
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-900 dark:text-white mb-1">
                Título de la entrega
              </label>
              <input
                type="text"
                required
                value={issueForm.title}
                onChange={(e) => setIssueForm({ ...issueForm, title: e.target.value })}
                placeholder="Ej. Entrega #4: Primeras notas sobre la próxima trilogía"
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-900 dark:text-white mb-1">
                Asunto del boletín
              </label>
              <input
                type="text"
                required
                value={issueForm.subject}
                onChange={(e) => setIssueForm({ ...issueForm, subject: e.target.value })}
                placeholder="Ej. Novedades exclusivas para mi comunidad lectora"
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-900 dark:text-white mb-1">
                Contenido del boletín
              </label>
              <textarea
                rows={8}
                required
                value={issueForm.content}
                onChange={(e) => setIssueForm({ ...issueForm, content: e.target.value })}
                placeholder="Escribe tu mensaje para los suscriptores..."
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>

            <div className="flex items-center gap-2 pt-2">
              <input
                type="checkbox"
                id="sendImmediately"
                checked={issueForm.sendImmediately}
                onChange={(e) =>
                  setIssueForm({ ...issueForm, sendImmediately: e.target.checked })
                }
                className="w-4 h-4 text-rose-600 rounded border-gray-300 focus:ring-rose-500"
              />
              <label htmlFor="sendImmediately" className="text-sm text-gray-700 dark:text-gray-300">
                Enviar inmediatamente a los suscriptores activos (si no, quedará como borrador)
              </label>
            </div>
          </Modal.Body>
          <Modal.Footer>
            <Button color="gray" onClick={() => setIsIssueModalOpen(false)}>
              Cancelar
            </Button>
            <Button color="pink" type="submit" disabled={savingIssue}>
              {savingIssue ? (
                <Spinner size="sm" />
              ) : issueForm.sendImmediately ? (
                'Publicar y Enviar'
              ) : (
                'Guardar borrador'
              )}
            </Button>
          </Modal.Footer>
        </form>
      </Modal>
    </section>
  );
};
