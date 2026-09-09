import { Link } from 'react-router-dom';

export function TermsOfService() {
  return (
    <article className="max-w-4xl mx-auto py-8 px-4 sm:px-6">
      {/* Breadcrumb */}
      <nav aria-label="Navegación secundaria" className="text-xs text-slate-500 dark:text-slate-400 mb-6 flex items-center gap-2">
        <Link to="/" className="hover:text-teal-600 dark:hover:text-teal-400">Inicio</Link>
        <span>/</span>
        <span className="text-slate-800 dark:text-slate-200 font-medium">Términos y Condiciones</span>
      </nav>

      <header className="border-b border-slate-200 dark:border-slate-800 pb-6 mb-8">
        <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 mb-3">
          <span>📜 Condiciones de Uso</span>
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          Términos y Condiciones de Servicio
        </h1>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
          Última actualización: Septiembre 2026
        </p>
      </header>

      <div className="prose prose-slate dark:prose-invert max-w-none text-slate-700 dark:text-slate-300 space-y-8 leading-relaxed">
        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            1. Aceptación de los Términos
          </h2>
          <p className="text-sm">
            Al acceder, navegar o registrarte en <strong>MyBookConnect</strong>, aceptas expresamente cumplir con los presentes Términos y Condiciones de Servicio, así como con nuestra Política de Privacidad y Política de Cookies. Si no estás de acuerdo con alguna parte de estas condiciones, debes abstenerte de utilizar la plataforma.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            2. Uso de la Plataforma y Cuenta de Usuario
          </h2>
          <p className="text-sm mb-2">
            Para acceder a ciertas funcionalidades (organizar estanterías, publicar reseñas, mensajería y seguimiento de amigos), es necesario registrar una cuenta:
          </p>
          <ul className="list-disc pl-5 space-y-2 text-sm">
            <li>Te comprometes a proporcionar información verídica y mantener protegida tu contraseña de acceso.</li>
            <li>Queda prohibida la creación de cuentas automatizadas (bots), la suplantación de identidad de otros lectores o autores, y cualquier actividad maliciosa orientada a alterar el funcionamiento de la API o la base de datos.</li>
            <li>Nos reservamos el derecho de suspender o cancelar cuentas que incumplan de forma reiterada las normas de la comunidad.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            3. Normas de Contenido y Comunidad
          </h2>
          <p className="text-sm mb-2">
            MyBookConnect es un espacio seguro para el debate literario y el amor por los libros. Al publicar contenido (reseñas, sinopsis, comentarios, mensajes):
          </p>
          <ul className="list-disc pl-5 space-y-2 text-sm">
            <li>Conservas los derechos de autor de tus opiniones y textos. No obstante, concedes a MyBookConnect una licencia no exclusiva para mostrar dicho contenido dentro de la plataforma.</li>
            <li>No se tolera el acoso, la incitación al odio, el spam comercial no autorizado, ni la difusión deliberada de spoilers sin la debida advertencia.</li>
            <li>El catálogo de libros e información bibliográfica proviene de fuentes abiertas (OpenLibrary, Wikipedia) y de aportaciones comunitarias. Si detectas información errónea o que vulnere derechos de autor, puedes notificarlo mediante la función de reporte de erratas.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            4. Enlaces a Terceros y Programa de Afiliados de Amazon
          </h2>
          <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 text-amber-900 dark:text-amber-200 text-sm leading-relaxed">
            <p className="font-semibold mb-1">Aviso legal sobre Afiliados de Amazon:</p>
            <p>
              MyBookConnect participa en el <strong>Programa de Afiliados de Amazon EU</strong> y otros programas de afiliación similares. Esto nos permite obtener una pequeña comisión cuando realizas una compra a través de nuestros enlaces recomendados de libros, eBooks o Kindle, <em>sin ningún coste adicional para ti</em>.
            </p>
            <p className="mt-2 text-xs">
              No nos responsabilizamos de la disponibilidad, precios, envíos o transacciones comerciales efectuadas directamente en plataformas de terceros como Amazon.
            </p>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            5. Limitación de Responsabilidad
          </h2>
          <p className="text-sm">
            MyBookConnect se proporciona "tal cual" y "según disponibilidad". Aunque trabajamos continuamente para garantizar la máxima estabilidad, rapidez y seguridad, no garantizamos que el servicio esté libre de interrupciones puntuales por labores de mantenimiento o factores ajenos a nuestra infraestructura.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            6. Modificaciones de los Términos
          </h2>
          <p className="text-sm">
            Podremos actualizar estos términos periódicamente para reflejar mejoras técnicas, regulatorias o nuevos servicios. Te informaremos de cambios sustanciales a través de la plataforma o por correo electrónico.
          </p>
        </section>
      </div>
    </article>
  );
}
