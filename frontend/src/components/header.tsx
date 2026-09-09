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

  return (
    <>
      <header className="fixed top-0 left-0 right-0 z-50 shadow">
        <Navbar fluid rounded className="bg-teal-600 dark:bg-teal-800">
          <div className="flex items-center">
            <Link to="/home" className="flex items-center">
              <img
                src={logoLibro}
                className="mr-3 h-6 sm:h-9"
                alt={es.logo_simple.imgAlt}
                loading="lazy"
              />
              <span className="self-center whitespace-nowrap text-xl font-bold text-white tracking-tight">
                My Book Connect
              </span>
            </Link>
          </div>

          <div className="flex items-center gap-2 md:order-2">
            <button
              onClick={() => setIsAiModalOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-amber-400 to-orange-400 hover:from-amber-300 hover:to-orange-300 text-slate-900 font-bold text-xs shadow-md transition-all transform hover:scale-105"
            >
              <span>✨</span>
              <span>BookAI</span>
            </button>
            <Button size="xs" color="light" onClick={logout} className="rounded-xl">
              Cerrar sesión
            </Button>
            <Navbar.Toggle />
          </div>

          <Navbar.Collapse>
            <NavLink
              to="/home"
              className={({ isActive }) =>
                `block py-2 px-3 md:p-0 transition-colors ${
                  isActive ? "text-white font-bold underline underline-offset-4" : "text-white/80 hover:text-white"
                }`
              }
              end
            >
              Inicio
            </NavLink>
            <NavLink
              to="/library"
              className={({ isActive }) =>
                `block py-2 px-3 md:p-0 transition-colors ${
                  isActive ? "text-white font-bold underline underline-offset-4" : "text-white/80 hover:text-white"
                }`
              }
            >
              Mi Biblioteca
            </NavLink>
            <NavLink
              to="/books/add"
              className={({ isActive }) =>
                `block py-2 px-3 md:p-0 transition-colors ${
                  isActive ? "text-white font-bold underline underline-offset-4" : "text-white/80 hover:text-white"
                }`
              }
            >
              Añadir libro
            </NavLink>
            <NavLink
              to="/chat"
              className={({ isActive }) =>
                `block py-2 px-3 md:p-0 transition-colors ${
                  isActive ? "text-white font-bold underline underline-offset-4" : "text-white/80 hover:text-white"
                }`
              }
            >
              Mensajes
            </NavLink>
            <NavLink
              to="/friends"
              className={({ isActive }) =>
                `block py-2 px-3 md:p-0 transition-colors ${
                  isActive ? "text-white font-bold underline underline-offset-4" : "text-white/80 hover:text-white"
                }`
              }
            >
              Amigos
            </NavLink>
            <NavLink
              to="/profile"
              className={({ isActive }) =>
                `block py-2 px-3 md:p-0 transition-colors ${
                  isActive ? "text-white font-bold underline underline-offset-4" : "text-white/80 hover:text-white"
                }`
              }
            >
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
