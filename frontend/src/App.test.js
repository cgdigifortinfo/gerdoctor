import React from 'react';
import { render, screen } from '@testing-library/react';

jest.mock('react-router-dom', () => ({
  BrowserRouter: ({ children }) => <div>{children}</div>,
  Routes: ({ children }) => <div>{children}</div>,
  Route: ({ element }) => <>{element}</>,
}), { virtual: true });
jest.mock('./contexts/AuthContext', () => ({ AuthProvider: ({ children }) => <>{children}</> }));
jest.mock('./contexts/LanguageContext', () => ({ LanguageProvider: ({ children }) => <>{children}</> }));
jest.mock('./contexts/ThemeContext', () => ({ ThemeProvider: ({ children }) => <>{children}</> }));
jest.mock('./components/ProtectedRoute', () => ({ ProtectedRoute: ({ children }) => <>{children}</>, PublicRoute: ({ children }) => <>{children}</> }));
jest.mock('./components/ui/sonner', () => ({ Toaster: () => <div>toaster</div> }));
jest.mock('./pages/Landing', () => () => <div>landing</div>);
jest.mock('./pages/Auth', () => ({ Login: () => <div>login</div>, Register: () => <div>register</div>, ForgotPassword: () => <div>forgot</div>, ResetPassword: () => <div>reset</div> }));
jest.mock('./pages/UserDashboard', () => () => <div>user dashboard</div>);
jest.mock('./pages/AdminDashboard', () => () => <div>admin dashboard</div>);
jest.mock('./pages/PartnerDashboard', () => () => <div>partner dashboard</div>);
jest.mock('./pages/PartnerLanding', () => () => <div>partner landing</div>);
jest.mock('./pages/PartnerPayment', () => ({ PartnerOnboarding: () => <div>partner onboarding</div>, PartnerPaymentSuccess: () => <div>payment success</div> }));

const App = require('./App').default;

test('composes every public and protected application route', () => {
  render(<App />);
  expect(screen.getAllByText('landing').length).toBeGreaterThan(1);
  expect(screen.getByText('admin dashboard')).toBeInTheDocument();
  expect(screen.getByText('partner dashboard')).toBeInTheDocument();
  expect(screen.getByText('user dashboard')).toBeInTheDocument();
  expect(screen.getByText('toaster')).toBeInTheDocument();
});
