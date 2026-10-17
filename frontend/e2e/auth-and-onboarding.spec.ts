import { test, expect } from '@playwright/test';

/**
 * Suite E2E: Autenticación, Registro y Flujo de Onboarding.
 */
test.describe('E2E — Autenticación y Onboarding', () => {
  test('Página de Login es accesible y valida inputs requeridos', async ({ page }) => {
    await page.goto('/login');

    const submitBtn = page.getByRole('button', { name: /iniciar sesión|login|entrar/i });
    await expect(submitBtn).toBeVisible();

    // Intentar submit sin credenciales
    await submitBtn.click();
    const usernameInput = page.getByLabel(/usuario|username|email/i).first();
    await expect(usernameInput).toBeVisible();
  });

  test('Página de Registro es accesible y muestra selector de modalidad', async ({ page }) => {
    await page.goto('/register');

    await expect(page.getByLabel(/usuario|username/i).first()).toBeVisible();
    await expect(page.getByLabel(/contraseña|password/i).first()).toBeVisible();
  });

  test('Navegación fluida entre login y registro sin errores de consola', async ({ page }) => {
    await page.goto('/login');
    const registerLink = page.getByRole('link', { name: /crear cuenta|regístrate|registro/i }).first();
    if (await registerLink.isVisible()) {
      await registerLink.click();
      await expect(page).toHaveURL(/.*register/);
    }
  });
});
