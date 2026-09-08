import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button, Card, Dropdown, Spinner } from 'flowbite-react';
import { useAuthStore } from '../store/auth';
import { User } from '../types/auth';
import DOMPurify from 'dompurify';

export function Profile() {
  const { userId, id } = useParams<{ userId?: string; id?: string }>();
  const profileId = userId || id;
  const { user: currentUser, token, followUser, unfollowUser, getFollowStatus } = useAuthStore();
  const navigate = useNavigate();
  const [profileUser, setProfileUser] = useState<User | null>(null);
  const [isFollowing, setIsFollowing] = useState(false);
  const [isMutual, setIsMutual] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isOwnProfile = !profileId || (currentUser && String(currentUser.id) === String(profileId));

  const fetchProfile = async () => {
    if (!token) {
      navigate('/');
      return;
    }
    setLoading(true);
    setError(null);
    const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
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
        }
      } else if (res.status === 403) {
        const errData = await res.json().catch(() => ({}));
        setError(errData.detail || 'No tienes permiso para ver este perfil.');
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

  useEffect(() => {
    fetchProfile();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profileId, token]);

  const handleAction = async (action: 'follow' | 'unfollow' | 'block' | 'unblock') => {
    if (!profileUser || !token) return;
    const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
    try {
      if (action === 'follow') {
        await followUser(profileUser.id);
      } else if (action === 'unfollow') {
        await unfollowUser(profileUser.id);
      } else {
        const res = await fetch(`${apiUrl}/api/v1/users/${profileUser.id}/${action}/`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          alert(err.detail || 'Error al realizar la acción');
          return;
        }
      }
      await fetchProfile();
    } catch (e: any) {
      console.error(e);
      alert(e.message || 'Error de conexión');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[40vh]">
        <Spinner size="xl" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto p-4">
        <Card>
          <div className="text-center text-red-600 p-4">
            <h3 className="text-xl font-bold mb-2">Acceso restringido</h3>
            <p>{error}</p>
            <Button color="light" className="mt-4 mx-auto" onClick={() => navigate(-1)}>Volver</Button>
          </div>
        </Card>
      </div>
    );
  }

  if (!profileUser) {
    return <div className="text-center mt-10 text-red-500">No se pudo cargar el perfil.</div>;
  }

  const isPublic = profileUser.privacy_level === 'public';
  const canShow = (flag?: boolean) => Boolean(isOwnProfile || (isPublic && flag));

  return (
    <div className="max-w-2xl mx-auto p-4">
      <Card>
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-4">
            {profileUser.avatar ? (
              <img
                src={profileUser.avatar}
                alt="Profile"
                className="w-20 h-20 rounded-full object-cover"
              />
            ) : (
              <div className="w-20 h-20 rounded-full bg-gray-200 flex items-center justify-center text-gray-500">
                No img
              </div>
            )}
            <div>
              <h5 className="text-xl font-bold">
                {profileUser.first_name ? `${profileUser.first_name} ${profileUser.last_name || ''}` : profileUser.username}
              </h5>
              <p className="text-sm text-gray-500">@{profileUser.username}</p>
              {(isOwnProfile || canShow(profileUser.show_email)) && (
                <p className="text-gray-600">{profileUser.email}</p>
              )}
              {profileUser.location && (isOwnProfile || canShow(profileUser.show_location)) && (
                <p className="text-sm text-gray-500">{profileUser.location}</p>
              )}
            </div>
          </div>

          <div className="flex gap-2">
            {isOwnProfile ? (
              <Button color="light" onClick={() => navigate('/profile/edit')}>
                Editar perfil
              </Button>
            ) : (
              <>
                {!profileUser.is_blocked && (
                  isFollowing || profileUser.is_following ? (
                    <Button color="light" size="sm" onClick={() => handleAction('unfollow')}>
                      Dejar de seguir
                    </Button>
                  ) : (
                    <Button color="blue" size="sm" onClick={() => handleAction('follow')}>
                      Seguir
                    </Button>
                  )
                )}
                {isMutual && (
                  <Button size="sm" color="light" onClick={() => alert('El chat se activará en un paso posterior')}>
                    Mensaje
                  </Button>
                )}
                <Dropdown label="" renderTrigger={() => <Button color="light" size="sm">...</Button>}>
                  {profileUser.is_blocked ? (
                    <Dropdown.Item onClick={() => handleAction('unblock')}>Desbloquear</Dropdown.Item>
                  ) : (
                    <Dropdown.Item onClick={() => handleAction('block')} className="text-red-600">Bloquear</Dropdown.Item>
                  )}
                </Dropdown>
              </>
            )}
          </div>
        </div>

        <div className="mt-4 space-y-2">
          <p className="text-sm text-gray-600">
            Privacidad: {profileUser.privacy_level === 'public' ? 'Público' :
                        profileUser.privacy_level === 'friends' ? 'Solo amigos' : 'Privado'}
          </p>
          {isMutual && !isOwnProfile && (
            <span className="text-green-600 text-sm font-medium">Amistad mutua</span>
          )}
          {profileUser.birth_date && (isOwnProfile || canShow(profileUser.show_birth_date)) && (
            <p className="text-sm text-gray-600">
              Fecha de nacimiento: {new Date(profileUser.birth_date).toLocaleDateString()}
            </p>
          )}
          {profileUser.bio && (isOwnProfile || canShow(profileUser.show_bio)) && (
            <div
              className="mt-2 text-gray-700 italic prose max-w-none"
              dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(profileUser.bio) }}
            />
          )}
        </div>

        <div className="grid grid-cols-3 gap-4 mt-6 border-t pt-4 text-center">
          <div>
            <span className="block font-bold text-xl">{profileUser.books_read_count || 0}</span>
            <span className="text-sm text-gray-500">Libros leídos</span>
          </div>
          <div>
            <span className="block font-bold text-xl">{profileUser.reviews_count || 0}</span>
            <span className="text-sm text-gray-500">Reseñas</span>
          </div>
          <div>
            <span className="block font-bold text-xl">{profileUser.following_count ?? profileUser.following?.length ?? 0}</span>
            <span className="text-sm text-gray-500">Siguiendo</span>
          </div>
        </div>
      </Card>
    </div>
  );
}
