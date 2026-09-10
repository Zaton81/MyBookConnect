import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Card, Tabs, Spinner } from 'flowbite-react';
import { useAuthStore } from '../store/auth';
import { User } from '../types/auth';

export function Friends() {
  const { getFollowing, getFollowers, token } = useAuthStore();
  const navigate = useNavigate();
  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
  const [following, setFollowing] = useState<User[]>([]);
  const [followers, setFollowers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [startingChatId, setStartingChatId] = useState<number | null>(null);

  const handleStartChat = async (e: React.MouseEvent, targetUserId: number) => {
    e.preventDefault();
    e.stopPropagation();
    if (!token) return;
    try {
      setStartingChatId(targetUserId);
      const res = await fetch(`${apiUrl}/api/v1/chat/conversations/start/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ user_id: targetUserId }),
      });
      if (res.ok) {
        const data = await res.json();
        navigate(`/chat?conversationId=${data.conversation_id}`);
      } else {
        const errData = await res.json().catch(() => ({}));
        alert(errData.error || 'No se pudo iniciar la conversación');
      }
    } catch (error) {
      console.error('Error al iniciar conversación:', error);
      alert('Error de conexión al iniciar la conversación');
    } finally {
      setStartingChatId(null);
    }
  };

  useEffect(() => {
    const loadData = async () => {
      try {
        const [followingData, followersData] = await Promise.all([
          getFollowing(),
          getFollowers(),
        ]);
        setFollowing(Array.isArray(followingData) ? followingData : (followingData as any)?.results || []);
        setFollowers(Array.isArray(followersData) ? followersData : (followersData as any)?.results || []);
      } catch (error) {
        console.error('Error cargando amigos:', error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [getFollowing, getFollowers]);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <Spinner size="xl" />
      </div>
    );
  }

  const UserCard = ({ user }: { user: User }) => (
    <Card className="hover:shadow-lg transition-all duration-200 border border-gray-100 dark:border-gray-700">
      <div className="flex items-center justify-between gap-3">
        <Link to={`/users/${user.id}`} className="flex items-center space-x-4 flex-1 min-w-0">
          {user.avatar ? (
            <img
              src={user.avatar}
              alt={user.username}
              className="w-14 h-14 rounded-full object-cover border border-gray-200 dark:border-gray-600 flex-shrink-0"
            />
          ) : (
            <div className="w-14 h-14 rounded-full bg-teal-600 text-white flex items-center justify-center font-bold text-lg shadow-sm flex-shrink-0">
              {user.username?.[0]?.toUpperCase() || 'U'}
            </div>
          )}
          <div className="min-w-0">
            <h5 className="text-base font-bold text-gray-900 dark:text-white truncate">
              {user.first_name ? `${user.first_name} ${user.last_name || ''}` : user.username}
            </h5>
            <p className="text-xs text-gray-500 truncate">@{user.username}</p>
            {user.bio && (
              <p className="text-xs text-gray-600 dark:text-gray-300 line-clamp-1 mt-0.5">{user.bio.replace(/<[^>]*>/g, '')}</p>
            )}
          </div>
        </Link>
        <button
          onClick={(e) => handleStartChat(e, user.id)}
          disabled={startingChatId === user.id}
          className="px-3 py-1.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-all transform hover:scale-105 flex-shrink-0 disabled:opacity-50"
          title={`Enviar mensaje a @${user.username}`}
        >
          <span>💬</span>
          <span>{startingChatId === user.id ? 'Abriendo...' : 'Mensaje'}</span>
        </button>
      </div>
    </Card>
  );

  return (
    <div className="max-w-4xl mx-auto p-4">
      <h2 className="text-2xl font-bold mb-4">Mis Amigos</h2>
      
      <Tabs aria-label="Amigos tabs">
        <Tabs.Item active title={`Siguiendo (${following.length})`}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            {following.length === 0 ? (
              <p className="text-gray-600">No sigues a nadie aún</p>
            ) : (
              following.map(user => <UserCard key={user.id} user={user} />)
            )}
          </div>
        </Tabs.Item>
        <Tabs.Item title={`Seguidores (${followers.length})`}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            {followers.length === 0 ? (
              <p className="text-gray-600">Nadie te sigue aún</p>
            ) : (
              followers.map(user => <UserCard key={user.id} user={user} />)
            )}
          </div>
        </Tabs.Item>
      </Tabs>
    </div>
  );
}
