import React, { useState } from "react";
import { Button, Navbar } from "flowbite-react";
import { Link, NavLink } from "react-router-dom";
import logoLibro from "../assets/logo-libro.png";
import { es } from "../locales/es";
import { useAuthStore } from "../store/auth";
import { AIAssistantModal } from "./AIAssistantModal";

export function Header() {
  const { isAuthenticated, logout } = useAuthStore();
  const [isAiModalOpen, setIsAiModalOpen] = useState(false);
  
  if (!isAuthenticated) return null;

  const navLinkClasses = ({ isActive }: { isActive: boolean }) =>
    `px-3.5 py-1.5 rounded-xl text-sm font-medium transition-all ${
      isActive
        ? "bg-white/20 text-white font-bold shadow-sm backdrop-blur-sm"
        : "text-teal-100 hover:text-white hover:bg-white/10"
    }`;

  return (
    <>
      <header className="sticky top-0 z-50 backdrop-blur-md bg-teal-700/95 dark:bg-slate-900/95 border-b border-teal-600/30 shadow-md">
        <Navbar fluid rounded className="bg-transparent max-w-7xl mx-auto py-2.5 px-4 sm:px-6">
          <div className="flex items-center">
            <Link to="/home" className="flex items-center group">
              <div className="relative p-1 mr-2 rounded-xl bg-white/10 group-hover:bg-white/20 transition-colors">
                <img
                  src={logoLibro}
                  className="h-7 sm:h-8 drop-shadow"
                  alt={es.logo_simple.imgAlt}
                  loading="lazy"
                />
              </div>
              <span className="self-center whitespace-nowrap text-xl font-extrabold text-white tracking-tight">
                MyBook<span className="text-teal-200">Connect</span>
              </span>
            </Link>
          </div>

          <div className="flex items-center gap-2.5 md:order-2">
            <button
              onClick={() => setIsAiModalOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-amber-400 to-orange-400 hover:from-amber-300 hover:to-orange-300 text-slate-900 font-bold text-xs shadow-md shadow-amber-500/20 transition-all transform hover:scale-105"
              title="Abrir Asistente BookAI"
            >
              <span>✨</span>
              <span className="hidden sm:inline">BookAI</span>
            </button>
            <Button
              size="xs"
              color="light"
              onClick={logout}
              className="rounded-xl font-medium border-white/20 hover:bg-white/10"
            >
              Salir
            </Button>
            <Navbar.Toggle className="text-white hover:bg-white/10 focus:ring-teal-400" />
          </div>

          <Navbar.Collapse className="mt-2 md:mt-0">
            <NavLink to="/home" className={navLinkClasses} end>
              Inicio
            </NavLink>
            <NavLink to="/library" className={navLinkClasses}>
              Mi Biblioteca
            </NavLink>
            <NavLink to="/books/add" className={navLinkClasses}>
              + Añadir Libro
            </NavLink>
            <NavLink to="/chat" className={navLinkClasses}>
              Mensajes
            </NavLink>
            <NavLink to="/friends" className={navLinkClasses}>
              Amigos
            </NavLink>
            <NavLink to="/profile" className={navLinkClasses}>
              Mi Perfil
            </NavLink>
          </Navbar.Collapse>
        </Navbar>
      </header>

      {/* Modal global del asistente de IA */}
      <AIAssistantModal
        isOpen={isAiModalOpen}
        onClose={() => setIsAiModalOpen(false)}
      />
    </>
  );
}
