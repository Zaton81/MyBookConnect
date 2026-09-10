import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, Tabs, Spinner } from 'flowbite-react';
import { useAuthStore } from '../store/auth';
import { User } from '../types/auth';

export function Friends() {
  const { getFollowing, getFollowers } = useAuthStore();
  const [following, setFollowing] = useState<User[]>([]);
  const [followers, setFollowers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);

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
    <Link to={`/users/${user.id}`}>
      <Card className="hover:shadow-lg transition-shadow duration-200">
        <div className="flex items-center space-x-4">
          {user.avatar && (
            <img
              src={user.avatar}
              alt={user.username}
              className="w-16 h-16 rounded-full object-cover"
            />
          )}
          <div>
            <h5 className="text-lg font-bold">
              {user.first_name ? `${user.first_name} ${user.last_name || ''}` : user.username}
            </h5>
            <p className="text-sm text-gray-500">@{user.username}</p>
            {user.bio && (
              <p className="text-sm text-gray-600 line-clamp-2 mt-1">{user.bio.replace(/<[^>]*>/g, '')}</p>
            )}
          </div>
        </div>
      </Card>
    </Link>
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
