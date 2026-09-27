import React, { useState } from 'react';
import { EditProfileForm } from '../components/EditProfileForm';
import { AccountSecuritySection } from '../components/AccountSecuritySection';
import { AccountPrivacySection } from '../components/AccountPrivacySection';

export const EditProfile: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'profile' | 'security' | 'privacy'>('profile');

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto space-y-6">
        <div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white">
            Configuración de Cuenta
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Administra tus datos personales, credenciales de acceso y preferencias de privacidad.
          </p>
        </div>

        {/* Selector de Pestañas */}
        <div className="flex border-b border-slate-200 dark:border-slate-700 space-x-2">
          <button
            onClick={() => setActiveTab('profile')}
            className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-colors ${
              activeTab === 'profile'
                ? 'border-teal-600 text-teal-600 dark:text-teal-400'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            👤 Perfil
          </button>
          <button
            onClick={() => setActiveTab('security')}
            className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-colors ${
              activeTab === 'security'
                ? 'border-teal-600 text-teal-600 dark:text-teal-400'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            🔒 Seguridad
          </button>
          <button
            onClick={() => setActiveTab('privacy')}
            className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-colors ${
              activeTab === 'privacy'
                ? 'border-teal-600 text-teal-600 dark:text-teal-400'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            🛡️ Privacidad & RGPD
          </button>
        </div>

        {/* Contenido de la Pestaña Activa */}
        <div className="pt-2">
          {activeTab === 'profile' && <EditProfileForm />}
          {activeTab === 'security' && <AccountSecuritySection />}
          {activeTab === 'privacy' && <AccountPrivacySection />}
        </div>
      </div>
    </div>
  );
};

export default EditProfile;
