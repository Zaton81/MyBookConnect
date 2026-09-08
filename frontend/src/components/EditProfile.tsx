import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Label, TextInput, Button, Select, Checkbox } from 'flowbite-react';
import ReactQuill from 'react-quill';
import 'react-quill/dist/quill.snow.css';
import { useAuthStore } from '../store/auth';

export function EditProfile() {
  const { user, updateProfile } = useAuthStore();
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    email: user?.email || '',
    birth_date: user?.birth_date || '',
    location: user?.location || '',
    privacy_level: user?.privacy_level || 'public',
    bio: user?.bio || '',
    show_email: user?.show_email ?? false,
    show_birth_date: user?.show_birth_date ?? false,
    show_location: user?.show_location ?? false,
    show_bio: user?.show_bio ?? false,
  });
  const [avatar, setAvatar] = useState<File | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    
    setIsSubmitting(true);
    try {
      const data = new FormData();
      if (avatar) {
        data.append('avatar', avatar);
      }
      Object.entries(formData).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          // DRF acepta 'true'/'false' para booleanos; aseguramos string
          const v = typeof value === 'boolean' ? String(value) : (value as string);
          data.append(key, v);
        }
      });
      
      await updateProfile(data);
      navigate('/profile');
    } catch (error) {
      console.error('Error actualizando perfil:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setAvatar(e.target.files[0]);
    }
  };

  if (!user) {
    return null;
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-md mx-auto">
      <div className="mb-4">
        <Label htmlFor="avatar" value="Foto de perfil" />
        <input
          id="avatar"
          type="file"
          onChange={handleFileChange}
          accept="image/*"
          aria-label="Foto de perfil"
          className="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none"
        />
      </div>

      <div className="mb-4">
        <Label htmlFor="first_name" value="Nombre" />
        <TextInput
          id="first_name"
          type="text"
          value={formData.first_name}
          onChange={(e) => setFormData({...formData, first_name: e.target.value})}
        />
      </div>
      <div className="mb-4">
        <Label htmlFor="last_name" value="Apellidos" />
        <TextInput
          id="last_name"
          type="text"
          value={formData.last_name}
          onChange={(e) => setFormData({...formData, last_name: e.target.value})}
        />
      </div>
      <div className="mb-4">
        <Label htmlFor="email" value="Email" />
        <TextInput
          id="email"
          type="email"
          value={formData.email}
          onChange={(e) => setFormData({...formData, email: e.target.value})}
        />
      </div>
      <div className="mb-4">
        <Label htmlFor="birth_date" value="Fecha de nacimiento" />
        <TextInput
          id="birth_date"
          type="date"
          value={formData.birth_date}
          onChange={(e) => setFormData({...formData, birth_date: e.target.value})}
        />
      </div>

      <div className="mb-4">
        <Label htmlFor="location" value="Ubicación" />
        <TextInput
          id="location"
          type="text"
          value={formData.location}
          onChange={(e) => setFormData({...formData, location: e.target.value})}
        />
      </div>

      <div className="mb-4">
        <Label htmlFor="privacy_level" value="Nivel de privacidad" />
        <Select
          id="privacy_level"
          value={formData.privacy_level}
          onChange={(e) => setFormData({...formData, privacy_level: e.target.value as 'public' | 'friends' | 'private'})}
        >
          <option value="public">Público</option>
          <option value="friends">Solo amigos</option>
          <option value="private">Privado</option>
        </Select>
      </div>

      <div className="mb-4 border rounded-md p-4">
        <p className="font-medium mb-2">Visibilidad de campos</p>
        <div className="flex flex-col gap-2">
          <label className="flex items-center gap-2">
            <Checkbox
              checked={formData.show_email}
              onChange={(e) => setFormData({ ...formData, show_email: e.target.checked })}
            />
            <span>Mostrar email</span>
          </label>
          <label className="flex items-center gap-2">
            <Checkbox
              checked={formData.show_birth_date}
              onChange={(e) => setFormData({ ...formData, show_birth_date: e.target.checked })}
            />
            <span>Mostrar fecha de nacimiento</span>
          </label>
          <label className="flex items-center gap-2">
            <Checkbox
              checked={formData.show_location}
              onChange={(e) => setFormData({ ...formData, show_location: e.target.checked })}
            />
            <span>Mostrar ubicación</span>
          </label>
          <label className="flex items-center gap-2">
            <Checkbox
              checked={formData.show_bio}
              onChange={(e) => setFormData({ ...formData, show_bio: e.target.checked })}
            />
            <span>Mostrar biografía</span>
          </label>
        </div>
      </div>
      <div className="mb-4">
        <Label htmlFor="bio" value="Biografía enriquecida" />
        <ReactQuill
          id="bio"
          value={formData.bio}
          onChange={(value: string) => setFormData({...formData, bio: value})}
          theme="snow"
        />
      </div>

      <div className="flex justify-between">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Guardando...' : 'Guardar cambios'}
        </Button>
        <Button color="light" onClick={() => navigate('/profile')}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}