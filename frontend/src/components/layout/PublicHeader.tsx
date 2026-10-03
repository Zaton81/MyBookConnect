import { useState } from 'react';
import { Link } from 'react-router-dom';
import logoLibro from '../../assets/logo-libro.png';

export interface PublicHeaderProps {
  onOpenAuth: (mode: 'login' | 'register') => void;
}

export function PublicHeader({ onOpenAuth }: PublicHeaderProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const scrollToSection = (id: string) => {
    setMobileMenuOpen(false);
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <header className="sticky top-0 z-40 backdrop-blur-md bg-teal-800/95 dark:bg-slate-950/90 border-b border-teal-600/30 dark:border-slate-800/80 shadow-sm transition-all">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="p-1 rounded-xl bg-white/10 group-hover:bg-white/20 transition-colors shadow-sm">
              <img
                src={logoLibro}
                alt="MyBookConnect"
                className="h-7 sm:h-8 drop-shadow object-contain"
              />
            </div>
            <span className="text-xl font-extrabold text-white tracking-tight">
              MyBook<span className="text-teal-300">Social</span>
            </span>
          </Link>

          {/* Navegación Desktop */}
          <nav className="hidden md:flex items-center gap-6">
            <button
              onClick={() => scrollToSection('descubrimiento')}
              className="text-sm font-medium text-teal-100 hover:text-white transition-colors cursor-pointer"
            >
              Descubrir Libros
            </button>
            <button
              onClick={() => scrollToSection('caracteristicas')}
              className="text-sm font-medium text-teal-100 hover:text-white transition-colors cursor-pointer"
            >
              Por qué elegirnos
            </button>
            <Link
              to="/search"
              className="text-sm font-medium text-teal-100 hover:text-white transition-colors flex items-center gap-1"
            >
              <span>🔍</span>
              <span>Buscar</span>
            </Link>
            <Link
              to="/faqs"
              className="text-sm font-medium text-teal-100 hover:text-white transition-colors"
            >
              FAQs
            </Link>
            <Link
              to="/terms"
              className="text-sm font-medium text-teal-100 hover:text-white transition-colors"
            >
              Legal & Privacidad
            </Link>
          </nav>

          {/* Botones de Auth en Header */}
          <div className="hidden sm:flex items-center gap-3">
            <button
              onClick={() => onOpenAuth('login')}
              className="px-4 py-2 text-sm font-bold text-white hover:text-teal-200 hover:bg-white/10 rounded-xl transition-all cursor-pointer"
            >
              Iniciar sesión
            </button>
            <button
              onClick={() => onOpenAuth('register')}
              className="px-4 py-2 text-sm font-bold text-slate-950 bg-gradient-to-r from-teal-300 via-emerald-300 to-teal-200 hover:from-teal-200 hover:to-emerald-200 rounded-xl shadow-md shadow-teal-900/20 hover:shadow-teal-900/40 transition-all transform hover:-translate-y-0.5 cursor-pointer"
            >
              Crear cuenta gratis
            </button>
          </div>

          {/* Botón hamburguesa móvil */}
          <div className="flex sm:hidden items-center gap-2">
            <button
              onClick={() => onOpenAuth('login')}
              className="px-2.5 py-1.5 text-xs font-bold text-white bg-white/15 rounded-lg"
            >
              Entrar
            </button>
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-teal-100 hover:text-white hover:bg-white/10"
              aria-label="Abrir menú"
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                {mobileMenuOpen ? (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                ) : (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                )}
              </svg>
            </button>
          </div>
        </div>

        {/* Menú desplegable móvil */}
        {mobileMenuOpen && (
          <div className="sm:hidden py-4 border-t border-teal-600/30 space-y-3">
            <button
              onClick={() => scrollToSection('descubrimiento')}
              className="block w-full text-left px-3 py-2 text-sm font-medium text-teal-100 hover:text-white hover:bg-white/10 rounded-lg"
            >
              Descubrir Libros
            </button>
            <button
              onClick={() => scrollToSection('caracteristicas')}
              className="block w-full text-left px-3 py-2 text-sm font-medium text-teal-100 hover:text-white hover:bg-white/10 rounded-lg"
            >
              Por qué elegirnos
            </button>
            <Link
              to="/search"
              onClick={() => setMobileMenuOpen(false)}
              className="block px-3 py-2 text-sm font-medium text-teal-100 hover:text-white hover:bg-white/10 rounded-lg flex items-center gap-2"
            >
              <span>🔍</span>
              <span>Búsqueda Global</span>
            </Link>
            <Link
              to="/faqs"
              className="block px-3 py-2 text-sm font-medium text-teal-100 hover:text-white hover:bg-white/10 rounded-lg"
            >
              Preguntas Frecuentes (FAQs)
            </Link>
            <Link
              to="/terms"
              className="block px-3 py-2 text-sm font-medium text-teal-100 hover:text-white hover:bg-white/10 rounded-lg"
            >
              Legal & Privacidad
            </Link>
            <div className="pt-2 flex flex-col gap-2">
              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  onOpenAuth('register');
                }}
                className="w-full py-2.5 text-center text-sm font-bold text-slate-950 bg-gradient-to-r from-teal-300 to-emerald-300 rounded-xl"
              >
                Crear cuenta gratis
              </button>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}

export default PublicHeader;
