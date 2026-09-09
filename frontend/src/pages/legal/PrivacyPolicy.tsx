import { Link } from 'react-router-dom';

export function PrivacyPolicy() {
  return (
    <article className="max-w-4xl mx-auto py-8 px-4 sm:px-6">
      {/* Breadcrumb */}
      <nav aria-label="Navegación secundaria" className="text-xs text-slate-500 dark:text-slate-400 mb-6 flex items-center gap-2">
        <Link to="/" className="hover:text-teal-600 dark:hover:text-teal-400">Inicio</Link>
        <span>/</span>
        <span className="text-slate-800 dark:text-slate-200 font-medium">Política de Privacidad</span>
      </nav>

      <header className="border-b border-slate-200 dark:border-slate-800 pb-6 mb-8">
        <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-semibold bg-teal-50 dark:bg-teal-950/60 text-teal-700 dark:text-teal-300 border border-teal-200 dark:border-teal-800 mb-3">
          <span>🔒 RGPD / LOPD-GDD</span>
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          Política de Privacidad
        </h1>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
          Última actualización: Septiembre 2026
        </p>
      </header>

      <div className="prose prose-slate dark:prose-invert max-w-none text-slate-700 dark:text-slate-300 space-y-8 leading-relaxed">
        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            1. Responsable del Tratamiento
          </h2>
          <p className="text-sm">
            El responsable del tratamiento de los datos recabados a través de <strong>MyBookConnect</strong> es el equipo administrador de la plataforma. Para cualquier consulta, ejercicio de derechos o sugerencia relativa a la protección de datos personales, puedes contactar con nosotros a través del correo de soporte habilitado en el servicio.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            2. Datos que recopilamos y finalidad
          </h2>
          <p className="text-sm mb-3">
            Recopilamos únicamente los datos necesarios para ofrecerte una experiencia enriquecedora de lectura comunitaria:
          </p>
          <ul className="list-disc pl-5 space-y-2 text-sm">
            <li>
              <strong>Datos de registro y autenticación:</strong> Nombre de usuario, dirección de correo electrónico y contraseña cifrada mediante algoritmos estándar del sector.
            </li>
            <li>
              <strong>Perfil de lector:</strong> Biografía, avatar opcional, preferencias literarias y enlaces a redes sociales que decidas incorporar voluntariamente.
            </li>
            <li>
              <strong>Actividad de lectura:</strong> Libros guardados en estanterías (leídos, leyendo, por leer), valoraciones (1-10 estrellas), reseñas públicas y erratas reportadas.
            </li>
            <li>
              <strong>Interacción social:</strong> Mensajes en tiempo real con otros usuarios y lista de amigos o seguidores.
            </li>
            <li>
              <strong>Datos técnicos y de uso:</strong> Dirección IP anonimizada, tipo de navegador y registros de auditoría para salvaguardar la seguridad contra abusos y ataques de denegación de servicio.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            3. Base Legal del Tratamiento
          </h2>
          <p className="text-sm">
            El tratamiento de tus datos se fundamenta en:
          </p>
          <ul className="list-disc pl-5 space-y-1.5 text-sm mt-2">
            <li>La <strong>ejecución del contrato</strong> de servicio al registrarte y utilizar la plataforma.</li>
            <li>El <strong>consentimiento explícito</strong> prestado para funcionalidades opcionales (cookies analíticas y publicidad personalizada).</li>
            <li>El <strong>interés legítimo</strong> en mantener la seguridad e integridad técnica de la infraestructura.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            4. Servicios de Terceros, Publicidad y Afiliación (Amazon)
          </h2>
          <p className="text-sm mb-2">
            MyBookConnect participa o prevé participar en programas de afiliados y publicidad digital, principalmente en el <strong>Programa de Afiliados de Amazon EU</strong>. Esto significa que:
          </p>
          <ul className="list-disc pl-5 space-y-2 text-sm">
            <li>
              Cuando haces clic en un enlace a libros o productos de Amazon en nuestra web, Amazon puede instalar cookies o utilizar identificadores para rastrear la referencia y procesar la comisión por venta.
            </li>
            <li>
              Dichas compras no tienen ningún sobrecoste para ti y ayudan al mantenimiento técnico del servidor de MyBookConnect.
            </li>
            <li>
              Puedes revocar el consentimiento de estas cookies en cualquier momento a través de nuestro <Link to="/cookies" className="text-teal-600 dark:text-teal-400 font-medium underline">Panel de Preferencias de Cookies</Link>.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            5. Tus Derechos (ARCO / RGPD)
          </h2>
          <p className="text-sm mb-3">
            De acuerdo con el Reglamento General de Protección de Datos (RGPD) de la UE, tienes derecho a:
          </p>
          <div className="grid sm:grid-cols-2 gap-3 text-sm">
            <div className="p-3 rounded-xl bg-slate-100 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800">
              <span className="font-semibold text-slate-900 dark:text-white block">Acceso y Rectificación</span>
              <span className="text-xs text-slate-600 dark:text-slate-400">Consultar y editar en cualquier momento los datos de tu perfil en la sección de Ajustes.</span>
            </div>
            <div className="p-3 rounded-xl bg-slate-100 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800">
              <span className="font-semibold text-slate-900 dark:text-white block">Supresión ("Derecho al olvido")</span>
              <span className="text-xs text-slate-600 dark:text-slate-400">Solicitar la eliminación total de tu cuenta y datos asociados.</span>
            </div>
            <div className="p-3 rounded-xl bg-slate-100 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800">
              <span className="font-semibold text-slate-900 dark:text-white block">Portabilidad</span>
              <span className="text-xs text-slate-600 dark:text-slate-400">Descargar tus estanterías y reseñas en formatos interoperables (JSON/CSV).</span>
            </div>
            <div className="p-3 rounded-xl bg-slate-100 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800">
              <span className="font-semibold text-slate-900 dark:text-white block">Limitación y Oposición</span>
              <span className="text-xs text-slate-600 dark:text-slate-400">Oponerte a análisis o comunicaciones promocionales automáticas.</span>
            </div>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
            6. Conservación de Datos
          </h2>
          <p className="text-sm">
            Tus datos se conservarán mientras mantengas activa tu cuenta de usuario. Una vez solicitada la baja, se procederá al borrado seguro o a su bloqueo durante los plazos legalmente exigibles por las normativas aplicables.
          </p>
        </section>
      </div>
    </article>
  );
}
