import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { OnboardingModal } from '../components/OnboardingModal';
import { Button } from 'flowbite-react';

export function OnboardingPage() {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(true);

  return (
    <div className="max-w-3xl mx-auto py-12 px-4 text-center">
      <nav
        aria-label="Navegación secundaria"
        className="text-xs text-slate-500 mb-6 flex items-center justify-center gap-2"
      >
        <Link to="/home" className="hover:text-teal-600">
          Inicio
        </Link>
        <span>/</span>
        <span className="text-slate-800 dark:text-slate-200 font-medium">
          Personalización Inicial
        </span>
      </nav>

      <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white mb-2">
        Configura tus Preferencias Lectoras
      </h1>
      <p className="text-sm text-slate-600 dark:text-slate-400 mb-6">
        Selecciona tus géneros favoritos y tus primeras lecturas para entrenar tus recomendaciones.
      </p>

      <Button color="teal" onClick={() => setIsOpen(true)} className="mx-auto">
        Abrir Asistente de Bienvenida
      </Button>

      <OnboardingModal
        isOpen={isOpen}
        onClose={() => {
          setIsOpen(false);
          navigate('/home');
        }}
        onComplete={() => {
          setIsOpen(false);
          navigate('/home');
        }}
      />
    </div>
  );
}

export default OnboardingPage;
