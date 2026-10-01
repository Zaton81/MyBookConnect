import { lazy } from 'react';
import { BrowserRouter, Navigate, Routes, Route, useParams } from 'react-router-dom';
import { PublicLayout, ProtectedLayout, AdminLayout, ScrollToTop } from '../components/layout';

const EditProfile = lazy(() =>
  import('../features/profile').then((m) => ({ default: m.EditProfile }))
);
const Profile = lazy(() => import('../features/profile').then((m) => ({ default: m.Profile })));
const Library = lazy(() => import('../features/library').then((m) => ({ default: m.Library })));
const AddBook = lazy(() => import('../features/books').then((m) => ({ default: m.AddBook })));
const Home = lazy(() => import('../features/social').then((m) => ({ default: m.Home })));
const BookDetail = lazy(() => import('../features/books').then((m) => ({ default: m.BookDetail })));
const Author = lazy(() => import('../features/books').then((m) => ({ default: m.Author })));
const Friends = lazy(() => import('../features/social').then((m) => ({ default: m.Friends })));
const Chat = lazy(() => import('../features/chat').then((m) => ({ default: m.Chat })));
const PrivacyPolicy = lazy(() =>
  import('../features/legal').then((m) => ({ default: m.PrivacyPolicy }))
);
const TermsOfService = lazy(() =>
  import('../features/legal').then((m) => ({ default: m.TermsOfService }))
);
const CookiePolicy = lazy(() =>
  import('../features/legal').then((m) => ({ default: m.CookiePolicy }))
);
const LegalNotice = lazy(() =>
  import('../features/legal').then((m) => ({ default: m.LegalNotice }))
);
const ContentPolicy = lazy(() =>
  import('../features/legal').then((m) => ({ default: m.ContentPolicy }))
);
const DeletionPolicy = lazy(() =>
  import('../features/legal').then((m) => ({ default: m.DeletionPolicy }))
);
const ContactPage = lazy(() =>
  import('../features/legal').then((m) => ({ default: m.ContactPage }))
);
const AdminDashboard = lazy(() =>
  import('../features/admin').then((m) => ({ default: m.AdminDashboard }))
);
const ReadingLists = lazy(() =>
  import('../features/books').then((m) => ({ default: m.ReadingLists }))
);
const ReadingStats = lazy(() =>
  import('../features/books').then((m) => ({ default: m.ReadingStats }))
);
const NotificationsPage = lazy(() =>
  import('../features/social').then((m) => ({ default: m.NotificationsPage }))
);
const OnboardingPage = lazy(() =>
  import('../features/onboarding').then((m) => ({ default: m.OnboardingPage }))
);
const PublicLandingPage = lazy(() =>
  import('../features/discovery').then((m) => ({ default: m.PublicLandingPage }))
);

function ProfileIdRedirect() {
  const { id } = useParams();
  return <Navigate to={`/users/${id}`} replace />;
}

export const ADMIN_ROUTE = (import.meta as any).env?.VITE_ADMIN_PATH || '/panel-control-mbc';

export function AppRouter() {
  return (
    <BrowserRouter>
      <ScrollToTop />
      <Routes>
        {/* Rutas Públicas (Landing, Auth y Legales) */}
        <Route element={<PublicLayout />}>
          <Route path="/" element={<PublicLandingPage />} />
          <Route path="/login" element={<Navigate to="/?auth=login" replace />} />
          <Route path="/register" element={<Navigate to="/?auth=register" replace />} />
          <Route path="/privacy" element={<PrivacyPolicy />} />
          <Route path="/terms" element={<TermsOfService />} />
          <Route path="/cookies" element={<CookiePolicy />} />
          <Route path="/legal-notice" element={<LegalNotice />} />
          <Route path="/legal" element={<Navigate to="/legal-notice" replace />} />
          <Route path="/content-policy" element={<ContentPolicy />} />
          <Route path="/deletion-policy" element={<DeletionPolicy />} />
          <Route path="/contact" element={<ContactPage />} />
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
          <Route path="/settings" element={<Navigate to="/profile/edit" replace />} />
          <Route path="/profile/:id" element={<ProfileIdRedirect />} />
          <Route path="/users/:userId" element={<Profile />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/friends" element={<Friends />} />
          <Route path="/notifications" element={<NotificationsPage />} />
          <Route path="/onboarding" element={<OnboardingPage />} />
        </Route>

        {/* Rutas de Administración y Moderación Seguras */}
        <Route element={<AdminLayout />}>
          <Route path={ADMIN_ROUTE} element={<AdminDashboard />} />
        </Route>

        {/* Trampa de seguridad: /admin redirige a home */}
        <Route path="/admin" element={<Navigate to="/" replace />} />

        {/* Ruta Fallback (404) */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default AppRouter;
