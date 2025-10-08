import React from 'react';
import { EditProfile as EditProfileForm } from '../components/EditProfile';

export const EditProfile = () => {
  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-2xl mx-auto">
        <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900 mb-6">Editar Perfil</h2>
        <EditProfileForm />
      </div>
    </div>
  );
};