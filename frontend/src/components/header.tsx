import React from "react";
import { Button, Navbar } from "flowbite-react";
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
      <Navbar.Brand href="/">
        <img
          src={logoLibro}
          className="mr-3 h-6 sm:h-9"
          alt={es.logo_simple.imgAlt}
        />
        <span className="self-center whitespace-nowrap text-xl font-semibold dark:text-white">
          My Book Connect
        </span>
      </Navbar.Brand>
      <div className="flex md:order-2">
        <Button color="light" onClick={logout}>
          Cerrar sesión
        </Button>
        <Navbar.Toggle />
      </div>
      <Navbar.Collapse>
        <Navbar.Link href="/" active>
          Mi Biblioteca
        </Navbar.Link>
        <Navbar.Link href="/books/add">
          Añadir libro
        </Navbar.Link>
        <Navbar.Link href="/profile">
          Mi Perfil
        </Navbar.Link>
      </Navbar.Collapse>
      </Navbar>
    </header>
  );
}
