import React, { useState } from 'react';
import { Button, Modal, Label, TextInput, Spinner, Alert } from 'flowbite-react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../../store/auth';

export const AccountPrivacySection: React.FC = () => {
  const { token, logout, user } = useAuthStore();
  const navigate = useNavigate();
  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  // Exportación
  const [exportLoading, setExportLoading] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  // Eliminación modal
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deletePassword, setDeletePassword] = useState('');
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleExportData = async () => {
    if (!token) return;
    setExportLoading(true);
    setExportError(null);

    try {
      const res = await fetch(`${apiUrl}/api/v1/users/account/export/`, {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!res.ok) {
        throw new Error('No se pudo generar el archivo de exportación de datos.');
      }

      const blob = await res.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `mybookconnect_data_export_${user?.username || 'user'}.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err: any) {
      setExportError(err.message || 'Error al exportar datos personales.');
    } finally {
      setExportLoading(false);
    }
  };

  const handleDeleteAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;

    if (
      deleteConfirmText.trim().toUpperCase() !== 'ELIMINAR' &&
      deleteConfirmText.trim().toUpperCase() !== 'DELETE'
    ) {
      setDeleteError('Debes escribir exactamente la palabra "ELIMINAR" para confirmar.');
      return;
    }

    setDeleteLoading(true);
    setDeleteError(null);

    try {
      const res = await fetch(`${apiUrl}/api/v1/users/account/delete/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          password: deletePassword,
          confirmation: 'DELETE',
        }),
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || data.error || 'Error al procesar la baja de la cuenta.');
      }

      // Limpiar sesión y redirigir
      setDeleteModalOpen(false);
      logout();
      navigate('/');
    } catch (err: any) {
      setDeleteError(err.message || 'No se pudo eliminar la cuenta.');
    } finally {
      setDeleteLoading(false);
    }
  };

  return (
    <div className="space-y-6 bg-white dark:bg-slate-800 p-6 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm">
      <div>
        <h3 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <span>🛡️</span> Privacidad y Derechos RGPD
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Ejerce tus derechos de acceso, portabilidad de datos y derecho al olvido conforme al
          Reglamento General de Protección de Datos.
        </p>
      </div>

      {exportError && <Alert color="failure">{exportError}</Alert>}

      {/* Portabilidad de datos */}
      <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-700/50 border border-slate-100 dark:border-slate-700 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
            Descargar Portabilidad de Datos (JSON)
          </h4>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Recibe un archivo estructurado con tu biblioteca completa, reseñas redactadas, listas de
            lectura y preferencias.
          </p>
        </div>
        <Button
          size="sm"
          color="gray"
          onClick={handleExportData}
          disabled={exportLoading}
          className="whitespace-nowrap font-medium"
        >
          {exportLoading ? <Spinner size="sm" /> : '📥 Exportar mis datos'}
        </Button>
      </div>

      {/* Zona de peligro: Eliminación */}
      <div className="p-4 rounded-xl bg-red-50/70 dark:bg-red-950/20 border border-red-200 dark:border-red-900/50 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h4 className="text-sm font-bold text-red-800 dark:text-red-400">
            Zona de Peligro: Eliminación de Cuenta
          </h4>
          <p className="text-xs text-red-700 dark:text-red-300/80 mt-0.5 max-w-md">
            Al eliminar tu cuenta, tus datos personales serán anonimizados de forma irreversible,
            tus sesiones revocadas y tus relaciones sociales desvinculadas.
          </p>
        </div>
        <Button
          size="sm"
          color="failure"
          onClick={() => {
            setDeleteError(null);
            setDeletePassword('');
            setDeleteConfirmText('');
            setDeleteModalOpen(true);
          }}
          className="whitespace-nowrap font-semibold"
        >
          🗑️ Eliminar cuenta
        </Button>
      </div>

      {/* Modal de confirmación de eliminación */}
      <Modal
        show={deleteModalOpen}
        size="md"
        onClose={() => !deleteLoading && setDeleteModalOpen(false)}
        popup
      >
        <Modal.Header />
        <Modal.Body>
          <form onSubmit={handleDeleteAccount} className="space-y-4">
            <div className="text-center">
              <span className="text-4xl">⚠️</span>
              <h3 className="mb-2 text-lg font-bold text-slate-900 dark:text-white mt-2">
                ¿Eliminar cuenta definitivamente?
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Esta acción es <strong>permanente e irreversible</strong>. Tus reseñas literarias se
                conservarán de forma disociada, pero tu usuario, correo y relaciones sociales
                quedarán completamente anonimizados.
              </p>
            </div>

            {deleteError && <Alert color="failure">{deleteError}</Alert>}

            <div>
              <Label htmlFor="del-password" value="Introduce tu contraseña actual" />
              <TextInput
                id="del-password"
                type="password"
                required
                value={deletePassword}
                onChange={(e) => setDeletePassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>

            <div>
              <Label htmlFor="del-confirm" value="Escribe 'ELIMINAR' para confirmar" />
              <TextInput
                id="del-confirm"
                type="text"
                required
                value={deleteConfirmText}
                onChange={(e) => setDeleteConfirmText(e.target.value)}
                placeholder="ELIMINAR"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button
                color="gray"
                size="sm"
                disabled={deleteLoading}
                onClick={() => setDeleteModalOpen(false)}
              >
                Cancelar
              </Button>
              <Button
                color="failure"
                size="sm"
                type="submit"
                disabled={
                  deleteLoading ||
                  !deletePassword ||
                  deleteConfirmText.trim().toUpperCase() !== 'ELIMINAR'
                }
              >
                {deleteLoading ? <Spinner size="sm" /> : 'Confirmar baja definitiva'}
              </Button>
            </div>
          </form>
        </Modal.Body>
      </Modal>
    </div>
  );
};
