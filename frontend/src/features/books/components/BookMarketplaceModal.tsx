import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../../../store/auth';

export interface MarketplaceOffer {
  id: number | null;
  merchant_name: string;
  merchant_type: string;
  format: string;
  format_display: string;
  url: string;
  price: number | null;
  currency: string;
  is_official: boolean;
  is_affiliate: boolean;
  is_custom?: boolean;
  badge?: string;
}

export interface MarketplaceData {
  book_id: number;
  book_title: string;
  author_name: string;
  isbn?: string;
  publisher?: {
    id: number;
    name: string;
    slug: string;
    website?: string;
    is_verified?: boolean;
  } | null;
  can_manage: boolean;
  disclosure: string;
  total_offers: number;
  offers: MarketplaceOffer[];
  by_format: {
    paperback: MarketplaceOffer[];
    ebook: MarketplaceOffer[];
    audiobook: MarketplaceOffer[];
  };
  by_merchant_type: {
    indie: MarketplaceOffer[];
    online: MarketplaceOffer[];
    publisher: MarketplaceOffer[];
  };
}

interface BookMarketplaceModalProps {
  isOpen: boolean;
  onClose: () => void;
  bookId: number;
  bookTitle: string;
  authorName?: string;
}

export const BookMarketplaceModal: React.FC<BookMarketplaceModalProps> = ({
  isOpen,
  onClose,
  bookId,
  bookTitle,
  authorName,
}) => {
  const { token } = useAuthStore();
  const [data, setData] = useState<MarketplaceData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'all' | 'indie' | 'paperback' | 'ebook' | 'audiobook'>('all');

  // Formulario para autores verificados
  const [showAddForm, setShowAddForm] = useState<boolean>(false);
  const [newMerchantName, setNewMerchantName] = useState('');
  const [newUrl, setNewUrl] = useState('');
  const [newFormat, setNewFormat] = useState('paperback');
  const [newMerchantType, setNewMerchantType] = useState('publisher_direct');
  const [newPrice, setNewPrice] = useState('');
  const [submittingLink, setSubmittingLink] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const fetchMarketplaceOffers = async () => {
    setLoading(true);
    setError(null);
    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const res = await fetch(`${apiUrl}/api/v1/books/${bookId}/marketplace/`, {
        headers,
      });

      if (!res.ok) {
        throw new Error('Error al cargar las opciones de compra');
      }

      const json = await res.json();
      setData(json);
    } catch (err: any) {
      setError(err.message || 'No se pudieron recuperar las ofertas comerciales.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchMarketplaceOffers();
    }
  }, [isOpen, bookId]);

  const handleRecordClick = async (offer: MarketplaceOffer) => {
    try {
      await fetch(`${apiUrl}/api/v1/books/${bookId}/marketplace/click/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          merchant_name: offer.merchant_name,
          format: offer.format,
          buy_link_id: offer.id,
        }),
      });
    } catch (e) {
      // Registro no bloqueante
      console.debug('Telemetry error', e);
    }
  };

  const handleCreateOfficialLink = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setSubmittingLink(true);
    setFormError(null);

    try {
      const res = await fetch(`${apiUrl}/api/v1/books/${bookId}/marketplace/links/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          merchant_name: newMerchantName,
          url: newUrl,
          format: newFormat,
          merchant_type: newMerchantType,
          price: newPrice ? parseFloat(newPrice) : null,
          currency: 'EUR',
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || 'Error al guardar el enlace oficial.');
      }

      setNewMerchantName('');
      setNewUrl('');
      setNewPrice('');
      setShowAddForm(false);
      await fetchMarketplaceOffers();
    } catch (err: any) {
      setFormError(err.message || 'Error al crear enlace oficial');
    } finally {
      setSubmittingLink(false);
    }
  };

  const handleDeleteOfficialLink = async (linkId: number) => {
    if (!token) return;
    if (!window.confirm('¿Deseas eliminar este enlace comercial oficial?')) return;

    try {
      const res = await fetch(`${apiUrl}/api/v1/books/marketplace/links/${linkId}/`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (res.ok) {
        await fetchMarketplaceOffers();
      }
    } catch (err) {
      console.error(err);
    }
  };

  if (!isOpen) return null;

  const filteredOffers = data
    ? data.offers.filter((offer) => {
        if (activeTab === 'all') return true;
        if (activeTab === 'indie') return offer.merchant_type === 'indie_network';
        if (activeTab === 'paperback') return offer.format === 'paperback' || offer.format === 'hardcover';
        if (activeTab === 'ebook') return offer.format === 'ebook';
        if (activeTab === 'audiobook') return offer.format === 'audiobook';
        return true;
      })
    : [];

  const getMerchantIcon = (offer: MarketplaceOffer) => {
    const name = offer.merchant_name.toLowerCase();
    if (offer.merchant_type === 'indie_network' || name.includes('todostuslibros')) return '🏪';
    if (name.includes('kindle') || offer.format === 'ebook') return '📱';
    if (name.includes('audible') || offer.format === 'audiobook') return '🎧';
    if (name.includes('amazon')) return '📦';
    if (name.includes('casa del libro')) return '📚';
    if (name.includes('fnac')) return '🏬';
    if (offer.is_official || offer.merchant_type === 'publisher_direct') return '🏛️';
    return '📖';
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="marketplace-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm animate-fade-in"
    >
      <div className="relative w-full max-w-2xl bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Cabecera del modal */}
        <div className="p-5 sm:p-6 border-b border-slate-100 dark:border-slate-800 flex items-start justify-between bg-gradient-to-r from-emerald-500/10 via-teal-500/5 to-transparent">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xl">🛍️</span>
              <span className="text-xs uppercase font-extrabold tracking-wider px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                Marketplace & Librerías
              </span>
            </div>
            <h3 id="marketplace-modal-title" className="text-lg sm:text-xl font-black text-slate-900 dark:text-white">
              Dónde conseguir «{bookTitle}»
            </h3>
            {authorName && (
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Por <span className="font-semibold">{authorName}</span>
              </p>
            )}
          </div>

          <button
            onClick={onClose}
            aria-label="Cerrar modal"
            className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Pestañas de filtrado de formato */}
        <div className="flex items-center gap-1.5 px-5 sm:px-6 pt-3 pb-2 border-b border-slate-100 dark:border-slate-800 overflow-x-auto text-xs font-semibold">
          <button
            onClick={() => setActiveTab('all')}
            className={`px-3 py-1.5 rounded-xl whitespace-nowrap transition-all ${
              activeTab === 'all'
                ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-xs'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            Todas ({data?.offers.length || 0})
          </button>
          <button
            onClick={() => setActiveTab('indie')}
            className={`px-3 py-1.5 rounded-xl whitespace-nowrap flex items-center gap-1 transition-all ${
              activeTab === 'indie'
                ? 'bg-emerald-600 text-white shadow-xs'
                : 'text-emerald-700 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-950/40'
            }`}
          >
            <span>🏪</span>
            <span>Librerías de Barrio</span>
          </button>
          <button
            onClick={() => setActiveTab('paperback')}
            className={`px-3 py-1.5 rounded-xl whitespace-nowrap transition-all ${
              activeTab === 'paperback'
                ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-xs'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            📖 Papel / Físico
          </button>
          <button
            onClick={() => setActiveTab('ebook')}
            className={`px-3 py-1.5 rounded-xl whitespace-nowrap transition-all ${
              activeTab === 'ebook'
                ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-xs'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            📱 Ebook
          </button>
          <button
            onClick={() => setActiveTab('audiobook')}
            className={`px-3 py-1.5 rounded-xl whitespace-nowrap transition-all ${
              activeTab === 'audiobook'
                ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-xs'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            🎧 Audiolibro
          </button>
        </div>

        {/* Contenido principal scrollable */}
        <div className="p-5 sm:p-6 overflow-y-auto space-y-4 flex-1">
          {loading && (
            <div className="py-12 flex flex-col items-center justify-center gap-3 text-slate-500">
              <div className="w-8 h-8 border-3 border-emerald-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-xs font-medium">Buscando librerías y opciones de adquisición...</p>
            </div>
          )}

          {error && !loading && (
            <div className="p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-xs text-rose-700 dark:text-rose-300">
              {error}
            </div>
          )}

          {!loading && !error && filteredOffers.length === 0 && (
            <div className="py-10 text-center text-slate-500 dark:text-slate-400 space-y-2">
              <span className="text-3xl">🔍</span>
              <p className="text-xs font-semibold">No se encontraron opciones para el filtro seleccionado.</p>
            </div>
          )}

          {!loading && !error && filteredOffers.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {filteredOffers.map((offer, idx) => (
                <div
                  key={offer.id || `offer-${idx}`}
                  className={`p-4 rounded-2xl border transition-all flex flex-col justify-between ${
                    offer.merchant_type === 'indie_network'
                      ? 'bg-gradient-to-br from-emerald-50/80 to-teal-50/40 dark:from-emerald-950/30 dark:to-teal-950/20 border-emerald-300 dark:border-emerald-800/80 shadow-xs ring-1 ring-emerald-500/20'
                      : offer.is_official
                        ? 'bg-gradient-to-br from-indigo-50/80 to-purple-50/40 dark:from-indigo-950/30 dark:to-purple-950/20 border-indigo-300 dark:border-indigo-800/80 shadow-xs'
                        : 'bg-slate-50/80 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <div className="flex items-center gap-1.5">
                        <span className="text-lg">{getMerchantIcon(offer)}</span>
                        <h4 className="text-sm font-bold text-slate-900 dark:text-white leading-tight">
                          {offer.merchant_name}
                        </h4>
                      </div>

                      {offer.badge ? (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-200 dark:bg-emerald-900 text-emerald-900 dark:text-emerald-200">
                          {offer.badge}
                        </span>
                      ) : offer.is_official ? (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-200 dark:bg-indigo-900 text-indigo-900 dark:text-indigo-200">
                          Canal Oficial
                        </span>
                      ) : offer.is_affiliate ? (
                        <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300">
                          Afiliado
                        </span>
                      ) : null}
                    </div>

                    <p className="text-xs text-slate-600 dark:text-slate-300">
                      {offer.format_display}
                    </p>

                    {offer.price !== null && offer.price !== undefined && (
                      <p className="text-sm font-black text-slate-900 dark:text-white mt-1">
                        {offer.price.toFixed(2)} {offer.currency}
                      </p>
                    )}
                  </div>

                  <div className="mt-4 flex items-center gap-2 pt-2 border-t border-slate-200/60 dark:border-slate-700/60">
                    <a
                      href={offer.url}
                      target="_blank"
                      rel="noopener noreferrer sponsored"
                      onClick={() => handleRecordClick(offer)}
                      className={`flex-1 py-2 px-3 text-xs font-bold rounded-xl text-center transition-all flex items-center justify-center gap-1.5 ${
                        offer.merchant_type === 'indie_network'
                          ? 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs'
                          : offer.is_official
                            ? 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs'
                            : 'bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:hover:bg-white dark:text-slate-900'
                      }`}
                    >
                      <span>Ver en tienda</span>
                      <span aria-hidden="true">→</span>
                    </a>

                    {offer.is_custom && offer.id && data?.can_manage && (
                      <button
                        onClick={() => handleDeleteOfficialLink(offer.id!)}
                        className="p-2 text-rose-500 hover:text-rose-700 rounded-xl hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors"
                        title="Eliminar este enlace oficial"
                        aria-label="Eliminar enlace"
                      >
                        🗑️
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Panel para autores verificados / administradores */}
          {data?.can_manage && (
            <div className="mt-6 pt-5 border-t border-slate-200 dark:border-slate-800">
              {!showAddForm ? (
                <button
                  onClick={() => setShowAddForm(true)}
                  className="w-full py-2.5 px-4 rounded-2xl border-2 border-dashed border-indigo-300 dark:border-indigo-700/80 hover:bg-indigo-50/50 dark:hover:bg-indigo-950/20 text-xs font-bold text-indigo-700 dark:text-indigo-300 flex items-center justify-center gap-2 transition-all"
                >
                  <span>✍️</span>
                  <span>Añadir enlace oficial de compra o editorial como autor</span>
                </button>
              ) : (
                <form
                  onSubmit={handleCreateOfficialLink}
                  className="p-4 rounded-2xl bg-indigo-50/50 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-800/80 space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold text-indigo-900 dark:text-indigo-200">
                      Publicar enlace comercial oficial
                    </h4>
                    <button
                      type="button"
                      onClick={() => setShowAddForm(false)}
                      className="text-xs text-slate-400 hover:text-slate-600"
                    >
                      Cancelar
                    </button>
                  </div>

                  {formError && (
                    <p className="text-xs text-rose-600 dark:text-rose-400 font-medium">{formError}</p>
                  )}

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300 mb-1">
                        Nombre de la tienda o editorial:
                      </label>
                      <input
                        type="text"
                        required
                        placeholder="Ej: Tienda Oficial, Editorial Planeta"
                        value={newMerchantName}
                        onChange={(e) => setNewMerchantName(e.target.value)}
                        className="w-full text-xs py-1.5 px-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300 mb-1">
                        Formato:
                      </label>
                      <select
                        value={newFormat}
                        onChange={(e) => setNewFormat(e.target.value)}
                        className="w-full text-xs py-1.5 px-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800"
                      >
                        <option value="paperback">Tapa blanda / Bolsillo</option>
                        <option value="hardcover">Tapa dura</option>
                        <option value="ebook">Ebook / Digital</option>
                        <option value="audiobook">Audiolibro</option>
                      </select>
                    </div>

                    <div className="sm:col-span-2">
                      <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300 mb-1">
                        URL directa de compra:
                      </label>
                      <input
                        type="url"
                        required
                        placeholder="https://..."
                        value={newUrl}
                        onChange={(e) => setNewUrl(e.target.value)}
                        className="w-full text-xs py-1.5 px-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300 mb-1">
                        Precio estimado (€):
                      </label>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        placeholder="Ej: 19.90"
                        value={newPrice}
                        onChange={(e) => setNewPrice(e.target.value)}
                        className="w-full text-xs py-1.5 px-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300 mb-1">
                        Tipo de canal:
                      </label>
                      <select
                        value={newMerchantType}
                        onChange={(e) => setNewMerchantType(e.target.value)}
                        className="w-full text-xs py-1.5 px-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800"
                      >
                        <option value="publisher_direct">Editorial / Web oficial del autor</option>
                        <option value="online_retailer">Librería online</option>
                        <option value="indie_network">Red de librerías independientes</option>
                      </select>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={submittingLink}
                    className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-xl shadow transition-all disabled:opacity-50"
                  >
                    {submittingLink ? 'Guardando...' : 'Guardar enlace oficial'}
                  </button>
                </form>
              )}
            </div>
          )}
        </div>

        {/* Pie del modal con declaración ética y legal */}
        <div className="p-4 bg-slate-50 dark:bg-slate-950/80 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 flex flex-col sm:flex-row items-center justify-between gap-2 text-center sm:text-left">
          <p className="max-w-xl">
            🌿 <span className="font-semibold">Compromiso ético:</span> MyBookConnect apoya las librerías de proximidad. Las compras no condicionan las recomendaciones.
          </p>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-200 hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 font-bold text-xs rounded-xl transition-colors whitespace-nowrap"
          >
            Entendido
          </button>
        </div>
      </div>
    </div>
  );
};

export default BookMarketplaceModal;
