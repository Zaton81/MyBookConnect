import { Suspense, lazy } from 'react';
import { BrowserRouter, Navigate, Routes, Route, useParams } from 'react-router-dom';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Header } from "./components/header";
import { Logo } from "./components/logo";
import { FooterSection } from "./components/footer";
import { CookieBanner } from "./components/CookieBanner";
import AuthBox from './components/AuthBox';
import { useAuthStore } from './store/auth';

const EditProfile = lazy(() => import('./pages/EditProfile').then(m => ({ default: m.EditProfile })));
const Profile = lazy(() => import('./pages/Profile').then(m => ({ default: m.Profile })));
const Library = lazy(() => import('./pages/Library').then(m => ({ default: m.Library })));
const AddBook = lazy(() => import('./pages/AddBook').then(m => ({ default: m.AddBook })));
const Home = lazy(() => import('./pages/Home').then(m => ({ default: m.Home })));
const BookDetail = lazy(() => import('./pages/BookDetail').then(m => ({ default: m.BookDetail })));
const Author = lazy(() => import('./pages/Author').then(m => ({ default: m.Author })));
const Friends = lazy(() => import('./pages/Friends').then(m => ({ default: m.Friends })));
const Chat = lazy(() => import('./pages/Chat').then(m => ({ default: m.Chat })));
const PrivacyPolicy = lazy(() => import('./pages/legal/PrivacyPolicy').then(m => ({ default: m.PrivacyPolicy })));
const TermsOfService = lazy(() => import('./pages/legal/TermsOfService').then(m => ({ default: m.TermsOfService })));
const CookiePolicy = lazy(() => import('./pages/legal/CookiePolicy').then(m => ({ default: m.CookiePolicy })));
const AdminDashboard = lazy(() => import('./pages/AdminDashboard').then(m => ({ default: m.AdminDashboard })));
const ReadingLists = lazy(() => import('./pages/ReadingLists').then(m => ({ default: m.ReadingLists })));
const ReadingStats = lazy(() => import('./pages/ReadingStats').then(m => ({ default: m.ReadingStats })));

function ProfileIdRedirect() {
  const { id } = useParams();
  return <Navigate to={`/users/${id}`} replace />;
}

export default function App() {
  const isAuthenticated = useAuthStore(s => s.isAuthenticated);

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col font-sans antialiased">
        <Header />
        <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <Suspense
            fallback={
              <div className="flex items-center justify-center min-h-[40vh]">
                <div className="text-teal-600 dark:text-teal-400 font-semibold flex items-center gap-2">
                  <span className="animate-spin text-2xl">⏳</span>
                  <span>Cargando contenido...</span>
                </div>
              </div>
            }
          >
            <Routes>
              <Route
                path="/"
                element={
                  isAuthenticated ? (
                    <Navigate to="/home" replace />
                  ) : (
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
                  )
                }
              />

              <Route
                path="/home"
                element={
                  <ProtectedRoute>
                    <Home />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/books/add"
                element={
                  <ProtectedRoute>
                    <AddBook />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/library"
                element={
                  <ProtectedRoute>
                    <Library />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/reading-lists"
                element={
                  <ProtectedRoute>
                    <ReadingLists />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/lists"
                element={<Navigate to="/reading-lists" replace />}
              />
              <Route
                path="/statistics"
                element={
                  <ProtectedRoute>
                    <ReadingStats />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/users/:id/statistics"
                element={
                  <ProtectedRoute>
                    <ReadingStats />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/books/:id"
                element={
                  <ProtectedRoute>
                    <BookDetail />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/authors/:id"
                element={
                  <ProtectedRoute>
                    <Author />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/profile"
                element={
                  <ProtectedRoute>
                    <Profile />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/profile/edit"
                element={
                  <ProtectedRoute>
                    <EditProfile />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/profile/:id"
                element={<ProfileIdRedirect />}
              />
              <Route
                path="/users/:userId"
                element={
                  <ProtectedRoute>
                    <Profile />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/chat"
                element={
                  <ProtectedRoute>
                    <Chat />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/friends"
                element={
                  <ProtectedRoute>
                    <Friends />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin"
                element={
                  <ProtectedRoute>
                    <AdminDashboard />
                  </ProtectedRoute>
                }
              />
              <Route path="/privacy" element={<PrivacyPolicy />} />
              <Route path="/terms" element={<TermsOfService />} />
              <Route path="/cookies" element={<CookiePolicy />} />
            </Routes>
          </Suspense>
        </main>
        <FooterSection />
        <CookieBanner />
      </div>
    </BrowserRouter>
  );
}
