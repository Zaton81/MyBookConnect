import React from 'react';
import { Button } from 'flowbite-react'
import {Header} from "./components/header"
import {Logo} from "./components/logo"
import {FooterSection} from "./components/footer"

export default function App() {
  return (
    <div className="min-h-screen p-6 bg-teal-800">
      <Header />
      <main>
        <div className="flex justify-center">
          <Logo />

        </div>
      </main>
      <FooterSection />
    </div>
  )
}