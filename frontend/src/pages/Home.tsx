import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/auth';

export const Home = () => {
  const user = useAuthStore(state => state.user);
  const navigate = useNavigate();

  useEffect(() => {
    if (!user) {
      navigate('/');
    }
  }, [user, navigate]);

  if (!user) return null;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
        <div className="text-center">
          <h1 className="text-3xl font-extrabold text-gray-900 sm:text-4xl">
            ¡Bienvenido {user.username}!
          </h1>
          <p className="mt-3 max-w-2xl mx-auto text-xl text-gray-500 sm:mt-4">
            Tu muro de libros y recomendaciones
          </p>
        </div>

        {/* Aquí irá el contenido principal del muro */}
        <div className="mt-10">
          <div className="text-center text-gray-600">
            Próximamente: Tu colección de libros y recomendaciones
          </div>
        </div>
      </div>
    </div>
  );
};