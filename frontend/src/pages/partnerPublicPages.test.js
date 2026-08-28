import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import PartnerLanding from './PartnerLanding';
import { PartnerOnboarding, PartnerPaymentSuccess } from './PartnerPayment';
import { partnerDashboardAPI, partnerRegistrationAPI, formatApiError } from '../lib/api';
import { toast } from 'sonner';

const mockNavigate = jest.fn();
let mockAuth = { user: null, loading: false, checkAuth: jest.fn() };
let mockSessionId = 'session';
const mockParams = { get: () => mockSessionId };
jest.mock('react-router-dom', () => ({
  Link: ({ children, to }) => <a href={to}>{children}</a>, useNavigate: () => mockNavigate,
  useSearchParams: () => [mockParams],
}), { virtual: true });
jest.mock('../contexts/AuthContext', () => ({ useAuth: () => mockAuth }));
jest.mock('../lib/api', () => ({
  partnerRegistrationAPI: { config: jest.fn(), register: jest.fn() },
  partnerDashboardAPI: { getPaymentStatus: jest.fn(), createCheckout: jest.fn() },
  formatApiError: jest.fn(() => 'api error'),
}));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock('@phosphor-icons/react', () => new Proxy({}, { get: () => () => <i /> }));
jest.mock('../components/Logo', () => ({ Logo: () => <div>logo</div> }));
jest.mock('../components/ThemeLangToggle', () => ({ ThemeLangToggle: () => <button>theme</button> }));
jest.mock('../components/ui/button', () => ({ Button: ({ children, ...props }) => <button {...props}>{children}</button> }));

beforeEach(() => {
  jest.clearAllMocks();
  mockAuth = { user: null, loading: false, checkAuth: jest.fn().mockResolvedValue(undefined) };
  mockSessionId = 'session';
  formatApiError.mockReturnValue('api error');
  partnerRegistrationAPI.config.mockResolvedValue({ data: { stripe: { configured: true, sandbox_mode: true } } });
  partnerRegistrationAPI.register.mockResolvedValue({});
  partnerDashboardAPI.getPaymentStatus.mockResolvedValue({ data: { access_unlocked: false } });
  partnerDashboardAPI.createCheckout.mockResolvedValue({ data: { url: 'https://stripe.test' } });
});

test('partner landing loads Stripe modes and submits all registration fields', async () => {
  const { rerender } = render(<PartnerLanding />);
  expect(await screen.findByTestId('stripe-availability')).toHaveTextContent('Sandbox verfügbar');
  fireEvent.change(document.getElementById('partner-company'), { target: { value: 'School GmbH' } });
  fireEvent.change(document.getElementById('partner-contact'), { target: { value: 'Ada Admin' } });
  fireEvent.change(document.getElementById('partner-email'), { target: { value: 'ada@example.com' } });
  fireEvent.change(document.getElementById('partner-password'), { target: { value: 'password1' } });
  fireEvent.change(screen.getByPlaceholderText('https://'), { target: { value: 'https://school.test' } });
  fireEvent.change(document.querySelector('textarea'), { target: { value: 'Language courses' } });
  fireEvent.submit(screen.getByTestId('partner-registration-form'));
  expect(screen.getByText('Registrierung läuft…')).toBeDisabled();
  await waitFor(() => expect(partnerRegistrationAPI.register).toHaveBeenCalledWith(expect.objectContaining({ company_name: 'School GmbH', country: 'DE' })));
  expect(mockAuth.checkAuth).toHaveBeenCalled();
  expect(toast.success).toHaveBeenCalled();
  expect(mockNavigate).toHaveBeenCalledWith('/partner-payment');

  rerender(<></>);
  partnerRegistrationAPI.config.mockResolvedValueOnce({ data: { stripe: { configured: true, sandbox_mode: false } } });
  render(<PartnerLanding />);
  expect(await screen.findByTestId('stripe-availability')).toHaveTextContent('Live-Verbindung verfügbar');
});

test('partner landing handles config and registration failures and every authenticated redirect', async () => {
  partnerRegistrationAPI.config.mockRejectedValueOnce(new Error('config'));
  partnerRegistrationAPI.register.mockRejectedValueOnce(new Error('register'));
  const { unmount } = render(<PartnerLanding />);
  expect(await screen.findByTestId('stripe-availability')).toHaveTextContent('noch nicht konfiguriert');
  fireEvent.submit(screen.getByTestId('partner-registration-form'));
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('api error'));
  expect(screen.getByText(/Partnerkonto erstellen/)).not.toBeDisabled();
  unmount();
  for (const [role, path] of [['admin', '/admin'], ['partner', '/partner-dashboard'], ['user', '/dashboard']]) {
    mockAuth = { ...mockAuth, user: { role }, loading: false };
    const view = render(<PartnerLanding />);
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith(path));
    await screen.findByTestId('stripe-availability');
    view.unmount();
  }
  mockAuth = { ...mockAuth, user: { role: 'admin' }, loading: true };
  const loadingView = render(<PartnerLanding />);
  await screen.findByTestId('stripe-availability');
  loadingView.unmount();
});

test('partner onboarding loads status, redirects unlocked accounts and starts checkout', async () => {
  const location = { assign: jest.fn() };
  const { unmount } = render(<PartnerOnboarding location={location} />);
  const pay = screen.getByRole('button', { name: /Stripe bezahlen/ });
  expect(pay).toBeDisabled();
  await waitFor(() => expect(pay).not.toBeDisabled());
  fireEvent.click(pay);
  expect(screen.getByText('Weiterleitung…')).toBeInTheDocument();
  await waitFor(() => expect(location.assign).toHaveBeenCalledWith('https://stripe.test'));
  unmount();
  partnerDashboardAPI.getPaymentStatus.mockResolvedValueOnce({ data: { access_unlocked: true } });
  render(<PartnerOnboarding location={location} />);
  await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/partner-dashboard'));
});

test('partner onboarding reports status and checkout errors and re-enables payment', async () => {
  partnerDashboardAPI.getPaymentStatus.mockRejectedValueOnce(new Error('status'));
  const first = render(<PartnerOnboarding />);
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('api error'));
  first.unmount();
  partnerDashboardAPI.createCheckout.mockRejectedValueOnce(new Error('checkout'));
  render(<PartnerOnboarding location={{ assign: jest.fn() }} />);
  const pay = screen.getByRole('button', { name: /Stripe bezahlen/ });
  await waitFor(() => expect(pay).not.toBeDisabled());
  fireEvent.click(pay);
  await waitFor(() => expect(partnerDashboardAPI.createCheckout).toHaveBeenCalled());
  await waitFor(() => expect(pay).not.toBeDisabled());
});

test('payment success handles missing, pending, successful and failed sessions', async () => {
  jest.useFakeTimers();
  mockSessionId = null;
  const missing = render(<PartnerPaymentSuccess />);
  expect(await screen.findByText('Ungültige Rückkehr-URL')).toBeInTheDocument();
  fireEvent.click(screen.getByText('Status prüfen'));
  expect(mockNavigate).toHaveBeenCalledWith('/partner-payment');
  missing.unmount();

  mockSessionId = 'pending';
  partnerDashboardAPI.getPaymentStatus.mockResolvedValueOnce({ data: { access_unlocked: false } });
  const pending = render(<PartnerPaymentSuccess />);
  expect(await screen.findByText(/Stripe verarbeitet/)).toBeInTheDocument();
  pending.unmount();

  mockSessionId = 'success';
  partnerDashboardAPI.getPaymentStatus.mockResolvedValueOnce({ data: { access_unlocked: true } });
  const success = render(<PartnerPaymentSuccess />);
  expect(await screen.findByText(/Zahlung bestätigt/)).toBeInTheDocument();
  expect(mockAuth.checkAuth).toHaveBeenCalled();
  actTimers(1200);
  expect(mockNavigate).toHaveBeenCalledWith('/partner-dashboard');
  success.unmount();

  mockSessionId = 'failed';
  partnerDashboardAPI.getPaymentStatus.mockRejectedValueOnce(new Error('failed'));
  render(<PartnerPaymentSuccess />);
  expect(await screen.findByText('api error')).toBeInTheDocument();
  jest.useRealTimers();
});

function actTimers(milliseconds) {
  const { act } = require('@testing-library/react');
  act(() => jest.advanceTimersByTime(milliseconds));
}
