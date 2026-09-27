import { z } from 'zod';

export const editProfileSchema = z.object({
  first_name: z.string().max(50, 'Máximo 50 caracteres').optional().or(z.literal('')),
  last_name: z.string().max(50, 'Máximo 50 caracteres').optional().or(z.literal('')),
  email: z.string().email('Introduce un correo electrónico válido').optional().or(z.literal('')),
  birth_date: z.string().optional().or(z.literal('')),
  location: z.string().max(100, 'Máximo 100 caracteres').optional().or(z.literal('')),
  privacy_level: z.enum(['public', 'friends', 'private']),
  reading_privacy_level: z.enum(['public', 'friends', 'private']).optional(),
  activity_privacy_level: z.enum(['public', 'friends', 'private']).optional(),
  allow_messages_from: z.enum(['everyone', 'followed', 'nobody']).optional(),
  bio: z
    .string()
    .max(2000, 'La biografía no puede exceder 2000 caracteres')
    .optional()
    .or(z.literal('')),
  show_email: z.boolean(),
  show_birth_date: z.boolean(),
  show_location: z.boolean(),
  show_bio: z.boolean(),
  gamification_enabled: z.boolean().optional(),
});

export type EditProfileFormData = z.infer<typeof editProfileSchema>;
