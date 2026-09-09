import { Link } from 'react-router-dom';
import { openCookiePreferences } from '../../components/CookieBanner';

export function CookiePolicy() {
  return (
    <article className="max-w-4xl mx-auto py-8 px-4 sm:px-6">
      {/* Breadcrumb */}
      <nav aria-label="Navegación secundaria" className="text-xs text-slate-500 dark:text-slate-400 mb-6 flex items-center gap-2">
        <Link to="/" className="hover:text-teal-600 dark:hover:text-teal-400">Inicio</Link>
        <span>/</span>
        <span className="text-slate-800 dark:text-slate-200 font-medium">Política de Cookies</span>
      </nav>

      <header className="border-b border-slate-200 dark:border-slate-800 pb-6 mb-8">
        <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 mb-3">
          <span>🍪 Normativa LSSI / RGPD</span>
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          Política de Cookies
        </h1>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
          Última actualización: Septiembre 2026
        </p>
      </header>

      <div className="prose prose-slate dark:prose-invert max-w-none text-slate-700 dark:text-slate-300 space-y-8 leading-relaxed">
        {/* Banner with Direct Settings Button */}
        <div className="p-4 rounded-2xl bg-teal-50/70 dark:bg-teal-950/40 border border-teal-200/80 dark:border-teal-800/80 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-sm font-bold text-teal-950 dark:text-teal-200">
              ¿Deseas modificar tus preferencias de cookies en cualquier momento?
            </h2>
            <p className="text-xs text-teal-800 dark:text-teal-300 mt-0.5">
              Puedes activar o desactivar las cookies analíticas y de afiliados de Amazon con un solo clic.
            </p>
          </div>
          <button
            type="button"
            onClick={openCookiePreferences}
            className="whitespace-nowrap px-4 py-2 text-xs font-semibold bg-teal-600 hover:bg-teal-700 text-white rounded-xl shadow-sm transition-colors cursor-pointer"
          >
            Abrir Configuración de Cookies
          </button>
        </div>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            1. ¿Qué es una cookie?
          </h2>
          <p className="text-sm">
            Una cookie es un pequeño archivo de texto que un sitio web almacena en tu navegador u ordenador al visitarlo. Las cookies permiten a las páginas recordar tus acciones y preferencias (como inicio de sesión, idioma y opciones de visualización) para que no tengas que volver a configurarlas cada vez que regresas al sitio.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            2. ¿Qué tipos de cookies utilizamos en MyBookConnect?
          </h2>

          <div className="space-y-4 mt-3">
            <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
              <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <span>🔐</span>
                Cookies Técnicas y Esenciales
                <span className="text-[11px] font-semibold text-teal-600 dark:text-teal-400 bg-teal-50 dark:bg-teal-950 px-2 py-0.5 rounded-full border border-teal-200 dark:border-teal-800">
                  Siempre activas
                </span>
              </h3>
              <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                Son estrictamente necesarias para el funcionamiento del portal. Permiten la gestión de sesiones seguras mediante tokens JWT, la navegación por la biblioteca y la protección contra ataques maliciosos tipo Cross-Site Request Forgery (CSRF).
              </p>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
              <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <span>📊</span>
                Cookies de Análisis y Rendimiento
                <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded-full">
                  Opcionales
                </span>
              </h3>
              <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                Recaban información agregada y anónima sobre el tráfico y uso de la plataforma, ayudándonos a detectar páginas lentas, optimizar el motor de búsqueda de libros y perfeccionar la experiencia de usuario.
              </p>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
              <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <span>🏷️</span>
                Cookies de Publicidad y Afiliación (Amazon Associates)
                <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded-full">
                  Opcionales
                </span>
              </h3>
              <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                MyBookConnect incluye enlaces de compra a libros y servicios de lectura en tiendas asociadas, principalmente a través del <strong>Programa de Afiliados de Amazon</strong>. Cuando pulsas en un enlace de afiliado o interactúas con un módulo publicitario de libros, Amazon instala una cookie en tu navegador con una validez determinada (habitualmente 24 horas) para registrar la referencia y acreditar la comisión de venta correspondiente al soporte de nuestro proyecto, sin ningún incremento de precio en tu compra.
              </p>
            </div>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            3. Tabla de cookies y tecnologías de almacenamiento local
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden">
              <thead className="bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200">
                <tr>
                  <th className="p-3">Identificador</th>
                  <th className="p-3">Proveedor</th>
                  <th className="p-3">Finalidad</th>
                  <th className="p-3">Caducidad</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                <tr>
                  <td className="p-3 font-mono font-semibold">mbc_cookie_consent</td>
                  <td className="p-3">MyBookConnect</td>
                  <td className="p-3">Guarda tus elecciones de aceptación/rechazo de cookies.</td>
                  <td className="p-3">1 año</td>
                </tr>
                <tr>
                  <td className="p-3 font-mono font-semibold">auth_token / refresh</td>
                  <td className="p-3">MyBookConnect</td>
                  <td className="p-3">Mantiene la sesión de usuario activa y segura.</td>
                  <td className="p-3">Sesión / 7 días</td>
                </tr>
                <tr>
                  <td className="p-3 font-mono font-semibold">amazon_tag / session-id</td>
                  <td className="p-3">Amazon EU S.à r.l.</td>
                  <td className="p-3">Rastreo de enlaces de afiliado y carrito de libros recomendados.</td>
                  <td className="p-3">24 horas / 90 días</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            4. Cómo gestionar y deshabilitar cookies desde tu navegador
          </h2>
          <p className="text-sm mb-3">
            Además de nuestro panel de preferencias, puedes permitir, bloquear o eliminar las cookies instaladas en tu equipo mediante la configuración de las opciones del navegador que utilices:
          </p>
          <ul className="list-disc pl-5 space-y-1.5 text-sm">
            <li><strong>Google Chrome:</strong> Configuración &gt; Privacidad y seguridad &gt; Cookies y otros datos de sitios.</li>
            <li><strong>Mozilla Firefox:</strong> Ajustes &gt; Privacidad &amp; Seguridad &gt; Cookies y datos del sitio.</li>
            <li><strong>Apple Safari:</strong> Preferencias &gt; Privacidad &gt; Bloquear todas las cookies.</li>
            <li><strong>Microsoft Edge:</strong> Configuración &gt; Permisos del sitio &gt; Cookies y datos del sitio.</li>
          </ul>
        </section>
      </div>
    </article>
  );
}
