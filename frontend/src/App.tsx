import React from 'react';
import { Button } from 'flowbite-react'
import {Header} from "./components/header"
import {Logo} from "./components/logo"
import {FooterSection} from "./components/footer"
import AuthBox from './components/AuthBox'

export default function App() {
  return (
    // Añadimos pt-16 para dejar espacio al header fijo (ajusta si cambias la altura)
    <div className="min-h-screen pt-16 p-6 bg-teal-800">
      <Header />
      <main>
        <div className="mx-auto grid max-w-6xl grid-cols-1 gap-6 md:grid-cols-2">
          <div className="flex flex-col items-start justify-center px-6">
            <Logo />
          </div>
          <div className="flex items-center justify-center px-6">
            <AuthBox />
          </div>
        </div>
      </main>
      <FooterSection />
    </div>
  )
}