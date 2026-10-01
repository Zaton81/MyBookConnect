import { useEffect, useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { Button, Card, Dropdown, Spinner } from 'flowbite-react';
import { useAuthStore } from '../../../store/auth';
import { User } from '../../../types/auth';
import DOMPurify from 'dompurify';
import { ReportModal } from '../../moderation';
import { resolveMediaUrl } from '../../../utils/media';
import { GamificationOverviewData } from '../../books/components/gamification';
import { StarRating } from '../../../components/ui';

interface UserReviewItem {
  id: number;
  book: {
    id: number;
    title: string;
    cover?: string;
    author?: { id: number; name: string };
    authors?: { id: number; name: string }[];
  };
  rating: number;
  title?: string;
  text?: string;
  created_at: string;
  likes_count: number;
  comments_count: number;
  user_has_liked?: boolean;
}

interface WallPostItem {
  id: number;
  author: {
    id: number;
    username: string;
    avatar?: string;
  };
  target_user: {
    id: number;
    username: string;
  };
  content: string;
  book?: {
    id: number;
    title: string;
    cover?: string;
    author?: string;
  };
  likes_count: number;
  comments_count: number;
  is_pinned: boolean;
  user_has_liked: boolean;
  is_owner: boolean;
  comments: {
    id: number;
    user: {
      id: number;
      username: string;
      avatar?: string;
    };
    text: string;
    created_at: string;
    is_owner: boolean;
  }[];
  created_at: string;
}

export function Profile() {
  const { userId, id } = useParams<{ userId?: string; id?: string }>();
  const profileId = userId || id;
  const { user: currentUser, token, followUser, unfollowUser, getFollowStatus } = useAuthStore();
  const navigate = useNavigate();
  const [profileUser, setProfileUser] = useState<User | null>(null);
  const [isFollowing, setIsFollowing] = useState(false);
  const [isMutual, setIsMutual] = useState(false);
  const [isReportingUser, setIsReportingUser] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [restrictedDetail, setRestrictedDetail] = useState<string | null>(null);
  const [readingMatch, setReadingMatch] = useState<{
    match_percentage: number;
    common_books_count: number;
    common_books: { id: number; title: string; cover?: string; author_name: string }[];
  } | null>(null);
  const [gamification, setGamification] = useState<GamificationOverviewData | null>(null);

  // Pestañas del perfil: Muro (por defecto), Reseñas y Logros
  const [activeTab, setActiveTab] = useState<'wall' | 'reviews' | 'gamification'>('wall');

  // Estado del Muro Social
  const [posts, setPosts] = useState<WallPostItem[]>([]);
  const [loadingPosts, setLoadingPosts] = useState(false);
  const [newPostContent, setNewPostContent] = useState('');
  const [isPosting, setIsPosting] = useState(false);
  const [openCommentsPostId, setOpenCommentsPostId] = useState<number | null>(null);
  const [commentInputs, setCommentInputs] = useState<{ [postId: number]: string }>({});
  const [submittingComment, setSubmittingComment] = useState<{ [postId: number]: boolean }>({});

  // Estado de Reseñas del Usuario
  const [userReviews, setUserReviews] = useState<UserReviewItem[]>([]);
  const [loadingReviews, setLoadingReviews] = useState(false);

  const isOwnProfile = !profileId || (currentUser && String(currentUser.id) === String(profileId));
  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  const fetchProfile = async () => {
    if (!token) {
      navigate('/');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const url = isOwnProfile
        ? `${apiUrl}/api/v1/auth/profile/`
        : `${apiUrl}/api/v1/users/${profileId}/`;

      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        const data = await res.json();
        setProfileUser(data);
        setIsFollowing(!!data.is_following);
        if (!isOwnProfile && profileId) {
          try {
            const followStatus = await getFollowStatus(Number(profileId));
            setIsFollowing(followStatus.is_following);
            setIsMutual(followStatus.is_mutual);
          } catch {
            setIsMutual(false);
          }

          // Cargar afinidad lectora
          try {
            const matchRes = await fetch(`${apiUrl}/api/v1/books/match/${profileId}/`, {
              headers: { Authorization: `Bearer ${token}` },
            });
            if (matchRes.ok) {
              const matchData = await matchRes.json();
              setReadingMatch(matchData);
            }
          } catch (e) {
            console.warn('Error fetching reading match', e);
          }
        }

        // Cargar gamificación y logros
        try {
          const gamRes = await fetch(
            `${apiUrl}/api/v1/gamification/overview/${profileId ? `?user_id=${profileId}` : ''}`,
            { headers: { Authorization: `Bearer ${token}` } }
          );
          if (gamRes.ok) {
            const gamData = await gamRes.json();
            setGamification(gamData);
          }
        } catch (e) {
          console.warn('Error fetching gamification in profile', e);
        }

        // Cargar muro y reseñas del usuario
        fetchWallPosts(data.id);
        fetchUserReviews(data.id);
      } else if (res.status === 403) {
        const errData = await res.json().catch(() => ({}));
        setError('Acceso restringido');
        setRestrictedDetail(errData.detail || 'Este perfil es privado.');
        setProfileUser(null);
      } else {
        setError('Error al cargar el perfil.');
        setProfileUser(null);
      }
    } catch (e) {
      console.error(e);
      setError('Error de conexión.');
    } finally {
      setLoading(false);
    }
  };

  const fetchWallPosts = async (targetUserId: number) => {
    setLoadingPosts(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/users/${targetUserId}/posts/`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        const data = await res.json();
        setPosts(Array.isArray(data) ? data : data.results || []);
      }
    } catch (err) {
      console.error('Error fetching wall posts:', err);
    } finally {
      setLoadingPosts(false);
    }
  };

  const fetchUserReviews = async (targetUserId: number) => {
    setLoadingReviews(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/reviews/?user=${targetUserId}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        const data = await res.json();
        setUserReviews(Array.isArray(data) ? data : data.results || []);
      }
    } catch (err) {
      console.error('Error fetching user reviews:', err);
    } finally {
      setLoadingReviews(false);
    }
  };

  const handleCreatePost = async () => {
    if (!newPostContent.trim() || !profileUser || !token) return;
    setIsPosting(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/users/${profileUser.id}/posts/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ content: newPostContent.trim() }),
      });
      if (res.ok) {
        const createdPost = await res.json();
        setPosts((prev) => [createdPost, ...prev]);
        setNewPostContent('');
      } else {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || 'No se pudo publicar en el muro.');
      }
    } catch (err) {
      console.error('Error creating post:', err);
    } finally {
      setIsPosting(false);
    }
  };

  const handleLikePost = async (postId: number) => {
    if (!token) {
      navigate('/login');
      return;
    }
    try {
      const res = await fetch(`${apiUrl}/api/v1/users/posts/${postId}/like/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setPosts((prev) =>
          prev.map((p) =>
            p.id === postId
              ? { ...p, user_has_liked: data.liked, likes_count: data.likes_count }
              : p
          )
        );
      }
    } catch (err) {
      console.error('Error toggling like:', err);
    }
  };

  const handleAddComment = async (postId: number) => {
    const text = (commentInputs[postId] || '').trim();
    if (!text || !token) return;

    setSubmittingComment((prev) => ({ ...prev, [postId]: true }));
    try {
      const res = await fetch(`${apiUrl}/api/v1/users/posts/${postId}/comments/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ text }),
      });
      if (res.ok) {
        const newComment = await res.json();
        setPosts((prev) =>
          prev.map((p) =>
            p.id === postId
              ? {
                  ...p,
                  comments: [...(p.comments || []), newComment],
                  comments_count: (p.comments_count || 0) + 1,
                }
              : p
          )
        );
        setCommentInputs((prev) => ({ ...prev, [postId]: '' }));
      }
    } catch (err) {
      console.error('Error adding comment:', err);
    } finally {
      setSubmittingComment((prev) => ({ ...prev, [postId]: false }));
    }
  };

  const handleDeletePost = async (postId: number) => {
    if (!token || !confirm('¿Estás seguro de que deseas eliminar esta publicación?')) return;
    try {
      const res = await fetch(`${apiUrl}/api/v1/users/posts/${postId}/`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setPosts((prev) => prev.filter((p) => p.id !== postId));
      }
    } catch (err) {
      console.error('Error deleting post:', err);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, [profileId, token]);

  const handleFollowToggle = async () => {
    if (!profileId || !token) return;
    const targetId = Number(profileId);
    try {
      if (isFollowing) {
        await unfollowUser(targetId);
        setIsFollowing(false);
        setIsMutual(false);
      } else {
        await followUser(targetId);
        setIsFollowing(true);
        const status = await getFollowStatus(targetId);
        setIsMutual(status.is_mutual);
      }
      fetchProfile();
    } catch (err) {
      console.error('Error toggling follow', err);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[50vh]">
        <Spinner size="xl" />
      </div>
    );
  }

  if (error || !profileUser) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold text-gray-700 dark:text-gray-300">
          {error || 'Usuario no encontrado'}
        </h2>
        {restrictedDetail && (
          <p className="text-gray-500 mt-2">{restrictedDetail}</p>
        )}
        <Button className="mt-4 mx-auto" onClick={() => navigate(-1)}>
          Volver
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      {/* ── Tarjeta Principal de Perfil ── */}
      <Card className="p-4 sm:p-6 shadow-md border-slate-200 dark:border-slate-700">
        <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6">
          <img
            src={resolveMediaUrl(profileUser.avatar) || '/default-avatar.png'}
            alt={profileUser.username}
            className="w-28 h-28 sm:w-32 sm:h-32 rounded-full object-cover border-4 border-teal-500 shadow-sm"
          />

          <div className="flex-1 text-center sm:text-left space-y-2">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
              <div>
                <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white flex items-center justify-center sm:justify-start gap-2">
                  <span>
                    {profileUser.first_name || profileUser.last_name
                      ? `${profileUser.first_name || ''} ${profileUser.last_name || ''}`.trim()
                      : profileUser.username}
                  </span>
                  {profileUser.is_staff && (
                    <span className="bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 text-xs px-2.5 py-0.5 rounded-full font-semibold">
                      Staff
                    </span>
                  )}
                  {profileUser.role === 'ADMIN' && (
                    <span className="bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 text-xs px-2.5 py-0.5 rounded-full font-semibold">
                      Admin
                    </span>
                  )}
                  {(profileUser.account_type === 'author' || profileUser.account_type === 'both' || profileUser.is_author) && (
                    <span className="bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-200 text-xs px-2.5 py-0.5 rounded-full font-bold flex items-center gap-1 shadow-xs border border-amber-200 dark:border-amber-800">
                      ✍️ Escritor
                    </span>
                  )}
                  {(profileUser.account_type === 'reader' || profileUser.account_type === 'both') && (
                    <span className="bg-sky-100 dark:bg-sky-900/40 text-sky-800 dark:text-sky-200 text-xs px-2.5 py-0.5 rounded-full font-semibold flex items-center gap-1">
                      📖 Lector
                    </span>
                  )}
                </h1>
                <p className="text-slate-500 dark:text-slate-400 font-medium text-sm">
                  @{profileUser.username}
                </p>
              </div>

              {/* Acciones principales */}
              <div className="flex items-center gap-2">
                {isOwnProfile ? (
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      color="light"
                      className="font-semibold shadow-xs"
                      onClick={() => navigate('/settings')}
                    >
                      Editar perfil
                    </Button>
                    <Button
                      size="sm"
                      color="light"
                      className="font-semibold shadow-xs"
                      onClick={() => navigate('/statistics')}
                    >
                      📊 Estadísticas
                    </Button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      color={isFollowing ? 'light' : 'teal'}
                      className="font-semibold shadow-xs"
                      onClick={handleFollowToggle}
                    >
                      {isFollowing ? (isMutual ? 'Amigos' : 'Siguiendo') : 'Seguir'}
                    </Button>
                    <Button
                      size="sm"
                      color="light"
                      className="font-semibold shadow-xs"
                      onClick={() => navigate(`/messages?userId=${profileUser.id}`)}
                    >
                      💬 Mensaje
                    </Button>
                    <Dropdown label="•••" inline arrowIcon={false} size="sm">
                      <Dropdown.Item
                        className="text-red-600 dark:text-red-400"
                        onClick={() => setIsReportingUser(true)}
                      >
                        ⚠️ Denunciar perfil
                      </Dropdown.Item>
                    </Dropdown>
                  </div>
                )}
              </div>
            </div>

            {profileUser.bio && (
              <div
                className="text-slate-700 dark:text-slate-300 text-sm mt-3 prose dark:prose-invert max-w-none"
                dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(profileUser.bio) }}
              />
            )}

            {/* Categorías Favoritas */}
            {profileUser.favorite_categories && profileUser.favorite_categories.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5 pt-2">
                <span className="text-xs font-semibold text-slate-400">Géneros favoritos:</span>
                {profileUser.favorite_categories.map((cat: any) => (
                  <span
                    key={cat.id || cat.slug}
                    className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-teal-50 dark:bg-teal-950/40 text-teal-700 dark:text-teal-300 border border-teal-200/50 dark:border-teal-800/40"
                  >
                    {cat.name}
                  </span>
                ))}
              </div>
            )}

            {/* Afinidad Lectora si se visita a otro lector */}
            {readingMatch && readingMatch.match_percentage > 0 && (
              <div className="flex items-center gap-2 pt-2 text-xs">
                <span className="font-bold text-teal-600 dark:text-teal-400 flex items-center gap-1">
                  🎯 {readingMatch.match_percentage}% de afinidad lectora
                </span>
                {readingMatch.common_books_count > 0 && (
                  <span className="text-slate-400">
                    ({readingMatch.common_books_count} {readingMatch.common_books_count === 1 ? 'libro en común' : 'libros en común'})
                  </span>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Barra de métricas clickeables */}
        <div className="grid grid-cols-3 gap-4 mt-6 border-t border-slate-100 dark:border-slate-700/60 pt-4 text-center">
          <div>
            <span className="block font-extrabold text-xl text-slate-900 dark:text-white">
              {profileUser.books_read_count || 0}
            </span>
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Libros leídos</span>
          </div>
          <div
            onClick={() => setActiveTab('reviews')}
            className="cursor-pointer group hover:opacity-80 transition-opacity"
          >
            <span className="block font-extrabold text-xl text-teal-600 dark:text-teal-400 group-hover:underline">
              {profileUser.reviews_count || userReviews.length || 0}
            </span>
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400 group-hover:text-teal-600">
              Reseñas ➔
            </span>
          </div>
          <div>
            <span className="block font-extrabold text-xl text-slate-900 dark:text-white">
              {profileUser.following_count ?? profileUser.following?.length ?? 0}
            </span>
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Siguiendo</span>
          </div>
        </div>
      </Card>

      {/* ── Barra de Pestañas de Navegación del Perfil ── */}
      <div className="flex border-b border-slate-200 dark:border-slate-700 gap-2">
        <button
          type="button"
          onClick={() => setActiveTab('wall')}
          className={`flex items-center gap-2 py-3 px-5 font-bold text-sm border-b-2 transition-colors ${
            activeTab === 'wall'
              ? 'border-teal-600 text-teal-600 dark:text-teal-400 dark:border-teal-400'
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          <span>📰</span>
          <span>Muro ({posts.length})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('reviews')}
          className={`flex items-center gap-2 py-3 px-5 font-bold text-sm border-b-2 transition-colors ${
            activeTab === 'reviews'
              ? 'border-teal-600 text-teal-600 dark:text-teal-400 dark:border-teal-400'
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          <span>⭐</span>
          <span>Reseñas ({profileUser.reviews_count || userReviews.length})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('gamification')}
          className={`flex items-center gap-2 py-3 px-5 font-bold text-sm border-b-2 transition-colors ${
            activeTab === 'gamification'
              ? 'border-teal-600 text-teal-600 dark:text-teal-400 dark:border-teal-400'
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          <span>🏆</span>
          <span>Logros y Lectura</span>
        </button>
      </div>

      {/* ── Contenido de la Pestaña: Muro Social ── */}
      {activeTab === 'wall' && (
        <div className="space-y-6">
          {/* Compositor para publicar en el muro */}
          {currentUser && (
            <Card className="p-4 sm:p-5 shadow-xs border-slate-200 dark:border-slate-700">
              <div className="flex gap-3">
                <img
                  src={resolveMediaUrl(currentUser.avatar) || '/default-avatar.png'}
                  alt={currentUser.username}
                  className="w-10 h-10 rounded-full object-cover shrink-0 border border-slate-200 dark:border-slate-600"
                />
                <div className="flex-1 space-y-3">
                  <textarea
                    rows={3}
                    value={newPostContent}
                    onChange={(e) => setNewPostContent(e.target.value)}
                    placeholder={
                      isOwnProfile
                        ? '¿Qué estás leyendo, pensando o descubriendo hoy?...'
                        : `Escribe algo en el muro de @${profileUser.username}...`
                    }
                    className="w-full text-sm rounded-xl border-slate-200 dark:border-slate-700 dark:bg-slate-800/80 dark:text-white focus:ring-teal-500 focus:border-teal-500 resize-none p-3"
                    maxLength={2000}
                  />
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] text-slate-400">
                      {newPostContent.length}/2000 caracteres
                    </span>
                    <Button
                      size="sm"
                      color="teal"
                      disabled={!newPostContent.trim() || isPosting}
                      onClick={handleCreatePost}
                      className="font-bold shadow-xs"
                    >
                      {isPosting ? <Spinner size="sm" /> : 'Publicar en el muro'}
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          )}

          {/* Timeline de publicaciones del muro */}
          {loadingPosts ? (
            <div className="flex justify-center py-8">
              <Spinner size="md" />
            </div>
          ) : posts.length === 0 ? (
            <div className="text-center py-12 bg-slate-50 dark:bg-slate-800/40 rounded-2xl border border-dashed border-slate-200 dark:border-slate-700 p-8">
              <span className="text-4xl block mb-2">✍️</span>
              <h3 className="text-base font-bold text-slate-700 dark:text-slate-300">
                Aún no hay publicaciones en este muro
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto mt-1">
                {isOwnProfile
                  ? 'Comparte tu primera reflexión literaria o libro favorito con la comunidad.'
                  : `¡Sé el primero en dejarle un mensaje o recomendación a @${profileUser.username}!`}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {posts.map((post) => (
                <Card
                  key={post.id}
                  className="p-4 sm:p-5 shadow-xs border-slate-200 dark:border-slate-700 space-y-3"
                >
                  {/* Encabezado del post */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Link to={`/users/${post.author.id}`}>
                        <img
                          src={resolveMediaUrl(post.author.avatar) || '/default-avatar.png'}
                          alt={post.author.username}
                          className="w-10 h-10 rounded-full object-cover border border-slate-200 dark:border-slate-700"
                        />
                      </Link>
                      <div>
                        <Link
                          to={`/users/${post.author.id}`}
                          className="text-sm font-bold text-slate-900 dark:text-white hover:text-teal-600 hover:underline"
                        >
                          @{post.author.username}
                        </Link>
                        <div className="text-[11px] text-slate-400">
                          {new Date(post.created_at).toLocaleDateString(undefined, {
                            day: 'numeric',
                            month: 'short',
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </div>
                      </div>
                    </div>

                    {post.is_owner && (
                      <button
                        type="button"
                        onClick={() => handleDeletePost(post.id)}
                        className="text-slate-400 hover:text-red-500 transition-colors text-xs p-1"
                        title="Eliminar publicación"
                      >
                        🗑️
                      </button>
                    )}
                  </div>

                  {/* Contenido del post */}
                  <div className="text-slate-800 dark:text-slate-200 text-sm whitespace-pre-wrap leading-relaxed">
                    {post.content}
                  </div>

                  {/* Libro vinculado si existe */}
                  {post.book && (
                    <Link
                      to={`/books/${post.book.id}`}
                      className="flex items-center gap-3 p-3 bg-slate-50 dark:bg-slate-800/80 rounded-xl border border-slate-200/60 dark:border-slate-700/60 hover:border-teal-400 transition-colors group"
                    >
                      {post.book.cover ? (
                        <img
                          src={resolveMediaUrl(post.book.cover)}
                          alt={post.book.title}
                          className="w-10 h-14 object-cover rounded shadow-xs"
                        />
                      ) : (
                        <div className="w-10 h-14 bg-teal-100 dark:bg-teal-900/40 rounded flex items-center justify-center text-teal-600 font-bold text-xs">
                          📖
                        </div>
                      )}
                      <div>
                        <div className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-teal-600 transition-colors">
                          {post.book.title}
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-slate-400">
                          {post.book.author || 'Autor desconocido'}
                        </div>
                      </div>
                    </Link>
                  )}

                  {/* Barra de Interacción: Me gusta y Comentarios */}
                  <div className="flex items-center gap-4 pt-2 border-t border-slate-100 dark:border-slate-700/60">
                    <button
                      type="button"
                      onClick={() => handleLikePost(post.id)}
                      className={`flex items-center gap-1.5 text-xs font-bold transition-transform active:scale-95 ${
                        post.user_has_liked
                          ? 'text-red-500'
                          : 'text-slate-500 hover:text-red-500'
                      }`}
                    >
                      <span className="text-base">{post.user_has_liked ? '❤️' : '🤍'}</span>
                      <span>{post.likes_count}</span>
                    </button>

                    <button
                      type="button"
                      onClick={() =>
                        setOpenCommentsPostId(openCommentsPostId === post.id ? null : post.id)
                      }
                      className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-teal-600 transition-colors"
                    >
                      <span className="text-base">💬</span>
                      <span>
                        {post.comments_count} {post.comments_count === 1 ? 'comentario' : 'comentarios'}
                      </span>
                    </button>
                  </div>

                  {/* Sección desplegable de comentarios */}
                  {openCommentsPostId === post.id && (
                    <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700 space-y-3">
                      {post.comments && post.comments.length > 0 && (
                        <div className="space-y-2">
                          {post.comments.map((comm) => (
                            <div
                              key={comm.id}
                              className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 text-xs flex gap-2.5 items-start"
                            >
                              <Link to={`/users/${comm.user.id}`}>
                                <img
                                  src={resolveMediaUrl(comm.user.avatar) || '/default-avatar.png'}
                                  alt={comm.user.username}
                                  className="w-7 h-7 rounded-full object-cover shrink-0"
                                />
                              </Link>
                              <div className="flex-1">
                                <div className="flex items-center justify-between">
                                  <Link
                                    to={`/users/${comm.user.id}`}
                                    className="font-bold text-slate-900 dark:text-white hover:underline"
                                  >
                                    @{comm.user.username}
                                  </Link>
                                  <span className="text-[10px] text-slate-400">
                                    {new Date(comm.created_at).toLocaleDateString(undefined, {
                                      month: 'short',
                                      day: 'numeric',
                                    })}
                                  </span>
                                </div>
                                <div className="text-slate-700 dark:text-slate-300 mt-0.5">
                                  {comm.text}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Caja de nuevo comentario */}
                      {currentUser && (
                        <div className="flex gap-2">
                          <input
                            type="text"
                            placeholder="Escribe un comentario..."
                            value={commentInputs[post.id] || ''}
                            onChange={(e) =>
                              setCommentInputs((prev) => ({ ...prev, [post.id]: e.target.value }))
                            }
                            onKeyDown={(e) => {
                              if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                handleAddComment(post.id);
                              }
                            }}
                            className="flex-1 text-xs rounded-xl border-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:text-white px-3 py-1.5 focus:ring-teal-500 focus:border-teal-500"
                          />
                          <Button
                            size="xs"
                            color="teal"
                            disabled={!(commentInputs[post.id] || '').trim() || submittingComment[post.id]}
                            onClick={() => handleAddComment(post.id)}
                          >
                            {submittingComment[post.id] ? <Spinner size="xs" /> : 'Enviar'}
                          </Button>
                        </div>
                      )}
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Contenido de la Pestaña: Reseñas del Usuario ── */}
      {activeTab === 'reviews' && (
        <div className="space-y-4">
          {loadingReviews ? (
            <div className="flex justify-center py-8">
              <Spinner size="md" />
            </div>
          ) : userReviews.length === 0 ? (
            <div className="text-center py-12 bg-slate-50 dark:bg-slate-800/40 rounded-2xl border border-dashed border-slate-200 dark:border-slate-700 p-8">
              <span className="text-4xl block mb-2">⭐</span>
              <h3 className="text-base font-bold text-slate-700 dark:text-slate-300">
                Aún no hay reseñas publicadas
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto mt-1">
                {isOwnProfile
                  ? 'Valora y comparte tu opinión sobre los libros que has leído en tu biblioteca.'
                  : `Este usuario todavía no ha compartido valoraciones u opiniones públicas.`}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {userReviews.map((rev) => {
                const authorsDisplay =
                  rev.book.authors && rev.book.authors.length > 0
                    ? rev.book.authors.map((a) => a.name).join(', ')
                    : rev.book.author?.name || 'Autor desconocido';

                return (
                  <Card
                    key={rev.id}
                    className="p-4 sm:p-5 shadow-xs border-slate-200 dark:border-slate-700 hover:border-teal-300 transition-colors"
                  >
                    <div className="flex flex-col sm:flex-row gap-4">
                      {/* Portada del libro */}
                      <Link to={`/books/${rev.book.id}`} className="shrink-0 mx-auto sm:mx-0">
                        {rev.book.cover ? (
                          <img
                            src={resolveMediaUrl(rev.book.cover)}
                            alt={rev.book.title}
                            className="w-20 h-28 object-cover rounded-lg shadow-sm border border-slate-200 dark:border-slate-700"
                          />
                        ) : (
                          <div className="w-20 h-28 bg-teal-50 dark:bg-teal-950/40 border border-teal-200/60 dark:border-teal-800/40 rounded-lg flex items-center justify-center text-teal-600 font-bold text-xs p-2 text-center">
                            📖
                          </div>
                        )}
                      </Link>

                      {/* Detalles de la reseña */}
                      <div className="flex-1 space-y-2">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                          <div>
                            <Link
                              to={`/books/${rev.book.id}`}
                              className="text-base font-extrabold text-slate-900 dark:text-white hover:text-teal-600 dark:hover:text-teal-400 hover:underline"
                            >
                              {rev.book.title}
                            </Link>
                            <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                              por {authorsDisplay}
                            </p>
                          </div>

                          <span className="text-[11px] text-slate-400">
                            {new Date(rev.created_at).toLocaleDateString(undefined, {
                              year: 'numeric',
                              month: 'short',
                              day: 'numeric',
                            })}
                          </span>
                        </div>

                        {/* Estrellas 1 - 5 */}
                        <div className="flex items-center gap-2">
                          <StarRating rating={rev.rating} size="sm" />
                          <span className="text-xs font-bold text-slate-700 dark:text-slate-300">
                            {rev.rating}/5 estrellas
                          </span>
                        </div>

                        {rev.title && (
                          <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                            {rev.title}
                          </h4>
                        )}

                        {rev.text && (
                          <p className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap">
                            {rev.text}
                          </p>
                        )}

                        <div className="flex items-center gap-4 pt-2 text-xs text-slate-400 font-medium">
                          <span>❤️ {rev.likes_count || 0} me gusta</span>
                          <span>💬 {rev.comments_count || 0} comentarios</span>
                        </div>
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ── Contenido de la Pestaña: Logros y Gamificación ── */}
      {activeTab === 'gamification' && (
        <Card className="p-4 sm:p-6 shadow-xs border-slate-200 dark:border-slate-700 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-2xl">🏆</span>
              <h3 className="text-base font-bold text-slate-900 dark:text-white">
                Logros y Progreso Lector
              </h3>
            </div>
            <button
              type="button"
              onClick={() =>
                navigate(profileId ? `/users/${profileId}/statistics` : '/statistics')
              }
              className="text-xs font-semibold text-teal-600 dark:text-teal-400 hover:underline"
            >
              Ver estadísticas completas ➔
            </button>
          </div>

          {gamification ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {/* Racha */}
                <div className="p-4 rounded-2xl bg-gradient-to-br from-amber-50 to-orange-50 dark:from-slate-700/60 dark:to-orange-950/20 border border-amber-100/80 dark:border-amber-900/40 flex items-center gap-3">
                  <span className="text-3xl">🔥</span>
                  <div>
                    <div className="text-lg font-extrabold text-amber-700 dark:text-amber-300">
                      {gamification.streak?.current_streak || 0}{' '}
                      {gamification.streak?.current_streak === 1 ? 'día' : 'días'}
                    </div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">Racha activa de lectura</div>
                  </div>
                </div>

                {/* Objetivo anual */}
                <div className="p-4 rounded-2xl bg-gradient-to-br from-teal-50 to-emerald-50 dark:from-slate-700/60 dark:to-teal-950/20 border border-teal-100/80 dark:border-teal-900/40 flex items-center gap-3">
                  <span className="text-3xl">🎯</span>
                  <div>
                    <div className="text-lg font-extrabold text-teal-700 dark:text-teal-300">
                      {gamification.goal?.has_goal
                        ? `${gamification.goal.current_books}/${gamification.goal.target_books} libros`
                        : 'Sin meta fija'}
                    </div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">
                      Meta {gamification.goal?.year || new Date().getFullYear()} ({gamification.goal?.percentage || 0}%)
                    </div>
                  </div>
                </div>
              </div>

              {/* Insignias */}
              {gamification.badges && (
                <div className="pt-2">
                  <div className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-3 flex items-center justify-between">
                    <span>Insignias desbloqueadas:</span>
                    <span className="text-slate-400">
                      {gamification.badges.unlocked_count} de {gamification.badges.total_badges}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                    {gamification.badges.list.map((b) => (
                      <div
                        key={b.id}
                        className={`p-3 rounded-xl border flex flex-col items-center text-center gap-1.5 transition-all ${
                          b.unlocked
                            ? 'bg-white dark:bg-slate-700 border-teal-200 dark:border-teal-800 shadow-xs'
                            : 'bg-slate-50 dark:bg-slate-800/40 border-slate-200 dark:border-slate-700 opacity-40 grayscale'
                        }`}
                      >
                        <span className="text-2xl">{b.icon}</span>
                        <span className="text-xs font-bold text-slate-900 dark:text-white line-clamp-1">
                          {b.name}
                        </span>
                        <span className="text-[10px] text-slate-500 dark:text-slate-400 line-clamp-2">
                          {b.description}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-6 text-xs text-slate-400">
              Cargando estadísticas de lectura...
            </div>
          )}
        </Card>
      )}

      {/* Modal para denunciar perfil de usuario */}
      {profileUser && (
        <ReportModal
          isOpen={isReportingUser}
          onClose={() => setIsReportingUser(false)}
          targetType="user"
          targetId={profileUser.id}
          targetTitle={`@${profileUser.username}`}
        />
      )}
    </div>
  );
}

export default Profile;
