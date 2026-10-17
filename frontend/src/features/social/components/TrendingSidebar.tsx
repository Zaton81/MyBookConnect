import { useNavigate } from 'react-router-dom';
import { AmazonAdSlot } from '../../../components/ui';

export interface TrendingSidebarProps {
  onOpenAiModal: () => void;
}

export function TrendingSidebar({ onOpenAiModal }: TrendingSidebarProps) {
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      <div className="rounded-3xl bg-gradient-to-br from-teal-900 via-teal-800 to-emerald-950 text-white p-6 shadow-xl relative overflow-hidden">
        <div className="w-12 h-12 rounded-2xl bg-white/10 backdrop-blur-md flex items-center justify-center text-2xl mb-4 shadow-inner">
          ✨
        </div>
        <h3 className="text-lg font-bold">Asistente Literario BookAI</h3>
        <p className="mt-2 text-xs sm:text-sm text-teal-100/90 leading-relaxed">
          ¿No sabes qué leer a continuación? Pídele recomendaciones a BookAI basadas en tu
          biblioteca o consulta por géneros y autores.
        </p>
        <button
          onClick={onOpenAiModal}
          className="mt-5 w-full bg-gradient-to-r from-amber-400 to-orange-400 hover:from-amber-300 hover:to-orange-300 text-slate-900 font-bold py-2.5 px-4 rounded-xl text-sm transition-all shadow-md transform hover:-translate-y-0.5 cursor-pointer"
        >
          Abrir BookAI
        </button>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-3xl p-6 border border-gray-100 dark:border-gray-700 shadow-sm space-y-4">
        <h3 className="font-bold text-gray-900 dark:text-white text-base">
          Comunidad & Conexiones
        </h3>
        <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
          Encuentra amigos lectores, compara vuestras estanterías y chatea en tiempo real
          sobre vuestras novelas favoritas.
        </p>
        <div className="pt-2 flex flex-col gap-2">
          <button
            onClick={() => navigate('/friends')}
            className="w-full text-left px-4 py-2.5 rounded-xl text-xs font-semibold bg-gray-50 dark:bg-gray-700 hover:bg-teal-50 dark:hover:bg-teal-900/30 text-gray-700 dark:text-gray-200 hover:text-teal-700 transition-colors flex items-center justify-between cursor-pointer"
          >
            <span>👥 Ver Lista de Amigos</span>
            <span>➔</span>
          </button>
          <button
            onClick={() => navigate('/chat')}
            className="w-full text-left px-4 py-2.5 rounded-xl text-xs font-semibold bg-gray-50 dark:bg-gray-700 hover:bg-teal-50 dark:hover:bg-teal-900/30 text-gray-700 dark:text-gray-200 hover:text-teal-700 transition-colors flex items-center justify-between cursor-pointer"
          >
            <span>💬 Bandeja de Mensajes</span>
            <span>➔</span>
          </button>
        </div>
      </div>

      {/* Espacio Publicitario / Afiliados de Amazon */}
      <AmazonAdSlot variant="card" />
    </div>
  );
}

export default TrendingSidebar;
