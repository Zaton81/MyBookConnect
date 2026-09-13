import { z } from 'zod';

export const chatMessageSchema = z.object({
  message: z
    .string()
    .trim()
    .min(1, 'El mensaje no puede estar vacío')
    .max(2000, 'El mensaje no puede superar 2000 caracteres'),
});

export type ChatMessageFormData = z.infer<typeof chatMessageSchema>;
