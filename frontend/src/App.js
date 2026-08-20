import "@/App.css";
import "@/design-system.css";
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
import PartnerLanding from "./pages/PartnerLanding";
import { PartnerOnboarding, PartnerPaymentSuccess } from "./pages/PartnerPayment";

function App() {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <AuthProvider>
          <div className="App min-h-screen bg-background text-foreground">
            <BrowserRouter>
              <Routes>
                {/* Public Routes */}
                <Route path="/" element={<PartnerLanding />} />
                <Route path="/aerzte" element={<Landing />} />
                <Route path="/pflege" element={<Landing />} />
                <Route path="/login" element={
                  <PublicRoute>
                    <Login />
                  </PublicRoute>
                } />
                <Route path="/s/:surveySlug/login" element={
                  <PublicRoute>
                    <Login />
                  </PublicRoute>
                } />
                <Route path="/register" element={
                  <PublicRoute>
                    <Register />
                  </PublicRoute>
                } />
                <Route path="/s/:surveySlug/register" element={
                  <PublicRoute>
                    <Register />
                  </PublicRoute>
                } />
                <Route path="/s/:surveySlug" element={<Landing />} />
                <Route path="/forgot-password" element={<ForgotPassword />} />
                <Route path="/reset-password" element={<ResetPassword />} />

                {/* User Dashboard */}
                <Route path="/dashboard" element={
                  <ProtectedRoute allowedRoles={['user']} requiredPermission="portal.user.access">
                    <UserDashboard />
                  </ProtectedRoute>
                } />

                {/* Admin Dashboard */}
                <Route path="/admin" element={
                  <ProtectedRoute allowedRoles={['admin']} requiredPermission="admin.access">
                    <AdminDashboard />
                  </ProtectedRoute>
                } />

                {/* Partner Dashboard */}
                <Route path="/partner-dashboard" element={
                  <ProtectedRoute allowedRoles={['partner']} requiredPermission="portal.partner.access">
                    <PartnerDashboard />
                  </ProtectedRoute>
                } />
                <Route path="/partner-payment" element={<ProtectedRoute allowedRoles={['partner']} requiredPermission="portal.partner.access"><PartnerOnboarding /></ProtectedRoute>} />
                <Route path="/partner-payment/success" element={<ProtectedRoute allowedRoles={['partner']} requiredPermission="portal.partner.access"><PartnerPaymentSuccess /></ProtectedRoute>} />
                <Route path="/partner-payment/cancelled" element={<ProtectedRoute allowedRoles={['partner']} requiredPermission="portal.partner.access"><PartnerOnboarding /></ProtectedRoute>} />

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
