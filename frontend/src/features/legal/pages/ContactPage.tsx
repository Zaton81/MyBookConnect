import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

export function ContactPage() {
  const [dynamicDoc, setDynamicDoc] = useState<{
    title: string;
    content: string;
    updated_at?: string;
  } | null>(null);
  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    fetch(`${apiUrl}/api/v1/books/legal/contact/`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && data.content && data.content.trim().length > 0) {
          setDynamicDoc(data);
        }
      })
      .catch(() => {});
  }, [apiUrl]);

  return (
    <article className="max-w-4xl mx-auto py-8 px-4 sm:px-6">
      {/* Breadcrumb */}
      <nav
        aria-label="Navegación secundaria"
        className="text-xs text-slate-500 dark:text-slate-400 mb-6 flex items-center gap-2"
      >
        <Link to="/" className="hover:text-teal-600 dark:hover:text-teal-400">
          Inicio
        </Link>
        <span>/</span>
        <span className="text-slate-800 dark:text-slate-200 font-medium">
          Contacto y Canales Oficiales
        </span>
      </nav>

      <header className="border-b border-slate-200 dark:border-slate-800 pb-6 mb-8">
        <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-semibold bg-cyan-50 dark:bg-cyan-950/60 text-cyan-700 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-800 mb-3">
          <span>📬 Atención al Usuario</span>
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          {dynamicDoc?.title || 'Canales Oficiales de Contacto'}
        </h1>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
          Última actualización:{' '}
          {dynamicDoc?.updated_at
            ? new Date(dynamicDoc.updated_at).toLocaleDateString('es-ES', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })
            : 'Septiembre 2026'}
        </p>
      </header>

      <div className="prose prose-slate dark:prose-invert max-w-none text-slate-700 dark:text-slate-300 space-y-8 leading-relaxed">
        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            1. Puntos de Contacto por Especialidad
          </h2>
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-1">🛠️ Soporte Técnico</h3>
              <p className="text-xs text-slate-600 dark:text-slate-400 mb-2">Para incidencias técnicas, errores en la plataforma o problemas de inicio de sesión.</p>
              <a href="mailto:soporte@mybookconnect.local" className="text-teal-600 dark:text-teal-400 text-xs font-semibold underline">soporte@mybookconnect.local</a>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-1">🔒 Delegado de Privacidad (DPO)</h3>
              <p className="text-xs text-slate-600 dark:text-slate-400 mb-2">Para el ejercicio de derechos ARCO/RGPD y dudas sobre el tratamiento de datos personales.</p>
              <a href="mailto:privacidad@mybookconnect.local" className="text-teal-600 dark:text-teal-400 text-xs font-semibold underline">privacidad@mybookconnect.local</a>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-1">🛡️ Moderación y Seguridad (DSA)</h3>
              <p className="text-xs text-slate-600 dark:text-slate-400 mb-2">Para notificaciones urgentes de contenidos inadecuados o apelaciones de moderación.</p>
              <a href="mailto:moderacion@mybookconnect.local" className="text-teal-600 dark:text-teal-400 text-xs font-semibold underline">moderacion@mybookconnect.local</a>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-1">📖 Propiedad Intelectual</h3>
              <p className="text-xs text-slate-600 dark:text-slate-400 mb-2">Para autores y editoriales sobre derechos de autor o citas bibliográficas.</p>
              <a href="mailto:copyright@mybookconnect.local" className="text-teal-600 dark:text-teal-400 text-xs font-semibold underline">copyright@mybookconnect.local</a>
            </div>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            2. Compromiso de Atención
          </h2>
          <p className="text-sm">
            Nuestro equipo revisa todas las comunicaciones entrantes en días laborables. Las solicitudes de ejercicio de
            derechos conforme al RGPD se procesan con carácter prioritario dentro del plazo legal máximo de un mes.
          </p>
        </section>
      </div>
    </article>
  );
}

export default ContactPage;
