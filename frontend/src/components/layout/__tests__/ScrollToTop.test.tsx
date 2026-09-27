import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/react';
import { MemoryRouter, Link, Routes, Route } from 'react-router-dom';
import { ScrollToTop } from '../ScrollToTop';
import userEvent from '@testing-library/user-event';

describe('ScrollToTop Component', () => {
  beforeEach(() => {
    vi.stubGlobal('scrollTo', vi.fn());
  });

  it('llama a window.scrollTo al montar el componente en una ruta inicial', () => {
    render(
      <MemoryRouter initialEntries={['/statistics']}>
        <ScrollToTop />
      </MemoryRouter>
    );

    expect(window.scrollTo).toHaveBeenCalledWith({
      top: 0,
      left: 0,
      behavior: 'instant',
    });
  });

  it('restablece el scroll a (0,0) cuando cambia la ruta de navegacion', async () => {
    const user = userEvent.setup();

    const { getByText } = render(
      <MemoryRouter initialEntries={['/statistics']}>
        <ScrollToTop />
        <nav>
          <Link to="/friends">Ir a Amigos</Link>
        </nav>
        <Routes>
          <Route path="/statistics" element={<div>Estadisticas</div>} />
          <Route path="/friends" element={<div>Lista de Amigos</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(window.scrollTo).toHaveBeenCalledTimes(1);

    const link = getByText('Ir a Amigos');
    await user.click(link);

    expect(window.scrollTo).toHaveBeenCalledTimes(2);
    expect(window.scrollTo).toHaveBeenLastCalledWith({
      top: 0,
      left: 0,
      behavior: 'instant',
    });
  });
});
