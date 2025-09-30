import React from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button, Card } from 'flowbite-react';
import { useAuthStore } from '../store/auth';

export function Profile() {
  const { username } = useParams();
  const { user } = useAuthStore();
  const navigate = useNavigate();
  
  // Si no hay usuario autenticado, redirigir a login
  if (!user) {
    navigate('/login');
    return null;
  }
  
  // Si se está viendo un perfil específico y no es el del usuario logado
  const isOwnProfile = !username || username === user.username;
  
  return (
    <div className="max-w-2xl mx-auto p-4">
      <Card>
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-4">
            {user.avatar && (
              <img
                src={user.avatar}
                alt="Profile"
                className="w-20 h-20 rounded-full object-cover"
              />
            )}
            <div>
              <h5 className="text-xl font-bold">{user.first_name ? `${user.first_name} ${user.last_name || ''}` : user.username}</h5>
              <p className="text-gray-600">{user.email}</p>
              {user.location && (
                <p className="text-sm text-gray-500">{user.location}</p>
              )}
            </div>
          </div>
          {isOwnProfile && (
            <Button color="light" onClick={() => navigate('/profile/edit')}>
              Editar perfil
            </Button>
          )}
        </div>
        
        <div className="mt-4">
          <p className="text-sm text-gray-600">
            Privacidad: {user.privacy_level === 'public' ? 'Público' : 
                        user.privacy_level === 'friends' ? 'Solo amigos' : 'Privado'}
          </p>
          {user.birth_date && (
            <p className="text-sm text-gray-600">
              Fecha de nacimiento: {new Date(user.birth_date).toLocaleDateString()}
            </p>
          )}
        </div>
      </Card>
    </div>
  );
}