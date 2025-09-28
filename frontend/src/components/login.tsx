import React, { useState } from 'react';
import LoginModal from './LoginModal';
import RegisterModal from './RegisterModal';

export default function LoginButtons() {
  const [showLogin, setShowLogin] = useState(false);
  const [showRegister, setShowRegister] = useState(false);

  return (
    <div className="flex gap-3">
      <button
        onClick={() => setShowLogin(true)}
        className="rounded bg-blue-600 px-4 py-2 text-white"
      >
        Iniciar sesión
      </button>
      <button
        onClick={() => setShowRegister(true)}
        className="rounded border px-4 py-2"
      >
        Registrarse
      </button>

      <LoginModal open={showLogin} onClose={() => setShowLogin(false)} />
      <RegisterModal open={showRegister} onClose={() => setShowRegister(false)} />
    </div>
  );
}
