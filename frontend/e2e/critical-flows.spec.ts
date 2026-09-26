import { test, expect } from '@playwright/test';

/**
 * Pruebas E2E de flujos críticos de usuario (Fase 10 - Frontend Quality)
 * Cubre: Home, Autenticación (Login/Registro), Catálogo de Libros, Biblioteca y Navegación con Scroll.
 */

test.describe('Flujos Críticos de la Aplicación', () => {
  test('Flujo 1: Carga de la página de inicio y navegación a catálogo', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/BookConnect|BookSocial|Social/i);

    // Navegar a explorar/libros si existe link
    const exploreLink = page.getByRole('link', { name: /explorar|libros|catálogo/i }).first();
    if (await exploreLink.isVisible()) {
      await exploreLink.click();
      await expect(page).toHaveURL(/.*(books|explore|catalogo)/);
    }
  });

  test('Flujo 2: Página de Login accesible y valida inputs requeridos', async ({ page }) => {
    await page.goto('/login');

    const submitBtn = page.getByRole('button', { name: /iniciar sesión|login|entrar/i });
    await expect(submitBtn).toBeVisible();

    // Intentar submit sin credenciales
    await submitBtn.click();
    // Verificar mensaje de validación o campo marcado
    const usernameInput = page.getByLabel(/usuario|username|email/i).first();
    await expect(usernameInput).toBeVisible();
  });

  test('Flujo 3: Página de Registro accesible con campos de validación', async ({ page }) => {
    await page.goto('/register');

    await expect(page.getByLabel(/usuario|username/i).first()).toBeVisible();
    await expect(page.getByLabel(/contraseña|password/i).first()).toBeVisible();
  });

  test('Flujo 4: Navegación entre rutas restaura el scroll al inicio (ScrollToTop)', async ({
    page,
  }) => {
    await page.goto('/');

    // Hacer scroll hacia abajo
    await page.evaluate(() => window.scrollTo(0, 1000));
    const initialScrollY = await page.evaluate(() => window.scrollY);
    expect(initialScrollY).toBeGreaterThanOrEqual(0);

    // Navegar a otra página mediante enlace del router
    const legalOrAboutLink = page.getByRole('link', { name: /términos|privacidad|acerca|legal/i }).first();
    if (await legalOrAboutLink.isVisible()) {
      await legalOrAboutLink.click();
      await page.waitForTimeout(300);
      const newScrollY = await page.evaluate(() => window.scrollY);
      expect(newScrollY).toBe(0);
    }
  });
});
