import { z } from 'zod';

export const loginSchema = z.object({
  email: z.string().min(1, 'El correo electrónico o nombre de usuario es requerido'),
  password: z.string().min(1, 'La contraseña es requerida'),
});

export type LoginFormData = z.infer<typeof loginSchema>;

export const registerSchema = z.object({
  username: z
    .string()
    .min(3, 'El nombre de usuario debe tener al menos 3 caracteres')
    .max(150, 'El nombre de usuario no puede exceder 150 caracteres')
    .regex(/^[a-zA-Z0-9_]+$/, 'El usuario solo puede contener letras, números y guiones bajos'),
  email: z
    .string()
    .min(1, 'El correo electrónico es requerido')
    .email('Introduce un correo electrónico válido'),
  password: z
    .string()
    .min(8, 'La contraseña debe tener al menos 8 caracteres')
    .regex(/[A-Z]/, 'Debe incluir al menos una letra mayúscula')
    .regex(/[a-z]/, 'Debe incluir al menos una letra minúscula')
    .regex(/[0-9]/, 'Debe incluir al menos un número')
    .regex(/[!@#$%^&*(),.?"':{}|<>\[\]\\/~`_+=;-]/, 'Debe incluir al menos un símbolo especial'),
});

export type RegisterFormData = z.infer<typeof registerSchema>;
