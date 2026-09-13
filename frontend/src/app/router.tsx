import { lazy } from 'react';
import { BrowserRouter, Navigate, Routes, Route, useParams } from 'react-router-dom';
import { AuthBox } from '../features/auth';
import { Logo, PublicLayout, ProtectedLayout, AdminLayout } from '../components/layout';
import { useAuthStore } from '../store/auth';

const EditProfile = lazy(() => import('../features/profile').then(m => ({ default: m.EditProfile })));
const Profile = lazy(() => import('../features/profile').then(m => ({ default: m.Profile })));
const Library = lazy(() => import('../features/library').then(m => ({ default: m.Library })));
const AddBook = lazy(() => import('../features/books').then(m => ({ default: m.AddBook })));
const Home = lazy(() => import('../features/social').then(m => ({ default: m.Home })));
const BookDetail = lazy(() => import('../features/books').then(m => ({ default: m.BookDetail })));
const Author = lazy(() => import('../features/books').then(m => ({ default: m.Author })));
const Friends = lazy(() => import('../features/social').then(m => ({ default: m.Friends })));
const Chat = lazy(() => import('../features/chat').then(m => ({ default: m.Chat })));
const PrivacyPolicy = lazy(() => import('../features/legal').then(m => ({ default: m.PrivacyPolicy })));
const TermsOfService = lazy(() => import('../features/legal').then(m => ({ default: m.TermsOfService })));
const CookiePolicy = lazy(() => import('../features/legal').then(m => ({ default: m.CookiePolicy })));
const AdminDashboard = lazy(() => import('../features/admin').then(m => ({ default: m.AdminDashboard })));
const ReadingLists = lazy(() => import('../features/books').then(m => ({ default: m.ReadingLists })));
const ReadingStats = lazy(() => import('../features/books').then(m => ({ default: m.ReadingStats })));

function ProfileIdRedirect() {
  const { id } = useParams();
  return <Navigate to={`/users/${id}`} replace />;
}

function LandingPage() {
  const isAuthenticated = useAuthStore(s => s.isAuthenticated);

  if (isAuthenticated) {
    return <Navigate to="/home" replace />;
  }

  return (
    <div className="mx-auto grid max-w-5xl grid-cols-1 gap-8 md:grid-cols-2 mt-8 items-center">
      <div className="flex flex-col items-start justify-center px-4">
        <Logo />
        <p className="mt-4 text-slate-600 dark:text-slate-400 text-base leading-relaxed">
          Tu espacio social para organizar lecturas, descubrir nuevos autores y compartir reseñas con una comunidad de apasionados por los libros.
        </p>
      </div>
      <div className="flex items-center justify-center px-4">
        <AuthBox />
      </div>
    </div>
  );
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Rutas Públicas (Landing y Legales) */}
        <Route element={<PublicLayout />}>
          <Route path="/" element={<LandingPage />} />
          <Route path="/privacy" element={<PrivacyPolicy />} />
          <Route path="/terms" element={<TermsOfService />} />
          <Route path="/cookies" element={<CookiePolicy />} />
        </Route>

        {/* Rutas Protegidas de Miembros */}
        <Route element={<ProtectedLayout />}>
          <Route path="/home" element={<Home />} />
          <Route path="/books/add" element={<AddBook />} />
          <Route path="/books/:id" element={<BookDetail />} />
          <Route path="/authors/:id" element={<Author />} />
          <Route path="/library" element={<Library />} />
          <Route path="/reading-lists" element={<ReadingLists />} />
          <Route path="/lists" element={<Navigate to="/reading-lists" replace />} />
          <Route path="/statistics" element={<ReadingStats />} />
          <Route path="/users/:id/statistics" element={<ReadingStats />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/profile/edit" element={<EditProfile />} />
          <Route path="/profile/:id" element={<ProfileIdRedirect />} />
          <Route path="/users/:userId" element={<Profile />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/friends" element={<Friends />} />
        </Route>

        {/* Rutas de Administración y Moderación */}
        <Route element={<AdminLayout />}>
          <Route path="/admin" element={<AdminDashboard />} />
        </Route>

        {/* Ruta Fallback (404) */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default AppRouter;
