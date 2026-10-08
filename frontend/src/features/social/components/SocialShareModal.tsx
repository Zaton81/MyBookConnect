import React, { useEffect, useState } from 'react';
import { Modal, Button, Spinner } from 'flowbite-react';
import {
  HiOutlineClipboardCopy,
  HiOutlineCheck,
  HiOutlineShare,
  HiOutlinePhotograph,
} from 'react-icons/hi';
import {
  SiX,
  SiWhatsapp,
  SiTelegram,
  SiLinkedin,
  SiFacebook,
} from 'react-icons/si';
import { useAuthStore } from '../../../store/auth';

export interface SocialShareCardData {
  title: string;
  subtitle: string;
  stat_highlight: string;
  stat_label: string;
  badge_or_icon: string;
  image_url: string | null;
  theme_color: string;
  site_name: string;
}

export interface SocialShareResponse {
  share_type: string;
  title: string;
  description: string;
  canonical_url: string;
  hashtags: string[];
  share_text: string;
  share_urls: {
    twitter: string;
    whatsapp: string;
    telegram: string;
    linkedin: string;
    facebook: string;
    email: string;
  };
  card_data: SocialShareCardData;
}

export interface SocialShareModalProps {
  isOpen: boolean;
  onClose: () => void;
  shareType: 'book' | 'reading_stats' | 'challenge' | 'badge' | 'reading_list';
  objectId?: number | string;
  year?: number | string;
  initialTitle?: string;
  initialData?: SocialShareResponse | null;
}

export const SocialShareModal: React.FC<SocialShareModalProps> = ({
  isOpen,
  onClose,
  shareType,
  objectId,
  year,
  initialTitle,
  initialData,
}) => {
  const { token, user } = useAuthStore();
  const [data, setData] = useState<SocialShareResponse | null>(initialData || null);
  const [loading, setLoading] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);
  const [copiedText, setCopiedText] = useState(false);

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    if (!isOpen) return;

    if (initialData) {
      setData(initialData);
      setLoading(false);
      return;
    }

    const fetchShareData = async () => {
      setLoading(true);
      setCopiedLink(false);
      setCopiedText(false);

      try {
        const params = new URLSearchParams();
        params.set('type', shareType);
        if (objectId) params.set('id', String(objectId));
        if (year && year !== 'all') params.set('year', String(year));
        if (user?.id) params.set('user_id', String(user.id));

        const res = await fetch(`${apiUrl}/api/v1/books/share/card/?${params.toString()}`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });

        if (res.ok) {
          const json: SocialShareResponse = await res.json();
          setData(json);
        } else {
          // Fallback local en caso de error
          generateFallback(shareType, initialTitle, objectId);
        }
      } catch (err) {
        console.warn('Error fetching share metadata, using fallback:', err);
        generateFallback(shareType, initialTitle, objectId);
      } finally {
        setLoading(false);
      }
    };

    fetchShareData();
  }, [isOpen, shareType, objectId, year, apiUrl, token, user?.id]);

  const generateFallback = (type: string, title?: string, id?: number | string) => {
    const currentOrigin = window.location.origin;
    let url = currentOrigin;
    if (type === 'book' && id) url = `${currentOrigin}/books/${id}`;
    else if (type === 'reading_stats') url = `${currentOrigin}/statistics`;
    else if (type === 'challenge') url = `${currentOrigin}/challenges`;

    const text = `📖 ¡Echa un vistazo a ${title || 'esto'} en @MyBookConnect! 🚀`;
    const encodedText = encodeURIComponent(text);
    const encodedUrl = encodeURIComponent(url);

    setData({
      share_type: type,
      title: title || 'MyBookConnect',
      description: text,
      canonical_url: url,
      hashtags: ['#MyBookConnect', '#Lectura'],
      share_text: text,
      share_urls: {
        twitter: `https://twitter.com/intent/tweet?text=${encodedText}&url=${encodedUrl}`,
        whatsapp: `https://api.whatsapp.com/send?text=${encodedText}%20${encodedUrl}`,
        telegram: `https://t.me/share/url?url=${encodedUrl}&text=${encodedText}`,
        linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodedUrl}`,
        facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`,
        email: `mailto:?subject=${encodeURIComponent(title || 'MyBookConnect')}&body=${encodedText}%0A%0A${encodedUrl}`,
      },
      card_data: {
        title: title || 'MyBookConnect',
        subtitle: 'Comunidad Literaria',
        stat_highlight: 'Social',
        stat_label: 'Compartido',
        badge_or_icon: '📚',
        image_url: null,
        theme_color: 'teal',
        site_name: 'MyBookConnect',
      },
    });
  };

  const handleTrackShare = (platform: string) => {
    try {
      fetch(`${apiUrl}/api/v1/books/share/track/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          type: shareType,
          id: objectId,
          platform,
        }),
      }).catch(() => {});
    } catch {}
  };

  const handleOpenPlatform = (platform: string, url: string) => {
    handleTrackShare(platform);
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const handleCopyLink = () => {
    if (!data?.canonical_url) return;
    navigator.clipboard.writeText(data.canonical_url);
    handleTrackShare('clipboard_link');
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 3000);
  };

  const handleCopyText = () => {
    if (!data) return;
    const fullMessage = `${data.share_text}\n\n${data.canonical_url}\n${data.hashtags.join(' ')}`;
    navigator.clipboard.writeText(fullMessage);
    handleTrackShare('clipboard_text');
    setCopiedText(true);
    setTimeout(() => setCopiedText(false), 3000);
  };

  return (
    <Modal
      show={isOpen}
      onClose={onClose}
      size="lg"
      dismissible
      role="dialog"
      aria-labelledby="social-share-title"
    >
      <Modal.Header>
        <div className="flex items-center gap-2">
          <HiOutlineShare className="w-5 h-5 text-teal-600 dark:text-teal-400" />
          <span id="social-share-title" className="text-lg font-bold text-slate-900 dark:text-white">
            Compartir en Redes Sociales
          </span>
        </div>
      </Modal.Header>

      <Modal.Body>
        {loading ? (
          <div className="flex flex-col items-center justify-center py-12 gap-3">
            <Spinner size="lg" color="teal" />
            <p className="text-xs font-semibold text-slate-500">
              Generando tarjeta gráfica y enlaces sociales...
            </p>
          </div>
        ) : data ? (
          <div className="space-y-6">
            {/* ── Tarjeta Gráfica Previsualizable (Social Card) ── */}
            <div className="relative overflow-hidden rounded-3xl p-6 sm:p-7 text-white shadow-xl bg-gradient-to-br from-slate-900 via-teal-950 to-slate-900 border border-teal-500/30">
              {/* Decoración de fondo */}
              <div className="absolute -top-12 -right-12 w-40 h-40 bg-teal-500/10 rounded-full blur-2xl pointer-events-none" />
              <div className="absolute -bottom-12 -left-12 w-40 h-40 bg-blue-500/10 rounded-full blur-2xl pointer-events-none" />

              {/* Encabezado de la tarjeta */}
              <div className="flex justify-between items-center mb-5 border-b border-white/10 pb-3">
                <div className="flex items-center gap-2">
                  <span className="text-lg">📖</span>
                  <span className="font-black text-sm tracking-wide text-teal-300">
                    {data.card_data.site_name}
                  </span>
                </div>
                <span className="text-[10px] uppercase font-bold tracking-widest text-slate-400 px-2.5 py-0.5 rounded-full bg-white/5 border border-white/10">
                  Tarjeta Social
                </span>
              </div>

              {/* Contenido principal */}
              <div className="flex items-center gap-4 sm:gap-5">
                {/* Portada o Icono */}
                <div className="w-20 h-28 rounded-xl bg-white/10 border border-white/15 overflow-hidden shrink-0 flex items-center justify-center text-3xl shadow-md">
                  {data.card_data.image_url ? (
                    <img
                      src={data.card_data.image_url}
                      alt={data.card_data.title}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <span>{data.card_data.badge_or_icon || '📚'}</span>
                  )}
                </div>

                {/* Textos */}
                <div className="min-w-0 flex-1">
                  <h3 className="text-xl sm:text-2xl font-black text-white leading-tight line-clamp-2">
                    {data.card_data.title}
                  </h3>
                  <p className="text-xs sm:text-sm text-slate-300 mt-1 truncate">
                    {data.card_data.subtitle}
                  </p>

                  {/* Resalte métrico */}
                  <div className="mt-3 flex items-baseline gap-2">
                    <span className="text-lg sm:text-xl font-black text-teal-300">
                      {data.card_data.stat_highlight}
                    </span>
                    <span className="text-[11px] text-slate-300 font-medium">
                      {data.card_data.stat_label}
                    </span>
                  </div>
                </div>
              </div>

              {/* Pie de tarjeta */}
              <div className="mt-5 pt-3 border-t border-white/10 flex justify-between items-center text-[10px] text-slate-400">
                <span className="truncate">{data.hashtags.join(' ')}</span>
                <span className="shrink-0 font-semibold text-teal-400 ml-2">mybookconnect.com</span>
              </div>
            </div>

            {/* ── Botones de 1 Clic en Redes Sociales ── */}
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2 uppercase tracking-wider">
                Compartir con 1 clic
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
                {/* X / Twitter */}
                <button
                  type="button"
                  onClick={() => handleOpenPlatform('twitter', data.share_urls.twitter)}
                  className="flex items-center justify-center gap-2 p-2.5 rounded-xl bg-black hover:bg-slate-800 text-white text-xs font-bold transition-all shadow-xs"
                >
                  <SiX className="w-3.5 h-3.5" />
                  <span>X (Twitter)</span>
                </button>

                {/* WhatsApp */}
                <button
                  type="button"
                  onClick={() => handleOpenPlatform('whatsapp', data.share_urls.whatsapp)}
                  className="flex items-center justify-center gap-2 p-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition-all shadow-xs"
                >
                  <SiWhatsapp className="w-3.5 h-3.5" />
                  <span>WhatsApp</span>
                </button>

                {/* Telegram */}
                <button
                  type="button"
                  onClick={() => handleOpenPlatform('telegram', data.share_urls.telegram)}
                  className="flex items-center justify-center gap-2 p-2.5 rounded-xl bg-sky-500 hover:bg-sky-600 text-white text-xs font-bold transition-all shadow-xs"
                >
                  <SiTelegram className="w-3.5 h-3.5" />
                  <span>Telegram</span>
                </button>

                {/* LinkedIn */}
                <button
                  type="button"
                  onClick={() => handleOpenPlatform('linkedin', data.share_urls.linkedin)}
                  className="flex items-center justify-center gap-2 p-2.5 rounded-xl bg-blue-700 hover:bg-blue-800 text-white text-xs font-bold transition-all shadow-xs"
                >
                  <SiLinkedin className="w-3.5 h-3.5" />
                  <span>LinkedIn</span>
                </button>

                {/* Facebook */}
                <button
                  type="button"
                  onClick={() => handleOpenPlatform('facebook', data.share_urls.facebook)}
                  className="flex items-center justify-center gap-2 p-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-all shadow-xs col-span-2 sm:col-span-1"
                >
                  <SiFacebook className="w-3.5 h-3.5" />
                  <span>Facebook</span>
                </button>
              </div>
            </div>

            {/* ── Copiar Enlace y Texto ── */}
            <div className="pt-2 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row gap-2.5">
              <Button
                color={copiedLink ? 'success' : 'light'}
                onClick={handleCopyLink}
                className="flex-1 font-bold text-xs"
              >
                {copiedLink ? (
                  <>
                    <HiOutlineCheck className="w-4 h-4 mr-1.5 text-emerald-600" />
                    ¡Enlace copiado!
                  </>
                ) : (
                  <>
                    <HiOutlineClipboardCopy className="w-4 h-4 mr-1.5" />
                    Copiar Enlace
                  </>
                )}
              </Button>

              <Button
                color={copiedText ? 'success' : 'light'}
                onClick={handleCopyText}
                className="flex-1 font-bold text-xs"
              >
                {copiedText ? (
                  <>
                    <HiOutlineCheck className="w-4 h-4 mr-1.5 text-emerald-600" />
                    ¡Texto copiado!
                  </>
                ) : (
                  <>
                    <HiOutlinePhotograph className="w-4 h-4 mr-1.5" />
                    Copiar Texto con Emojis
                  </>
                )}
              </Button>
            </div>
          </div>
        ) : null}
      </Modal.Body>
    </Modal>
  );
};

export default SocialShareModal;
