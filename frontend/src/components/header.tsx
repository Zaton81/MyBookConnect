import React from "react";
import { Button, Navbar } from "flowbite-react";
import { Link, NavLink } from "react-router-dom";
import logoLibro from "../assets/logo-libro.png";
import { es } from "../locales/es";
import { useAuthStore } from "../store/auth";

export function Header() {
  const { isAuthenticated, logout } = useAuthStore();
  
  if (!isAuthenticated) return null;
  return (
    // Fixed header: usamos 'fixed top-0 left-0 right-0 z-50' y sombra
    <header className="fixed top-0 left-0 right-0 z-50 shadow">
      <Navbar fluid rounded className="bg-teal-500">
      <div className="flex items-center">
        <Link to="/" className="flex items-center">
          <img
            src={logoLibro}
            className="mr-3 h-6 sm:h-9"
            alt={es.logo_simple.imgAlt}
            loading="lazy"
          />
          <span className="self-center whitespace-nowrap text-xl font-semibold dark:text-white">
            My Book Connect
          </span>
        </Link>
      </div>
      <div className="flex md:order-2">
        <Button color="light" onClick={logout}>
          Cerrar sesión
        </Button>
        <Navbar.Toggle />
      </div>
      <Navbar.Collapse>
        <NavLink to="/library" className={({ isActive }) => `block py-2 px-3 md:p-0 ${isActive ? 'text-white font-semibold' : 'text-white/90 hover:text-white'}`} end>
          Mi Biblioteca
        </NavLink>
        <NavLink to="/books/add" className={({ isActive }) => `block py-2 px-3 md:p-0 ${isActive ? 'text-white font-semibold' : 'text-white/90 hover:text-white'}`}>
          Añadir libro
        </NavLink>
        <NavLink to="/friends" className={({ isActive }) => `block py-2 px-3 md:p-0 ${isActive ? 'text-white font-semibold' : 'text-white/90 hover:text-white'}`}>
          Amigos
        </NavLink>
        <NavLink to="/profile" className={({ isActive }) => `block py-2 px-3 md:p-0 ${isActive ? 'text-white font-semibold' : 'text-white/90 hover:text-white'}`}>
          Mi Perfil
        </NavLink>
      </Navbar.Collapse>
      </Navbar>
    </header>
  );
}
