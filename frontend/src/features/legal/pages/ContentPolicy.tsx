import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

export function ContentPolicy() {
  const [dynamicDoc, setDynamicDoc] = useState<{
    title: string;
    content: string;
    updated_at?: string;
  } | null>(null);
  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    fetch(`${apiUrl}/api/v1/books/legal/content_policy/`)
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
          Política de Contenido
        </span>
      </nav>

      <header className="border-b border-slate-200 dark:border-slate-800 pb-6 mb-8">
        <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800 mb-3">
          <span>⚖️ Normativa DSA (UE 2022/2065)</span>
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          {dynamicDoc?.title || 'Política de Contenido y Normas de la Comunidad'}
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
            1. Filosofía de Comunidad Literaria
          </h2>
          <p className="text-sm">
            MyBookConnect es un punto de encuentro para lectores. Valoramos la libertad de criterio,
            el entusiasmo crítico y el debate argumentado. Para garantizar un entorno seguro y agradable
            para todas las sensibilidades lectoras, establecemos las siguientes normas comunitarias.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            2. Conductas y Contenidos Prohibidos
          </h2>
          <ul className="list-disc pl-5 space-y-2 text-sm">
            <li>
              <strong>Acoso, amenazas e incitación al odio:</strong> Queda prohibido cualquier contenido
              que insulte, hostigue o promueva la discriminación por motivos de raza, género, orientación
              sexual, religión, nacionalidad o discapacidad.
            </li>
            <li>
              <strong>Spam y publicidad encubierta:</strong> No se permite la publicación reiterada de
              enlaces con fines lucrativos ajenos a la plataforma, venta no autorizada o esquemas para
              manipular artificialmente las valoraciones de libros.
            </li>
            <li>
              <strong>Contenido ilegal o perjudicial:</strong> Prohibición absoluta de distribución de
              material protegido por derechos de autor sin autorización, malware, o contenido que vulnere
              la integridad de menores.
            </li>
            <li>
              <strong>Spoilers no advertidos:</strong> Desvelar partes cruciales de tramas sin etiquetar
              puede resultar en la ocultación de la reseña por parte de la comunidad.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            3. Mecanismos de Reporte y Moderación (Fase 16)
          </h2>
          <p className="text-sm mb-3">
            Cualquier usuario puede reportar infracciones mediante el botón de denuncia habilitado en
            perfiles, reseñas, comentarios en reseñas, mensajes y listas de lectura:
          </p>
          <div className="grid sm:grid-cols-3 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
              <span className="font-bold block text-slate-900 dark:text-white mb-1">1. Reporte Inmediato</span>
              Selección del motivo de la queja y envío a la cola de moderación.
            </div>
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
              <span className="font-bold block text-slate-900 dark:text-white mb-1">2. Revisión Humana</span>
              Examen por el equipo administrador respetando el principio de proporcionalidad.
            </div>
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
              <span className="font-bold block text-slate-900 dark:text-white mb-1">3. Medida Graduada</span>
              Advertencia, ocultación del contenido o suspensión con registro en auditoría.
            </div>
          </div>
        </section>
      </div>
    </article>
  );
}

export default ContentPolicy;
