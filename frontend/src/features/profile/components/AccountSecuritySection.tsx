import React, { useState } from 'react';
import { Button, Label, TextInput, Spinner, Alert } from 'flowbite-react';
import { useAuthStore } from '../../../store/auth';

export const AccountSecuritySection: React.FC = () => {
  const { token, user } = useAuthStore();
  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  // Estados para cambio de contraseña
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [pwdLoading, setPwdLoading] = useState(false);
  const [pwdSuccess, setPwdSuccess] = useState<string | null>(null);
  const [pwdError, setPwdError] = useState<string | null>(null);

  // Estados para cambio de email
  const [newEmail, setNewEmail] = useState('');
  const [emailPassword, setEmailPassword] = useState('');
  const [emailLoading, setEmailLoading] = useState(false);
  const [emailSuccess, setEmailSuccess] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwdSuccess(null);
    setPwdError(null);

    if (newPassword.length < 8) {
      setPwdError('La nueva contraseña debe tener al menos 8 caracteres.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setPwdError('Las contraseñas no coinciden.');
      return;
    }

    setPwdLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/users/password/change/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || data.error || 'Error al cambiar la contraseña.');
      }

      setPwdSuccess('¡Contraseña cambiada con éxito!');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      setPwdError(err.message || 'No se pudo actualizar la contraseña.');
    } finally {
      setPwdLoading(false);
    }
  };

  const handleEmailChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setEmailSuccess(null);
    setEmailError(null);

    if (!newEmail.includes('@')) {
      setEmailError('Introduce un correo electrónico válido.');
      return;
    }

    setEmailLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/users/email/change/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          new_email: newEmail,
          password: emailPassword,
        }),
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || data.error || 'Error al cambiar el correo.');
      }

      setEmailSuccess(data.detail || 'Correo actualizado exitosamente.');
      setNewEmail('');
      setEmailPassword('');
    } catch (err: any) {
      setEmailError(err.message || 'No se pudo actualizar el correo electrónico.');
    } finally {
      setEmailLoading(false);
    }
  };

  return (
    <div className="space-y-8 bg-white dark:bg-slate-800 p-6 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm">
      <div>
        <h3 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <span>🔒</span> Seguridad y Credenciales
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Actualiza tu contraseña periódicamente o modifica tu dirección de correo electrónico
          vinculada.
        </p>
      </div>

      {/* Formulario Cambio de Contraseña */}
      <form
        onSubmit={handlePasswordChange}
        className="space-y-4 pt-2 border-t border-slate-100 dark:border-slate-700"
      >
        <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
          Modificar Contraseña
        </h4>

        {pwdSuccess && <Alert color="success">{pwdSuccess}</Alert>}
        {pwdError && <Alert color="failure">{pwdError}</Alert>}

        <div>
          <Label htmlFor="curr-password" value="Contraseña actual" />
          <TextInput
            id="curr-password"
            type="password"
            required
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            placeholder="••••••••"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <Label htmlFor="new-password" value="Nueva contraseña" />
            <TextInput
              id="new-password"
              type="password"
              required
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Mínimo 8 caracteres"
            />
          </div>
          <div>
            <Label htmlFor="conf-password" value="Confirmar contraseña" />
            <TextInput
              id="conf-password"
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Repite la nueva contraseña"
            />
          </div>
        </div>

        <Button
          type="submit"
          size="sm"
          color="dark"
          disabled={pwdLoading || !currentPassword || !newPassword || !confirmPassword}
          className="mt-2"
        >
          {pwdLoading ? <Spinner size="sm" /> : 'Actualizar contraseña'}
        </Button>
      </form>

      {/* Formulario Cambio de Correo Electrónico */}
      <form
        onSubmit={handleEmailChange}
        className="space-y-4 pt-6 border-t border-slate-100 dark:border-slate-700"
      >
        <div>
          <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
            Cambiar Correo Electrónico
          </h4>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Email actual:{' '}
            <span className="font-mono text-slate-700 dark:text-slate-300">{user?.email}</span>
          </p>
        </div>

        {emailSuccess && <Alert color="success">{emailSuccess}</Alert>}
        {emailError && <Alert color="failure">{emailError}</Alert>}

        <div>
          <Label htmlFor="new-email" value="Nuevo correo electrónico" />
          <TextInput
            id="new-email"
            type="email"
            required
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
            placeholder="nuevo_correo@ejemplo.com"
          />
        </div>

        <div>
          <Label htmlFor="email-password" value="Contraseña actual para autorizar el cambio" />
          <TextInput
            id="email-password"
            type="password"
            required
            value={emailPassword}
            onChange={(e) => setEmailPassword(e.target.value)}
            placeholder="••••••••"
          />
        </div>

        <Button
          type="submit"
          size="sm"
          color="dark"
          disabled={emailLoading || !newEmail || !emailPassword}
          className="mt-2"
        >
          {emailLoading ? <Spinner size="sm" /> : 'Guardar nuevo correo'}
        </Button>
      </form>
    </div>
  );
};
