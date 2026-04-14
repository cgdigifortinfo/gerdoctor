import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { LanguageProvider } from "./contexts/LanguageContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import { ProtectedRoute, PublicRoute } from "./components/ProtectedRoute";
import { Toaster } from "./components/ui/sonner";

// Pages
import Landing from "./pages/Landing";
import { Login, Register, ForgotPassword, ResetPassword } from "./pages/Auth";
import UserDashboard from "./pages/UserDashboard";
import AdminDashboard from "./pages/AdminDashboard";
import PartnerDashboard from "./pages/PartnerDashboard";

function App() {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <AuthProvider>
          <div className="App min-h-screen bg-background text-foreground">
            <BrowserRouter>
              <Routes>
                {/* Public Routes */}
                <Route path="/" element={<Landing />} />
                <Route path="/login" element={
                  <PublicRoute>
                    <Login />
                  </PublicRoute>
                } />
                <Route path="/register" element={
                  <PublicRoute>
                    <Register />
                  </PublicRoute>
                } />
                <Route path="/forgot-password" element={<ForgotPassword />} />
                <Route path="/reset-password" element={<ResetPassword />} />

                {/* User Dashboard */}
                <Route path="/dashboard" element={
                  <ProtectedRoute allowedRoles={['user']}>
                    <UserDashboard />
                  </ProtectedRoute>
                } />

                {/* Admin Dashboard */}
                <Route path="/admin" element={
                  <ProtectedRoute allowedRoles={['admin']}>
                    <AdminDashboard />
                  </ProtectedRoute>
                } />

                {/* Partner Dashboard */}
                <Route path="/partner-dashboard" element={
                  <ProtectedRoute allowedRoles={['partner']}>
                    <PartnerDashboard />
                  </ProtectedRoute>
                } />

                {/* Catch all */}
                <Route path="*" element={<Landing />} />
              </Routes>
            </BrowserRouter>
            <Toaster position="top-right" richColors />
          </div>
        </AuthProvider>
      </LanguageProvider>
    </ThemeProvider>
  );
}

export default App;
