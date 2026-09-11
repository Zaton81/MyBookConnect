/**
 * Resuelve URLs de archivos multimedia (portadas, avatares).
 * Si la URL ya es absoluta (http/https/data:), se mantiene intacta.
 * Si es relativa (/media/...), la prefija con el host base de la API.
 */
export function resolveMediaUrl(pathOrUrl?: string | null): string {
  if (!pathOrUrl) return '';
  if (
    pathOrUrl.startsWith('http://') ||
    pathOrUrl.startsWith('https://') ||
    pathOrUrl.startsWith('data:') ||
    pathOrUrl.startsWith('blob:')
  ) {
    return pathOrUrl;
  }

  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const base = apiUrl.replace(/\/api(\/.*)?$/, '').replace(/\/+$/, '');
  let cleanPath = pathOrUrl.startsWith('/') ? pathOrUrl : `/${pathOrUrl}`;
  if (!cleanPath.startsWith('/media/')) {
    cleanPath = `/media${cleanPath}`;
  }
  return `${base}${cleanPath}`;
}
