import React from 'react';
import { Button } from 'flowbite-react'
import {Header} from "./components/header"

export default function App() {
  return (
    <div className="min-h-screen p-6">
      <Header />
      <header className="mb-6">
        <h1 className="text-2xl font-semibold">My Book Connect</h1>
        <p className="text-gray-600">MVP con React + Tailwind + Flowbite</p>
      </header>
      <main>
        <div className="flex gap-3">
          <Button color="blue">Guardar cambios 3</Button>
          <Button color="gray">Cancelar</Button>
        </div>
      </main>
    </div>
  )
}