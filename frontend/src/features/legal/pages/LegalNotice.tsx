import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

export function LegalNotice() {
  const [dynamicDoc, setDynamicDoc] = useState<{
    title: string;
    content: string;
    updated_at?: string;
  } | null>(null);
  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    fetch(`${apiUrl}/api/v1/books/legal/legal_notice/`)
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
          Aviso Legal
        </span>
      </nav>

      <header className="border-b border-slate-200 dark:border-slate-800 pb-6 mb-8">
        <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 mb-3">
          <span>🏛️ Ley 34/2002 (LSSI-CE)</span>
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          {dynamicDoc?.title || 'Aviso Legal e Información Corporativa'}
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
            1. Datos Identificativos del Prestador (Art. 10 LSSI-CE)
          </h2>
          <p className="text-sm">
            En cumplimiento del deber de información estipulado en el artículo 10 de la Ley 34/2002,
            de 11 de julio, de Servicios de la Sociedad de la Información y de Comercio Electrónico
            (LSSI-CE), se facilita la siguiente información sobre el titular de la plataforma:
          </p>
          <div className="mt-3 p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 text-sm space-y-1.5">
            <p><strong>Plataforma:</strong> MyBookConnect (Red Social de Lectura y Catalogación)</p>
            <p><strong>Correo general:</strong> <a href="mailto:contacto@mybookconnect.local" className="text-teal-600 dark:text-teal-400 underline">contacto@mybookconnect.local</a></p>
            <p><strong>Canal legal y privacidad:</strong> <a href="mailto:legal@mybookconnect.local" className="text-teal-600 dark:text-teal-400 underline">legal@mybookconnect.local</a></p>
            <p><strong>Fase operativa:</strong> Versión Beta Pública para pruebas de comunidad y estabilidad.</p>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            2. Condiciones de Acceso y Uso
          </h2>
          <p className="text-sm">
            El acceso a MyBookConnect es de carácter libre y voluntario. La navegación o registro
            atribuye la condición de usuario e implica la adhesión plena y sin reservas a todas y
            cada una de las disposiciones incluidas en este Aviso Legal y en los Términos de Servicio.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            3. Propiedad Intelectual e Industrial
          </h2>
          <p className="text-sm mb-3">
            Todos los contenidos del portal (código fuente, diseño gráfico, logotipos, iconos, arquitectura
            de datos y desarrollos de software) son titularidad de los promotores de MyBookConnect o cuentan
            con licencias de uso de código abierto (Open Source) debidamente acreditadas.
          </p>
          <p className="text-sm">
            Las portadas, títulos y sinopsis bibliográficas se exhiben exclusivamente con fines informativos,
            de identificación y cita cultural conforme a la Ley de Propiedad Intelectual, procedentes de fuentes
            públicas abiertas (Google Books API y OpenLibrary).
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            4. Exclusión de Garantías y Responsabilidad
          </h2>
          <p className="text-sm">
            MyBookConnect adopta las medidas tecnológicas y organizativas necesarias para evitar la presencia de
            errores o virus en el servidor. No obstante, al tratarse de una versión en fase beta, no se garantiza
            la disponibilidad ininterrumpida ni la ausencia absoluta de incidencias técnicas en períodos de
            mantenimiento o actualización de la plataforma.
          </p>
        </section>
      </div>
    </article>
  );
}

export default LegalNotice;
