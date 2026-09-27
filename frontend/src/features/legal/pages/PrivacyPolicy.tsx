import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

export function PrivacyPolicy() {
  const [dynamicDoc, setDynamicDoc] = useState<{
    title: string;
    content: string;
    updated_at?: string;
  } | null>(null);
  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    fetch(`${apiUrl}/api/v1/books/legal/privacy/`)
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
          Política de Privacidad
        </span>
      </nav>

      <header className="border-b border-slate-200 dark:border-slate-800 pb-6 mb-8">
        <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-semibold bg-teal-50 dark:bg-teal-950/60 text-teal-700 dark:text-teal-300 border border-teal-200 dark:border-teal-800 mb-3">
          <span>🔒 RGPD (UE 2016/679) / LOPD-GDD</span>
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          {dynamicDoc?.title || 'Política de Privacidad y Protección de Datos'}
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
            1. Responsable del Tratamiento
          </h2>
          <p className="text-sm">
            El responsable del tratamiento de los datos recabados a través de{' '}
            <strong>MyBookConnect</strong> es el equipo promotor de la plataforma. Para cualquier
            consulta relativa a la privacidad o para el ejercicio de tus derechos, puedes contactar
            directamente con nuestro Delegado de Protección de Datos a través de{' '}
            <a
              href="mailto:privacidad@mybookconnect.local"
              className="text-teal-600 dark:text-teal-400 underline font-medium"
            >
              privacidad@mybookconnect.local
            </a>
            .
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            2. Datos Recopilados y Finalidades
          </h2>
          <ul className="list-disc pl-5 space-y-2 text-sm">
            <li>
              <strong>Datos de cuenta y autenticación:</strong> Nombre de usuario, email y
              contraseña cifrada mediante PBKDF2/Argon2. Finalidad: gestión del acceso e inicio de
              sesión seguro mediante JWT.
            </li>
            <li>
              <strong>Perfil público y preferencias:</strong> Biografía opcional, avatar y enlaces a
              redes sociales.
            </li>
            <li>
              <strong>Actividad literaria:</strong> Biblioteca personal, estados de lectura,
              progreso de páginas, calificaciones de 1 a 5 estrellas y reseñas públicas redactadas
              voluntariamente.
            </li>
            <li>
              <strong>Interacción comunitaria:</strong> Listas temáticas de lectura, seguimiento
              social, bloqueos y mensajería en vivo.
            </li>
            <li>
              <strong>Registros técnicos de seguridad:</strong> Dirección IP, User-Agent y marcas de
              tiempo en <code>AuditLog</code> para prevención de fraude y mitigación de
              ciberataques.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            3. Proveedores y Encargados del Tratamiento
          </h2>
          <p className="text-sm mb-2">
            Tus datos se procesan en centros de datos ubicados en la Unión Europea bajo estrictos
            acuerdos de confidencialidad y DPA:
          </p>
          <ul className="list-disc pl-5 space-y-1.5 text-sm">
            <li>
              <strong>Alojamiento e Infraestructura:</strong> Servidores en la UE conformes a RGPD.
            </li>
            <li>
              <strong>Base de Datos y Caché:</strong> PostgreSQL con soporte vectorizado y Redis
              aislado en red interna.
            </li>
            <li>
              <strong>Fuentes Bibliográficas Públicas:</strong> Google Books API y OpenLibrary para
              metadatos públicos de libros.
            </li>
            <li>
              <strong>Comunicaciones:</strong> Servidores SMTP transaccionales seguros para
              notificaciones de seguridad.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            4. Inteligencia Artificial y Ausencia de Entrenamiento de Terceros
          </h2>
          <div className="p-4 rounded-xl bg-teal-50/70 dark:bg-teal-950/40 border border-teal-200 dark:border-teal-800 text-sm">
            <p className="font-semibold text-teal-950 dark:text-teal-200 mb-1">
              Garantía Estricta sobre tus Datos y la IA:
            </p>
            <p className="text-xs text-teal-900 dark:text-teal-300 leading-relaxed">
              Las funciones de búsqueda semántica y recomendación personalizada v3 utilizan
              embeddings matemáticos calculados de forma anónima y aislada.{' '}
              <strong>
                Tus datos personales, lecturas y textos NUNCA se emplean para entrenar modelos de
                Inteligencia Artificial de terceros.
              </strong>
            </p>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            5. Filosofía Analytics Privacy-First
          </h2>
          <p className="text-sm">
            En MyBookConnect <strong>no introducimos tracking innecesario</strong>. No empleamos
            herramientas de rastreo invasivo, cookies de perfilado comercial entre sitios ni
            servicios de publicidad comportamental de terceros. Las estadísticas de la plataforma
            son agregadas, anónimas y orientadas exclusivamente al rendimiento del servicio.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            6. Plazos de Retención y Ejercicio de Derechos (RGPD)
          </h2>
          <p className="text-sm mb-3">
            Conservamos tus datos mientras mantengas tu cuenta activa. En cualquier momento puedes
            ejercer tus derechos:
          </p>
          <div className="grid sm:grid-cols-2 gap-3 text-sm">
            <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
              <span className="font-bold text-slate-900 dark:text-white block mb-1">
                Portabilidad (Art. 20 RGPD)
              </span>
              <span className="text-xs text-slate-600 dark:text-slate-400">
                Descarga en un clic un informe estructurado JSON con toda tu biblioteca, reseñas y
                actividad social desde{' '}
                <Link to="/profile/edit" className="text-teal-600 dark:text-teal-400 underline">
                  Ajustes &gt; Privacidad
                </Link>
                .
              </span>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
              <span className="font-bold text-slate-900 dark:text-white block mb-1">
                Supresión y Olvido (Art. 17 RGPD)
              </span>
              <span className="text-xs text-slate-600 dark:text-slate-400">
                Elimina tu cuenta de manera permanente y atómica con anonimización irreversible de
                tus datos desde{' '}
                <Link to="/profile/edit" className="text-teal-600 dark:text-teal-400 underline">
                  Ajustes &gt; Privacidad
                </Link>
                .
              </span>
            </div>
          </div>
        </section>
      </div>
    </article>
  );
}

export default PrivacyPolicy;
