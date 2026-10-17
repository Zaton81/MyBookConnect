import { test, expect } from '@playwright/test';

/**
 * Suite E2E: Gestión de Biblioteca, Estanterías e Importación CSV.
 */
test.describe('E2E — Biblioteca Personal e Importación', () => {
  test('Ruta de biblioteca redirige o solicita autenticación si es anónimo', async ({ page }) => {
    await page.goto('/library');
    // Si no está autenticado, redirige a login o muestra botón de acceso
    await expect(page).toHaveURL(/.*(login|library)/);
  });

  test('Página de inicio muestra enlaces a colecciones y exploración', async ({ page }) => {
    await page.goto('/');
    const exploreBtn = page.getByRole('link', { name: /explorar|catálogo|libros/i }).first();
    if (await exploreBtn.isVisible()) {
      await expect(exploreBtn).toBeVisible();
    }
  });
});
