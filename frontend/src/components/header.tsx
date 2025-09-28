import React from "react";
import { Button, Navbar } from "flowbite-react";
import logoLibro from "../assets/logo-libro.png";
import { es } from "../locales/es";
import LoginButtons from "./login";



export function Header() {
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
        <LoginButtons />
        <Navbar.Toggle />
      </div>
      <Navbar.Collapse>
        <Navbar.Link href="#" active>
          Home
        </Navbar.Link>
        <Navbar.Link href="#">About</Navbar.Link>
        <Navbar.Link href="#">Services</Navbar.Link>
        <Navbar.Link href="#">Pricing</Navbar.Link>
        <Navbar.Link href="#">Contact</Navbar.Link>
      </Navbar.Collapse>
      </Navbar>
    </header>
  );
}
