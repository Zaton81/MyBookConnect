import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type ThemeMode = 'light' | 'dark' | 'system';

export interface UIState {
  theme: ThemeMode;
  sidebarOpen: boolean;
  activeModals: Record<string, boolean>;
  drafts: Record<string, string>;

  // Theme actions
  setTheme: (theme: ThemeMode) => void;
  toggleTheme: () => void;

  // Sidebar actions
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;

  // Modals actions
  openModal: (modalId: string) => void;
  closeModal: (modalId: string) => void;
  toggleModal: (modalId: string) => void;

  // Drafts actions
  setDraft: (key: string, content: string) => void;
  clearDraft: (key: string) => void;
  clearAllDrafts: () => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set, get) => ({
      theme: 'light',
      sidebarOpen: false,
      activeModals: {},
      drafts: {},

      setTheme: (theme: ThemeMode) => {
        set({ theme });
        if (typeof window !== 'undefined') {
          if (theme === 'dark') {
            document.documentElement.classList.add('dark');
          } else if (theme === 'light') {
            document.documentElement.classList.remove('dark');
          } else {
            const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            if (systemPrefersDark) {
              document.documentElement.classList.add('dark');
            } else {
              document.documentElement.classList.remove('dark');
            }
          }
        }
      },

      toggleTheme: () => {
        const currentTheme = get().theme;
        const nextTheme: ThemeMode = currentTheme === 'dark' ? 'light' : 'dark';
        get().setTheme(nextTheme);
      },

      setSidebarOpen: (open: boolean) => set({ sidebarOpen: open }),

      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

      openModal: (modalId: string) =>
        set((state) => ({
          activeModals: { ...state.activeModals, [modalId]: true },
        })),

      closeModal: (modalId: string) =>
        set((state) => ({
          activeModals: { ...state.activeModals, [modalId]: false },
        })),

      toggleModal: (modalId: string) =>
        set((state) => ({
          activeModals: {
            ...state.activeModals,
            [modalId]: !state.activeModals[modalId],
          },
        })),

      setDraft: (key: string, content: string) =>
        set((state) => ({
          drafts: { ...state.drafts, [key]: content },
        })),

      clearDraft: (key: string) =>
        set((state) => {
          const newDrafts = { ...state.drafts };
          delete newDrafts[key];
          return { drafts: newDrafts };
        }),

      clearAllDrafts: () => set({ drafts: {} }),
    }),
    {
      name: 'ui-storage',
      partialize: (state) => ({
        theme: state.theme,
        drafts: state.drafts,
      }),
    }
  )
);

export default useUIStore;
