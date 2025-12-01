import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button, Card, Dropdown } from 'flowbite-react';
import { useAuthStore } from '../store/auth';
import DOMPurify from 'dompurify';

export function Profile() {
  const { id } = useParams();
  const { user: authUser, token } = useAuthStore();
  const navigate = useNavigate();
  const [profileUser, setProfileUser] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const fetchProfile = async () => {
      setLoading(true);
      setError(null);
      const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
      try {
          let url = `${apiUrl}/api/v1/users/profile/`; 
          if (id) {
              url = `${apiUrl}/api/v1/users/${id}/`;
          }
          
          const res = await fetch(url, {
              headers: { Authorization: `Bearer ${token}` }
          });
          
          if (res.ok) {
              const data = await res.json();
              setProfileUser(data);
          } else {
              if (res.status === 403) {
                  const errData = await res.json();
                  setError(errData.detail || 'No tienes permiso para ver este perfil.');
              } else {
                  setError('Error al cargar el perfil.');
              }
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
    if (!token) {
      navigate('/login');
      return;
    }
    fetchProfile();
  }, [id, token, navigate]);

  const handleAction = async (action: 'follow' | 'unfollow' | 'block' | 'unblock') => {
      if (!profileUser || !token) return;
      const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
      try {
          const res = await fetch(`${apiUrl}/api/v1/users/${profileUser.id}/${action}/`, {
              method: 'POST',
              headers: { Authorization: `Bearer ${token}` }
          });
          if (res.ok) {
              // Refresh profile to update stats and buttons
              fetchProfile();
          } else {
              const err = await res.json();
              alert(err.detail || 'Error al realizar la acción');
          }
      } catch (e) {
          console.error(e);
          alert('Error de conexión');
      }
  };

  if (loading) return <div className="text-center mt-10">Cargando perfil...</div>;
  
  if (error) {
      return (
          <div className="max-w-2xl mx-auto p-4">
            <Card>
                <div className="text-center text-red-600 p-4">
                    <h3 className="text-xl font-bold mb-2">Acceso Restringido</h3>
                    <p>{error}</p>
                    <Button color="light" className="mt-4 mx-auto" onClick={() => navigate(-1)}>Volver</Button>
                </div>
            </Card>
          </div>
      );
  }

  if (!profileUser) return <div className="text-center mt-10 text-red-500">No se pudo cargar el perfil.</div>;
  
  const isOwnProfile = !id || (authUser && String(authUser.id) === String(profileUser.id));
  
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
              <h5 className="text-xl font-bold">{profileUser.first_name ? `${profileUser.first_name} ${profileUser.last_name || ''}` : profileUser.username}</h5>
              <p className="text-gray-600">{profileUser.email}</p>
              {profileUser.location && (
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
                        profileUser.is_following ? (
                            <Button color="light" size="sm" onClick={() => handleAction('unfollow')}>
                                Dejar de seguir
                            </Button>
                        ) : (
                            <Button color="blue" size="sm" onClick={() => handleAction('follow')}>
                                Seguir
                            </Button>
                        )
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
        
        <div className="mt-4">
          <p className="text-sm text-gray-600">
            Privacidad: {profileUser.privacy_level === 'public' ? 'Público' : 
                        profileUser.privacy_level === 'friends' ? 'Solo amigos' : 'Privado'}
          </p>
          {profileUser.birth_date && (
            <p className="text-sm text-gray-600">
              Fecha de nacimiento: {new Date(profileUser.birth_date).toLocaleDateString()}
            </p>
          )}
          {profileUser.bio && (
            <div 
                className="mt-2 text-gray-700 italic prose max-w-none"
                dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(profileUser.bio) }}
            />
          )}
        </div>

        {/* Stats Section */}
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
            <span className="block font-bold text-xl">{profileUser.following_count || 0}</span>
            <span className="text-sm text-gray-500">Siguiendo</span>
          </div>
        </div>
      </Card>
    </div>
  );
}