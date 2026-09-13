import { z } from 'zod';

export const reviewSchema = z.object({
  rating: z
    .number()
    .int('La calificación debe ser un número entero')
    .min(1, 'Por favor califica el libro con al menos 1 punto')
    .max(10, 'La calificación máxima es 10 puntos'),
  title: z
    .string()
    .max(200, 'El título no puede superar 200 caracteres')
    .optional()
    .or(z.literal('')),
  text: z
    .string()
    .max(5000, 'La reseña no puede superar 5000 caracteres')
    .optional()
    .or(z.literal('')),
});

export type ReviewFormData = z.infer<typeof reviewSchema>;

export const commentSchema = z.object({
  content: z
    .string()
    .min(1, 'El comentario no puede estar vacío')
    .max(1000, 'El comentario no puede superar 1000 caracteres'),
});

export type CommentFormData = z.infer<typeof commentSchema>;
