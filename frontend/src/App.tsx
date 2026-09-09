import { Suspense, lazy } from 'react';
import { BrowserRouter, Navigate, Routes, Route, useParams } from 'react-router-dom';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Header } from "./components/header";
import { Logo } from "./components/logo";
import { FooterSection } from "./components/footer";
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

function ProfileIdRedirect() {
  const { id } = useParams();
  return <Navigate to={`/users/${id}`} replace />;
}

export default function App() {
  const isAuthenticated = useAuthStore(s => s.isAuthenticated);

  return (
    <BrowserRouter>
      <div className="min-h-screen pt-16 p-4 sm:p-6 bg-teal-800">
        <Header />
        <Suspense fallback={<div className="text-white p-6 text-center font-medium">Cargando…</div>}>
          <Routes>
            <Route
              path="/"
              element={
                isAuthenticated ? (
                  <Navigate to="/home" replace />
                ) : (
                  <main>
                    <div className="mx-auto grid max-w-6xl grid-cols-1 gap-6 md:grid-cols-2 mt-8">
                      <div className="flex flex-col items-start justify-center px-6">
                        <Logo />
                      </div>
                      <div className="flex items-center justify-center px-6">
                        <AuthBox />
                      </div>
                    </div>
                  </main>
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
          </Routes>
        </Suspense>
        <FooterSection />
      </div>
    </BrowserRouter>
  );
}
