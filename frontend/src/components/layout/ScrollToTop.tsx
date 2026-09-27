import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

/**
 * Componente que restablece el desplazamiento de la ventana (scroll) al inicio
 * de la página cada vez que cambia la ruta de navegación (pathname).
 * Soluciona el problema de retención de posición de scroll entre vistas.
 */
export function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo({
      top: 0,
      left: 0,
      behavior: 'instant',
    });
  }, [pathname]);

  return null;
}

export default ScrollToTop;
