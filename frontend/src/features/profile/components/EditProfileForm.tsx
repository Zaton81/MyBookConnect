import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Label, TextInput, Button, Select, Checkbox } from 'flowbite-react';
import { BioEditor } from '../../../components/ui';
import { useAuthStore } from '../../../store/auth';
import { editProfileSchema, EditProfileFormData } from '../schemas/profileSchemas';

export function EditProfileForm() {
  const { user, updateProfile } = useAuthStore();
  const navigate = useNavigate();
  const [avatar, setAvatar] = useState<File | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    control,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<EditProfileFormData>({
    resolver: zodResolver(editProfileSchema),
    defaultValues: {
      first_name: user?.first_name || '',
      last_name: user?.last_name || '',
      email: user?.email || '',
      birth_date: user?.birth_date || '',
      location: user?.location || '',
      privacy_level: (user?.privacy_level as 'public' | 'friends' | 'private') || 'public',
      bio: user?.bio || '',
      show_email: user?.show_email ?? false,
      show_birth_date: user?.show_birth_date ?? false,
      show_location: user?.show_location ?? false,
      show_bio: user?.show_bio ?? false,
    },
  });

  const bioContent = watch('bio') || '';

  const onSubmit = async (formData: EditProfileFormData) => {
    if (!user) return;
    setServerError(null);

    try {
      const data = new FormData();
      if (avatar) {
        data.append('avatar', avatar);
      }
      Object.entries(formData).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          const v = typeof value === 'boolean' ? String(value) : String(value);
          data.append(key, v);
        }
      });

      await updateProfile(data);
      navigate('/profile');
    } catch (error: any) {
      setServerError(error?.message || 'Error al actualizar el perfil');
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
    <form onSubmit={handleSubmit(onSubmit)} className="max-w-md mx-auto" noValidate>
      <div className="mb-4">
        <Label htmlFor="avatar" value="Foto de perfil" />
        <input
          id="avatar"
          type="file"
          onChange={handleFileChange}
          accept="image/*"
          aria-label="Foto de perfil"
          className="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200"
        />
      </div>

      <div className="mb-4">
        <Label htmlFor="first_name" value="Nombre" />
        <TextInput
          id="first_name"
          type="text"
          {...register('first_name')}
          color={errors.first_name ? 'failure' : undefined}
          helperText={errors.first_name?.message}
        />
      </div>

      <div className="mb-4">
        <Label htmlFor="last_name" value="Apellidos" />
        <TextInput
          id="last_name"
          type="text"
          {...register('last_name')}
          color={errors.last_name ? 'failure' : undefined}
          helperText={errors.last_name?.message}
        />
      </div>

      <div className="mb-4">
        <Label htmlFor="email" value="Email" />
        <TextInput
          id="email"
          type="email"
          {...register('email')}
          color={errors.email ? 'failure' : undefined}
          helperText={errors.email?.message}
        />
      </div>

      <div className="mb-4">
        <Label htmlFor="birth_date" value="Fecha de nacimiento" />
        <TextInput
          id="birth_date"
          type="date"
          {...register('birth_date')}
          color={errors.birth_date ? 'failure' : undefined}
          helperText={errors.birth_date?.message}
        />
      </div>

      <div className="mb-4">
        <Label htmlFor="location" value="Ubicación" />
        <TextInput
          id="location"
          type="text"
          {...register('location')}
          color={errors.location ? 'failure' : undefined}
          helperText={errors.location?.message}
        />
      </div>

      <div className="mb-4">
        <Label htmlFor="privacy_level" value="Nivel de privacidad" />
        <Select
          id="privacy_level"
          {...register('privacy_level')}
        >
          <option value="public">Público</option>
          <option value="friends">Solo amigos</option>
          <option value="private">Privado</option>
        </Select>
      </div>

      <div className="mb-4 border border-gray-200 dark:border-gray-700 rounded-xl p-4 bg-gray-50/50 dark:bg-gray-800/50">
        <p className="font-semibold text-sm mb-3 text-gray-800 dark:text-gray-200">Visibilidad de campos</p>
        <div className="flex flex-col gap-2.5">
          <label className="flex items-center gap-2 cursor-pointer text-sm">
            <Controller
              name="show_email"
              control={control}
              render={({ field }) => (
                <Checkbox
                  id="show_email"
                  checked={field.value}
                  onChange={(e) => field.onChange(e.target.checked)}
                />
              )}
            />
            <span className="text-gray-700 dark:text-gray-300">Mostrar email públicamente</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer text-sm">
            <Controller
              name="show_birth_date"
              control={control}
              render={({ field }) => (
                <Checkbox
                  id="show_birth_date"
                  checked={field.value}
                  onChange={(e) => field.onChange(e.target.checked)}
                />
              )}
            />
            <span className="text-gray-700 dark:text-gray-300">Mostrar fecha de nacimiento</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer text-sm">
            <Controller
              name="show_location"
              control={control}
              render={({ field }) => (
                <Checkbox
                  id="show_location"
                  checked={field.value}
                  onChange={(e) => field.onChange(e.target.checked)}
                />
              )}
            />
            <span className="text-gray-700 dark:text-gray-300">Mostrar ubicación</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer text-sm">
            <Controller
              name="show_bio"
              control={control}
              render={({ field }) => (
                <Checkbox
                  id="show_bio"
                  checked={field.value}
                  onChange={(e) => field.onChange(e.target.checked)}
                />
              )}
            />
            <span className="text-gray-700 dark:text-gray-300">Mostrar biografía</span>
          </label>
        </div>
      </div>

      <div className="mb-4">
        <Label htmlFor="bio" value="Biografía enriquecida" />
        <BioEditor
          content={bioContent}
          onChange={(value: string) => setValue('bio', value, { shouldValidate: true })}
        />
        {errors.bio && (
          <p className="mt-1 text-xs text-red-600">{errors.bio.message}</p>
        )}
      </div>

      {serverError && (
        <p className="mb-4 text-sm text-red-600 bg-red-50 p-2.5 rounded-lg border border-red-200">
          {serverError}
        </p>
      )}

      <div className="flex justify-between pt-2">
        <Button type="submit" disabled={isSubmitting} className="bg-teal-600 hover:bg-teal-700">
          {isSubmitting ? 'Guardando...' : 'Guardar cambios'}
        </Button>
        <Button color="light" onClick={() => navigate('/profile')}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}

export const EditProfile = EditProfileForm;
export default EditProfileForm;