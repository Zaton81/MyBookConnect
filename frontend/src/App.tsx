import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from './components/ProtectedRoute';
import { EditProfile } from './pages/EditProfile';
import { Profile } from './pages/Profile';
import { Library } from './pages/Library';
import { AddBook } from './pages/AddBook';
import { Home } from './pages/Home';
import { BookDetail } from './pages/BookDetail';
import { Header } from "./components/header";
import { Logo } from "./components/logo";
import { FooterSection } from "./components/footer";
import AuthBox from './components/AuthBox';
import { Author } from './pages/Author';

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen pt-16 p-6 bg-teal-800">
        <Header />
        <Routes>
          {/* Ruta principal con AuthBox */}
          <Route
            path="/"
            element={
              <main>
                <div className="mx-auto grid max-w-6xl grid-cols-1 gap-6 md:grid-cols-2">
                  <div className="flex flex-col items-start justify-center px-6">
                    <Logo />
                  </div>
                  <div className="flex items-center justify-center px-6">
                    <AuthBox />
                  </div>
                </div>
              </main>
            }
          />

          {/* Rutas protegidas */}
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
            path="/profile/:username"
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
        </Routes>
        <FooterSection />
      </div>
    </BrowserRouter>
  );
}