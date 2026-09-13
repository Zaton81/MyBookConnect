import { z } from 'zod';

export const readingListSchema = z.object({
  name: z
    .string()
    .min(1, 'El nombre de la lista es obligatorio')
    .max(200, 'El nombre no puede superar 200 caracteres'),
  description: z
    .string()
    .max(1000, 'La descripción no puede superar 1000 caracteres')
    .optional()
    .or(z.literal('')),
  privacy: z.enum(['public', 'followers', 'private']),
});

export type ReadingListFormData = z.infer<typeof readingListSchema>;
