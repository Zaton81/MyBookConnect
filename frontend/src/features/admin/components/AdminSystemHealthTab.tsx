import { useState, useEffect } from 'react';

interface AlertItem {
  id?: string;
  type: string;
  severity: 'CRITICAL' | 'WARNING' | 'INFO' | string;
  message: string;
  timestamp?: string;
  metadata?: any;
}

interface AdminSystemHealthTabProps {
  token: string | null;
  apiUrl: string;
}

export function AdminSystemHealthTab({ token, apiUrl }: AdminSystemHealthTabProps) {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [metrics, setMetrics] = useState<any | null>(null);
  const [liveness, setLiveness] = useState<'healthy' | 'unhealthy' | 'checking'>('checking');
  const [readiness, setReadiness] = useState<'ready' | 'not_ready' | 'checking'>('checking');
  const [readinessDetails, setReadinessDetails] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);

  const checkHealth = async () => {
    setLoading(true);
    // 1. Liveness
    try {
      const res = await fetch(`${apiUrl}/api/v1/health/`);
      if (res.ok) {
        setLiveness('healthy');
      } else {
        setLiveness('unhealthy');
      }
    } catch {
      setLiveness('unhealthy');
    }

    // 2. Readiness
    try {
      const res = await fetch(`${apiUrl}/api/v1/ready/`);
      if (res.ok) {
        const data = await res.json().catch(() => ({}));
        setReadiness('ready');
        setReadinessDetails(data);
      } else {
        const data = await res.json().catch(() => ({}));
        setReadiness('not_ready');
        setReadinessDetails(data);
      }
    } catch {
      setReadiness('not_ready');
    }

    // 3. Alertas activas de la beta (Fase 36)
    if (token) {
      try {
        const res = await fetch(`${apiUrl}/api/v1/beta/admin/alerts/`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setAlerts(data.alerts || []);
        }
      } catch (e) {
        console.error('Error cargando alertas:', e);
      }

      // 4. Métricas de cohorte beta
      try {
        const res = await fetch(`${apiUrl}/api/v1/beta/admin/metrics/`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setMetrics(data);
        }
      } catch (e) {
        console.error('Error cargando métricas de cohorte:', e);
      }
    }

    setLoading(false);
  };

  useEffect(() => {
    checkHealth();
  }, [token]);

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Cabecera */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white dark:bg-slate-800 p-6 rounded-3xl border border-slate-200/80 dark:border-slate-700 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">⚡</span>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              Salud del Sistema & Telemetría Operativa
            </h2>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-xl">
            Inspección de microservicios, sondas de Liveness/Readiness, base de datos PostgreSQL, colas Celery/Redis y alertas de seguridad.
          </p>
        </div>

        <button
          onClick={checkHealth}
          disabled={loading}
          className="bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 text-xs font-bold px-4 py-2.5 rounded-2xl transition-all shadow-xs flex items-center gap-1.5"
        >
          <span>{loading ? '⏳' : '🔄'}</span>
          <span>{loading ? 'Verificando...' : 'Reescanear Sistema'}</span>
        </button>
      </div>

      {/* Sondas de Salud en Vivo */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Liveness Probe */}
        <div className="bg-white dark:bg-slate-800 p-5 rounded-3xl border border-slate-200/80 dark:border-slate-700 shadow-sm space-y-2">
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            Sonda de Vida (Liveness)
          </div>
          <div className="flex items-center gap-2">
            {liveness === 'healthy' ? (
              <span className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse" />
            ) : liveness === 'unhealthy' ? (
              <span className="w-3 h-3 rounded-full bg-rose-500" />
            ) : (
              <span className="w-3 h-3 rounded-full bg-amber-500" />
            )}
            <span className="text-lg font-bold text-slate-900 dark:text-white">
              {liveness === 'healthy' ? 'Operativo' : liveness === 'unhealthy' ? 'Fallo de Vida' : 'Comprobando...'}
            </span>
          </div>
          <div className="text-[11px] text-slate-400 font-mono">
            GET /api/v1/health/
          </div>
        </div>

        {/* Readiness Probe */}
        <div className="bg-white dark:bg-slate-800 p-5 rounded-3xl border border-slate-200/80 dark:border-slate-700 shadow-sm space-y-2">
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            Sonda de Preparación (Readiness)
          </div>
          <div className="flex items-center gap-2">
            {readiness === 'ready' ? (
              <span className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse" />
            ) : readiness === 'not_ready' ? (
              <span className="w-3 h-3 rounded-full bg-rose-500" />
            ) : (
              <span className="w-3 h-3 rounded-full bg-amber-500" />
            )}
            <span className="text-lg font-bold text-slate-900 dark:text-white">
              {readiness === 'ready' ? 'Listo (DB & Cache)' : readiness === 'not_ready' ? 'Degradado' : 'Comprobando...'}
            </span>
          </div>
          <div className="text-[11px] text-slate-400 font-mono">
            GET /api/v1/ready/ {readinessDetails?.status ? `(${readinessDetails.status})` : ''}
          </div>
        </div>

        {/* Alertas Activas */}
        <div className="bg-white dark:bg-slate-800 p-5 rounded-3xl border border-slate-200/80 dark:border-slate-700 shadow-sm space-y-2">
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            Alertas Operativas Activas
          </div>
          <div className="text-2xl font-black text-slate-900 dark:text-white">
            {alerts.length}
          </div>
          <div className="text-[11px] text-slate-500">
            {alerts.length === 0 ? 'Sin incidencias críticas' : `${alerts.length} alertas sin mitigar`}
          </div>
        </div>

        {/* Documentación & OpenAPI */}
        <div className="bg-white dark:bg-slate-800 p-5 rounded-3xl border border-slate-200/80 dark:border-slate-700 shadow-sm space-y-2">
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            Especificación OpenAPI
          </div>
          <div className="text-xs text-slate-600 dark:text-slate-300 font-semibold pt-1">
            Contrato REST v1.0.0
          </div>
          <div className="flex items-center gap-2 pt-1">
            <a
              href={`${apiUrl}/api/docs/`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs font-bold text-teal-600 dark:text-teal-400 hover:underline flex items-center gap-1"
            >
              <span>Swagger UI</span>
              <span>↗</span>
            </a>
            <span className="text-slate-400">•</span>
            <a
              href={`${apiUrl}/api/schema/`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs font-bold text-slate-500 hover:underline flex items-center gap-1"
            >
              <span>JSON Schema</span>
              <span>↗</span>
            </a>
          </div>
        </div>
      </div>

      {/* Métricas de Cohorte Beta si están disponibles */}
      {metrics && (
        <div className="bg-white dark:bg-slate-800 p-6 rounded-3xl border border-slate-200/80 dark:border-slate-700 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <span>📈</span>
            <span>Métricas de Cohorte & Activación de la Beta</span>
          </h3>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-4 bg-slate-50 dark:bg-slate-900/60 rounded-2xl">
              <div className="text-xs text-slate-500 font-medium">Usuarios Registrados</div>
              <div className="text-xl font-bold text-slate-900 dark:text-white mt-1">
                {metrics.total_users ?? '-'}
              </div>
            </div>
            <div className="p-4 bg-slate-50 dark:bg-slate-900/60 rounded-2xl">
              <div className="text-xs text-slate-500 font-medium">Usuarios Activos</div>
              <div className="text-xl font-bold text-teal-600 dark:text-teal-400 mt-1">
                {metrics.active_users ?? '-'}
              </div>
            </div>
            <div className="p-4 bg-slate-50 dark:bg-slate-900/60 rounded-2xl">
              <div className="text-xs text-slate-500 font-medium">Tasa de Activación</div>
              <div className="text-xl font-bold text-indigo-600 dark:text-indigo-400 mt-1">
                {metrics.activation_rate ? `${metrics.activation_rate}%` : '-'}
              </div>
            </div>
            <div className="p-4 bg-slate-50 dark:bg-slate-900/60 rounded-2xl">
              <div className="text-xs text-slate-500 font-medium">Retención Día 7 (D7)</div>
              <div className="text-xl font-bold text-amber-600 dark:text-amber-400 mt-1">
                {metrics.d7_retention ? `${metrics.d7_retention}%` : '-'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Alertas del Sistema */}
      <div className="bg-white dark:bg-slate-800 p-6 rounded-3xl border border-slate-200/80 dark:border-slate-700 shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <span>🚨</span>
          <span>Alertas Operativas e Incidencias en Cola</span>
        </h3>

        {alerts.length === 0 ? (
          <div className="text-center py-8 border border-dashed border-slate-200 dark:border-slate-700 rounded-2xl text-xs text-slate-500">
            ✓ Todos los subsistemas operan dentro de los umbrales nominales de disponibilidad.
          </div>
        ) : (
          <div className="space-y-3">
            {alerts.map((alert, i) => (
              <div
                key={i}
                className="p-4 rounded-2xl border border-rose-200 dark:border-rose-900/60 bg-rose-50/50 dark:bg-rose-950/30 flex items-start gap-3"
              >
                <span className="text-xl">⚠️</span>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-rose-800 dark:text-rose-200 uppercase">
                      {alert.type || 'ALERTA'}
                    </span>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-200 dark:bg-rose-900 text-rose-900 dark:text-rose-100">
                      {alert.severity || 'CRITICAL'}
                    </span>
                  </div>
                  <p className="text-xs text-rose-900 dark:text-rose-200 font-medium">
                    {alert.message}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Enlaces y Acciones Técnicas Rápidas */}
      <div className="bg-white dark:bg-slate-800 p-6 rounded-3xl border border-slate-200/80 dark:border-slate-700 shadow-sm space-y-3">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white">
          Herramientas de Diagnóstico y Backend
        </h3>
        <p className="text-xs text-slate-500">
          Accesos directos a los recursos técnicos para superadministradores y equipo de ingeniería:
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
          <a
            href={`${apiUrl}/api/docs/`}
            target="_blank"
            rel="noopener noreferrer"
            className="p-4 rounded-2xl border border-slate-200 dark:border-slate-700 hover:border-teal-500 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-all text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center justify-between"
          >
            <span className="flex items-center gap-2">
              <span>📖</span>
              <span>Documentación Swagger UI</span>
            </span>
            <span>↗</span>
          </a>

          <a
            href={`${apiUrl}/api/redoc/`}
            target="_blank"
            rel="noopener noreferrer"
            className="p-4 rounded-2xl border border-slate-200 dark:border-slate-700 hover:border-teal-500 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-all text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center justify-between"
          >
            <span className="flex items-center gap-2">
              <span>📑</span>
              <span>Especificación Redoc</span>
            </span>
            <span>↗</span>
          </a>

          <a
            href={`${apiUrl}/api/v1/observability/metrics/`}
            target="_blank"
            rel="noopener noreferrer"
            className="p-4 rounded-2xl border border-slate-200 dark:border-slate-700 hover:border-teal-500 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-all text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center justify-between"
          >
            <span className="flex items-center gap-2">
              <span>📊</span>
              <span>Métricas de Observabilidad</span>
            </span>
            <span>↗</span>
          </a>
        </div>
      </div>
    </div>
  );
}
export default AdminSystemHealthTab;
