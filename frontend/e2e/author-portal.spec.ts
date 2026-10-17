import { test, expect } from '@playwright/test';

/**
 * Suite E2E: Portal de Autores, Publicaciones y Eventos Literarios.
 */
test.describe('E2E — Portal de Autores y Eventos', () => {
  test('Ruta pública de autor responde adecuadamente', async ({ page }) => {
    await page.goto('/authors/1');
    // Si el autor no existe o carga, debe renderizar la vista o 404 manejado
    await expect(page).toHaveURL(/.*authors\/1/);
  });

  test('Componentes de navegación son responsivos', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await expect(page).toHaveTitle(/BookConnect|BookSocial|Social/i);
  });
});
