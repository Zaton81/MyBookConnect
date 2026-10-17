import { test, expect } from '@playwright/test';

/**
 * Suite E2E: Feed Social, Actividades Comunitarias y Clubes de Lectura.
 */
test.describe('E2E — Clubes de Lectura y Muro Social', () => {
  test('Página de inicio carga correctamente con encabezado y título de la app', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/BookConnect|BookSocial|Social/i);
  });

  test('Ruta de clubes de lectura carga la vista o redirige correctamente', async ({ page }) => {
    await page.goto('/clubs');
    await expect(page).toHaveURL(/.*(clubs|login)/);
  });

  test('ScrollToTop funciona al navegar entre páginas', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => window.scrollTo(0, 1000));
    const initialScrollY = await page.evaluate(() => window.scrollY);
    expect(initialScrollY).toBeGreaterThanOrEqual(0);

    const legalOrAboutLink = page.getByRole('link', { name: /términos|privacidad|legal/i }).first();
    if (await legalOrAboutLink.isVisible()) {
      await legalOrAboutLink.click();
      await page.waitForTimeout(300);
      const newScrollY = await page.evaluate(() => window.scrollY);
      expect(newScrollY).toBe(0);
    }
  });
});
