import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

export function DeletionPolicy() {
  const [dynamicDoc, setDynamicDoc] = useState<{
    title: string;
    content: string;
    updated_at?: string;
  } | null>(null);
  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    fetch(`${apiUrl}/api/v1/books/legal/deletion_policy/`)
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
          Política de Eliminación
        </span>
      </nav>

      <header className="border-b border-slate-200 dark:border-slate-800 pb-6 mb-8">
        <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-semibold bg-violet-50 dark:bg-violet-950/60 text-violet-700 dark:text-violet-300 border border-violet-200 dark:border-violet-800 mb-3">
          <span>🗑️ Derecho al Olvido (RGPD Art. 17)</span>
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          {dynamicDoc?.title || 'Política de Eliminación, Cancelación y Retención'}
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
            1. Control y Soberanía sobre tus Datos
          </h2>
          <p className="text-sm">
            En MyBookConnect creemos que el usuario debe tener control total de su información. Si
            decides dar de baja tu cuenta, nuestro sistema ejecuta un protocolo de disociación y
            anonimización atómica conforme al{' '}
            <strong>Artículo 17 del RGPD (Derecho a la Supresión / Derecho al Olvido)</strong>.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            2. Proceso de Cancelación de Cuenta (Fase 17)
          </h2>
          <p className="text-sm mb-3">
            La baja de la cuenta puede solicitarse en cualquier instante desde{' '}
            <Link
              to="/profile/edit"
              className="text-teal-600 dark:text-teal-400 underline font-medium"
            >
              Ajustes de Perfil &gt; Privacidad &amp; RGPD
            </Link>
            :
          </p>
          <ul className="list-disc pl-5 space-y-2 text-sm">
            <li>
              <strong>Reautenticación:</strong> Verificación mediante la contraseña actual.
            </li>
            <li>
              <strong>Confirmación explícita:</strong> Introducción del término de seguridad{' '}
              <code>ELIMINAR</code>.
            </li>
            <li>
              <strong>Anonimización irreversible:</strong> Tu nombre de usuario y correo electrónico
              se sustituyen por pseudónimos no trazables (<code>deleted_user_...</code>), se
              destruye la contraseña y se borran definitivamente biografías, fotos de perfil y
              fechas personales.
            </li>
            <li>
              <strong>Desconexión social:</strong> Supresión de amistades, seguidores, personas
              seguidas y bloqueos.
            </li>
            <li>
              <strong>Listas de lectura:</strong> Pasan a modo privado y oculto de forma automática.
            </li>
            <li>
              <strong>Revocación de credenciales:</strong> Inmediata invalidación en lista negra de
              todos los tokens JWT.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            3. Reseñas Literarias y Diálogo Comunitario
          </h2>
          <p className="text-sm">
            Para no quebrar las cadenas de discusión y lecturas colectivas, las reseñas previamente
            publicadas se mantienen desvinculadas de cualquier dato de carácter personal bajo la
            autoría anónima de <code>deleted_user_...</code>. Si deseas que tus reseñas no persistan
            tras tu baja, puedes eliminarlas manualmente antes de tramitar la cancelación de tu
            cuenta.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            4. Plazos Legales de Conservación de Logs
          </h2>
          <p className="text-sm">
            Los registros técnicos de conexión y auditoría de ciberseguridad se conservan bloqueados
            durante los períodos estrictamente fijados por la legislación vigente para la depuración
            de responsabilidades técnicas o judiciales.
          </p>
        </section>
      </div>
    </article>
  );
}

export default DeletionPolicy;
