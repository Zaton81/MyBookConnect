import { Link } from "react-router-dom";
import { BsGithub, BsInstagram, BsTwitterX, BsDiscord, BsBookHalf } from "react-icons/bs";
import logoLibro from "../assets/logo-libro.png";
import { openCookiePreferences } from "./CookieBanner";

export function FooterSection() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="mt-16 border-t border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/70 backdrop-blur-md text-slate-600 dark:text-slate-400">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-8 lg:gap-12">
          {/* Brand & Mission (Spans 2 columns on lg) */}
          <div className="lg:col-span-2 space-y-4">
            <Link to="/" className="inline-flex items-center gap-2 group">
              <img
                src={logoLibro}
                alt="MyBookConnect Logo"
                className="w-8 h-8 object-contain transition-transform group-hover:scale-105"
              />
              <span className="text-xl font-black tracking-tight text-slate-900 dark:text-white">
                MyBook<span className="text-teal-600 dark:text-teal-400">Connect</span>
              </span>
            </Link>
            <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed max-w-sm">
              Tu red social y biblioteca virtual para descubrir lecturas, catalogar tus libros favoritos y compartir opiniones con una comunidad apasionada por las historias.
            </p>

            {/* Amazon Affiliate Legal Notice */}
            <div className="p-3 rounded-xl bg-slate-100 dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-800 text-[11px] leading-relaxed text-slate-500 dark:text-slate-400 max-w-md">
              <p>
                <strong className="text-slate-700 dark:text-slate-300">Aviso de Afiliación:</strong> En calidad de Afiliado de Amazon, MyBookConnect podría obtener ingresos por las compras adscritas que cumplan los requisitos aplicables. Apoyas el proyecto sin ningún coste adicional para ti.
              </p>
            </div>
          </div>

          {/* Column 2: Platform Navigation */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-white mb-4">
              Explorar
            </h3>
            <ul className="space-y-2.5 text-sm">
              <li>
                <Link to="/home" className="hover:text-teal-600 dark:hover:text-teal-400 transition-colors">
                  Feed Social
                </Link>
              </li>
              <li>
                <Link to="/library" className="hover:text-teal-600 dark:hover:text-teal-400 transition-colors">
                  Mi Biblioteca
                </Link>
              </li>
              <li>
                <Link to="/books/add" className="hover:text-teal-600 dark:hover:text-teal-400 transition-colors">
                  Añadir Libro
                </Link>
              </li>
              <li>
                <Link to="/friends" className="hover:text-teal-600 dark:hover:text-teal-400 transition-colors">
                  Lectores & Amigos
                </Link>
              </li>
              <li>
                <Link to="/chat" className="hover:text-teal-600 dark:hover:text-teal-400 transition-colors">
                  Mensajería en vivo
                </Link>
              </li>
            </ul>
          </div>

          {/* Column 3: Legal & Privacy */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-white mb-4">
              Legal & Privacidad
            </h3>
            <ul className="space-y-2.5 text-sm">
              <li>
                <Link to="/privacy" className="hover:text-teal-600 dark:hover:text-teal-400 transition-colors">
                  Política de Privacidad
                </Link>
              </li>
              <li>
                <Link to="/terms" className="hover:text-teal-600 dark:hover:text-teal-400 transition-colors">
                  Términos y Condiciones
                </Link>
              </li>
              <li>
                <Link to="/cookies" className="hover:text-teal-600 dark:hover:text-teal-400 transition-colors">
                  Política de Cookies
                </Link>
              </li>
              <li>
                <button
                  type="button"
                  onClick={openCookiePreferences}
                  className="text-teal-600 dark:text-teal-400 hover:underline transition-colors flex items-center gap-1.5 cursor-pointer text-left"
                >
                  <span>Configurar cookies</span>
                  <span className="text-[10px]">⚙️</span>
                </button>
              </li>
            </ul>
          </div>

          {/* Column 4: Community & Social Networks */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-white mb-4">
              Comunidad
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-3">
              Únete a la conversación y sigue el desarrollo del proyecto:
            </p>
            <div className="flex flex-wrap gap-2">
              <a
                href="https://x.com"
                target="_blank"
                rel="noopener noreferrer"
                className="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-teal-50 dark:hover:bg-teal-950/60 hover:text-teal-600 dark:hover:text-teal-400 text-slate-600 dark:text-slate-300 flex items-center justify-center transition-colors"
                aria-label="X (Twitter)"
                title="X (Twitter)"
              >
                <BsTwitterX className="w-4 h-4" />
              </a>
              <a
                href="https://instagram.com"
                target="_blank"
                rel="noopener noreferrer"
                className="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-teal-50 dark:hover:bg-teal-950/60 hover:text-teal-600 dark:hover:text-teal-400 text-slate-600 dark:text-slate-300 flex items-center justify-center transition-colors"
                aria-label="Instagram"
                title="Instagram"
              >
                <BsInstagram className="w-4 h-4" />
              </a>
              <a
                href="https://github.com/Zaton81/MyBookConnect"
                target="_blank"
                rel="noopener noreferrer"
                className="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-teal-50 dark:hover:bg-teal-950/60 hover:text-teal-600 dark:hover:text-teal-400 text-slate-600 dark:text-slate-300 flex items-center justify-center transition-colors"
                aria-label="GitHub Repository"
                title="GitHub"
              >
                <BsGithub className="w-4 h-4" />
              </a>
              <a
                href="https://discord.com"
                target="_blank"
                rel="noopener noreferrer"
                className="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-teal-50 dark:hover:bg-teal-950/60 hover:text-teal-600 dark:hover:text-teal-400 text-slate-600 dark:text-slate-300 flex items-center justify-center transition-colors"
                aria-label="Discord Community"
                title="Discord"
              >
                <BsDiscord className="w-4 h-4" />
              </a>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-200/60 dark:border-slate-800">
              <span className="inline-flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
                <BsBookHalf className="text-teal-600 dark:text-teal-400" />
                <span>Club de Lectores Libres</span>
              </span>
            </div>
          </div>
        </div>

        {/* Bottom Bar: Copyright and status */}
        <div className="mt-12 pt-6 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500 dark:text-slate-400">
          <p>© {currentYear} MyBookConnect. Todos los derechos reservados.</p>
          <p className="flex items-center gap-1">
            <span>Hecho con</span>
            <span className="text-rose-500">❤️</span>
            <span>para amantes de los libros</span>
          </p>
        </div>
      </div>
    </footer>
  );
}
