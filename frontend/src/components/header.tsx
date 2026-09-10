import React, { useState, useEffect, useCallback, useRef } from "react";
import { Button, Navbar, Spinner } from "flowbite-react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import logoLibro from "../assets/logo-libro.png";
import { es } from "../locales/es";
import { useAuthStore } from "../store/auth";
import { AIAssistantModal } from "./AIAssistantModal";

export function Header() {
  const { isAuthenticated, logout, user, token } = useAuthStore();
  const navigate = useNavigate();
  const [isAiModalOpen, setIsAiModalOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const [loadingNotifs, setLoadingNotifs] = useState(false);
  const notifDropdownRef = useRef<HTMLDivElement>(null);

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  const fetchUnreadCount = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${apiUrl}/api/v1/users/notifications/unread-count/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setUnreadCount(data.unread_count || 0);
      }
    } catch (e) {
      // silent
    }
  }, [token, apiUrl]);

  useEffect(() => {
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 25000);
    return () => clearInterval(interval);
  }, [fetchUnreadCount]);

  // Cargar notificaciones al abrir panel
  const fetchNotifications = async () => {
    if (!token) return;
    try {
      setLoadingNotifs(true);
      const res = await fetch(`${apiUrl}/api/v1/users/notifications/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setNotifications(Array.isArray(data) ? data : data.results || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingNotifs(false);
    }
  };

  // Cerrar desplegable si hace clic fuera
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (notifDropdownRef.current && !notifDropdownRef.current.contains(event.target as Node)) {
        setIsNotifOpen(false);
      }
    };
    if (isNotifOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isNotifOpen]);

  const handleToggleNotifs = () => {
    const nextState = !isNotifOpen;
    setIsNotifOpen(nextState);
    if (nextState) {
      fetchNotifications();
    }
  };

  const handleMarkRead = async (id: number) => {
    if (!token) return;
    try {
      await fetch(`${apiUrl}/api/v1/users/notifications/${id}/read/`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (e) {
      console.error(e);
    }
  };

  const handleMarkAllRead = async () => {
    if (!token) return;
    try {
      await fetch(`${apiUrl}/api/v1/users/notifications/read-all/`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch (e) {
      console.error(e);
    }
  };

  const handleNotifClick = (n: any) => {
    if (!n.read) {
      handleMarkRead(n.id);
    }
    setIsNotifOpen(false);
    if (n.link) {
      navigate(n.link);
    }
  };
  
  if (!isAuthenticated) return null;

  const isStaff = user && (user.is_staff || user.is_superuser);

  const navLinkClasses = ({ isActive }: { isActive: boolean }) =>
    `px-3.5 py-1.5 rounded-xl text-sm font-medium transition-all ${
      isActive
        ? "bg-white/20 text-white font-bold shadow-sm backdrop-blur-sm"
        : "text-teal-100 hover:text-white hover:bg-white/10"
    }`;

  return (
    <>
      <header className="sticky top-0 z-50 backdrop-blur-md bg-teal-700/95 dark:bg-slate-900/95 border-b border-teal-600/30 shadow-md">
        <Navbar fluid rounded className="bg-transparent max-w-7xl mx-auto py-2.5 px-4 sm:px-6">
          <div className="flex items-center">
            <Link to="/home" className="flex items-center group">
              <div className="relative p-1 mr-2 rounded-xl bg-white/10 group-hover:bg-white/20 transition-colors">
                <img
                  src={logoLibro}
                  className="h-7 sm:h-8 drop-shadow"
                  alt={es.logo_simple.imgAlt}
                  loading="lazy"
                />
              </div>
              <span className="self-center whitespace-nowrap text-xl font-extrabold text-white tracking-tight">
                MyBook<span className="text-teal-200">Connect</span>
              </span>
            </Link>
          </div>

          <div className="flex items-center gap-2 md:order-2">
            {/* Campana de Notificaciones */}
            <div className="relative" ref={notifDropdownRef}>
              <button
                onClick={handleToggleNotifs}
                className="relative p-2 rounded-xl text-teal-100 hover:text-white hover:bg-white/10 transition-colors focus:outline-none focus:ring-2 focus:ring-teal-400"
                title="Notificaciones"
                aria-label="Abrir notificaciones"
              >
                <span className="text-lg leading-none">🔔</span>
                {unreadCount > 0 && (
                  <span className="absolute top-1 right-1 min-w-[18px] h-[18px] flex items-center justify-center px-1 text-[10px] font-black rounded-full bg-red-500 text-white shadow-sm ring-2 ring-teal-700 animate-pulse">
                    {unreadCount > 9 ? "9+" : unreadCount}
                  </span>
                )}
              </button>

              {/* Menú Desplegable de Notificaciones */}
              {isNotifOpen && (
                <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white dark:bg-gray-800 rounded-2xl shadow-2xl border border-gray-100 dark:border-gray-700 py-2 z-50 overflow-hidden">
                  <div className="px-4 py-2.5 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between">
                    <span className="font-bold text-sm text-gray-900 dark:text-white flex items-center gap-1.5">
                      <span>🔔</span>
                      <span>Notificaciones</span>
                      {unreadCount > 0 && (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-teal-100 text-teal-800 font-semibold">
                          {unreadCount} nuevas
                        </span>
                      )}
                    </span>
                    {unreadCount > 0 && (
                      <button
                        onClick={handleMarkAllRead}
                        className="text-xs text-teal-600 hover:text-teal-700 dark:text-teal-400 hover:underline font-semibold"
                      >
                        Marcar todas leídas
                      </button>
                    )}
                  </div>

                  <div className="max-h-80 overflow-y-auto divide-y divide-gray-100 dark:divide-gray-700">
                    {loadingNotifs ? (
                      <div className="p-6 flex justify-center">
                        <Spinner size="sm" color="info" />
                      </div>
                    ) : notifications.length === 0 ? (
                      <div className="p-6 text-center text-xs text-gray-500 dark:text-gray-400">
                        No tienes notificaciones por el momento.
                      </div>
                    ) : (
                      notifications.map((n) => (
                        <div
                          key={n.id}
                          onClick={() => handleNotifClick(n)}
                          className={`p-3 text-xs flex items-start gap-3 cursor-pointer transition-colors ${
                            !n.read
                              ? "bg-teal-50/70 dark:bg-teal-900/20 hover:bg-teal-100/60"
                              : "hover:bg-gray-50 dark:hover:bg-gray-700/40 opacity-80"
                          }`}
                        >
                          <div className="text-base flex-shrink-0 mt-0.5">
                            {n.type === "FOLLOW" ? "👤" : n.type === "MESSAGE" ? "💬" : "📢"}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="font-semibold text-gray-900 dark:text-white truncate">
                              {n.title}
                            </div>
                            {n.message && (
                              <p className="text-gray-600 dark:text-gray-300 line-clamp-2 mt-0.5">
                                {n.message}
                              </p>
                            )}
                            <span className="text-[10px] text-gray-400 mt-1 block">
                              {new Date(n.created_at).toLocaleString()}
                            </span>
                          </div>
                          {!n.read && (
                            <span className="w-2 h-2 rounded-full bg-teal-500 flex-shrink-0 mt-1.5" />
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            {isStaff && (
              <Link
                to="/admin"
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs shadow-md shadow-purple-900/20 transition-all transform hover:scale-105"
                title="Panel de Administración"
              >
                <span>🛡️</span>
                <span className="hidden sm:inline">Admin</span>
              </Link>
            )}
            <button
              onClick={() => setIsAiModalOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-amber-400 to-orange-400 hover:from-amber-300 hover:to-orange-300 text-slate-900 font-bold text-xs shadow-md shadow-amber-500/20 transition-all transform hover:scale-105"
              title="Abrir Asistente BookAI"
            >
              <span>✨</span>
              <span className="hidden sm:inline">BookAI</span>
            </button>
            <Button
              size="xs"
              color="light"
              onClick={logout}
              className="rounded-xl font-medium border-white/20 hover:bg-white/10"
            >
              Salir
            </Button>
            <Navbar.Toggle className="text-white hover:bg-white/10 focus:ring-teal-400" />
          </div>

          <Navbar.Collapse className="mt-2 md:mt-0">
            <NavLink to="/home" className={navLinkClasses} end>
              Inicio
            </NavLink>
            <NavLink to="/library" className={navLinkClasses}>
              Mi Biblioteca
            </NavLink>
            <NavLink to="/books/add" className={navLinkClasses}>
              + Añadir Libro
            </NavLink>
            <NavLink to="/chat" className={navLinkClasses}>
              Mensajes
            </NavLink>
            <NavLink to="/friends" className={navLinkClasses}>
              Amigos
            </NavLink>
            <NavLink to="/profile" className={navLinkClasses}>
              Mi Perfil
            </NavLink>
          </Navbar.Collapse>
        </Navbar>
      </header>

      {/* Modal global del asistente de IA */}
      <AIAssistantModal
        isOpen={isAiModalOpen}
        onClose={() => setIsAiModalOpen(false)}
      />
    </>
  );
}
