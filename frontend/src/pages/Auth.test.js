import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ForgotPassword, Login, Register, ResetPassword } from './Auth';
import { authAPI, formatApiError } from '../lib/api';
import { toast } from 'sonner';

const mockNavigate = jest.fn();
let mockSurveySlug;
let mockQuery = {};
const mockLogin = jest.fn();
const mockRegister = jest.fn();
const mockSearchParams = { get: (key) => mockQuery[key] || null };
jest.mock('react-router-dom', () => ({
  Link: ({ children, to, ...props }) => <a href={to} {...props}>{children}</a>, useNavigate: () => mockNavigate,
  useParams: () => ({ surveySlug: mockSurveySlug }), useSearchParams: () => [mockSearchParams],
}), { virtual: true });
jest.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ login: mockLogin, register: mockRegister }) }));
jest.mock('../lib/api', () => ({ authAPI: { forgotPassword: jest.fn(), resetPassword: jest.fn() }, formatApiError: jest.fn(() => 'api error') }));
jest.mock('sonner', () => ({ toast: { success: jest.fn() } }));
jest.mock('@phosphor-icons/react', () => ({ ArrowLeft: () => <i />, Eye: () => <i />, EyeSlash: () => <i /> }));
jest.mock('../components/ui/button', () => ({ Button: ({ children, ...props }) => <button {...props}>{children}</button> }));

beforeEach(() => {
  jest.clearAllMocks();
  mockSurveySlug = undefined;
  mockQuery = {};
  formatApiError.mockReturnValue('api error');
  mockLogin.mockResolvedValue({ role: 'user' });
  mockRegister.mockResolvedValue({});
  authAPI.forgotPassword.mockResolvedValue({});
  authAPI.resetPassword.mockResolvedValue({});
});

function fillLogin() {
  fireEvent.change(screen.getByTestId('login-email-input'), { target: { value: 'ada@example.com' } });
  fireEvent.change(screen.getByTestId('login-password-input'), { target: { value: 'secret' } });
}

test('login renders survey links, reset notice, toggles password and routes all roles', async () => {
  mockSurveySlug = 'pflege'; mockQuery = { passwordReset: 'success' };
  const view = render(<Login />);
  expect(screen.getByTestId('login-reset-success')).toBeInTheDocument();
  expect(screen.getByText('Zurück zur Startseite').closest('a')).toHaveAttribute('href', '/s/pflege');
  expect(screen.getByText('Jetzt registrieren').closest('a')).toHaveAttribute('href', '/s/pflege/register');
  fillLogin();
  const password = screen.getByTestId('login-password-input');
  fireEvent.click(screen.getByLabelText('Passwort anzeigen'));
  expect(password).toHaveAttribute('type', 'text');
  fireEvent.click(screen.getByLabelText('Passwort ausblenden'));
  fireEvent.submit(screen.getByTestId('login-submit-btn').closest('form'));
  expect(screen.getByTestId('login-submit-btn')).toHaveTextContent('Anmeldung...');
  await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/dashboard'));
  expect(toast.success).toHaveBeenCalledWith('Login successful!');
  view.unmount();
  for (const [role, path] of [['admin', '/admin'], ['partner', '/partner-dashboard']]) {
    mockLogin.mockResolvedValueOnce({ role });
    const instance = render(<Login />); fillLogin(); fireEvent.submit(screen.getByTestId('login-submit-btn').closest('form'));
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith(path)); instance.unmount();
  }
});

test('login shows formatted failures and default public links', async () => {
  mockLogin.mockRejectedValueOnce(new Error('bad'));
  render(<Login />); fillLogin();
  fireEvent.submit(screen.getByTestId('login-submit-btn').closest('form'));
  expect(await screen.findByTestId('login-error')).toHaveTextContent('api error');
  expect(screen.getByText('Zurück zur Startseite').closest('a')).toHaveAttribute('href', '/');
  expect(screen.getByText('Jetzt registrieren').closest('a')).toHaveAttribute('href', '/register');
  expect(screen.getByTestId('login-submit-btn')).not.toBeDisabled();
});

function fillRegister(password, confirmation = password) {
  fireEvent.change(screen.getByTestId('register-name-input'), { target: { value: 'Ada' } });
  fireEvent.change(screen.getByTestId('register-email-input'), { target: { value: 'ada@example.com' } });
  fireEvent.change(screen.getByTestId('register-password-input'), { target: { value: password } });
  fireEvent.change(screen.getByTestId('register-confirm-password-input'), { target: { value: confirmation } });
  fireEvent.submit(screen.getByTestId('register-submit-btn').closest('form'));
}

test('register validates mismatch and length then creates a survey-bound account', async () => {
  mockSurveySlug = 'pflege';
  const first = render(<Register />); fillRegister('secret', 'different');
  expect(screen.getByTestId('register-error')).toHaveTextContent('Passwords do not match'); first.unmount();
  const second = render(<Register />); fillRegister('short');
  expect(screen.getByTestId('register-error')).toHaveTextContent('at least 6'); second.unmount();
  render(<Register />);
  fireEvent.click(screen.getByTestId('register-password-input').parentElement.querySelector('button'));
  expect(screen.getByTestId('register-password-input')).toHaveAttribute('type', 'text');
  fireEvent.click(screen.getByTestId('register-password-input').parentElement.querySelector('button'));
  fillRegister('secret');
  expect(screen.getByTestId('register-submit-btn')).toHaveTextContent('Creating account...');
  await waitFor(() => expect(mockRegister).toHaveBeenCalledWith('ada@example.com', 'secret', 'Ada', 'pflege'));
  expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
  expect(screen.getByText('Back to Home').closest('a')).toHaveAttribute('href', '/s/pflege');
});

test('register reports API errors and supports default landing route', async () => {
  mockRegister.mockRejectedValueOnce(new Error('register'));
  render(<Register />); fillRegister('secret');
  expect(await screen.findByTestId('register-error')).toHaveTextContent('api error');
  expect(screen.getByText('Back to Home').closest('a')).toHaveAttribute('href', '/');
  expect(screen.getByTestId('register-submit-btn')).not.toBeDisabled();
});

test('forgot-password shows loading, formatted failures and privacy-preserving success', async () => {
  authAPI.forgotPassword.mockRejectedValueOnce(new Error('forgot'));
  const first = render(<ForgotPassword />);
  fireEvent.change(screen.getByTestId('forgot-email-input'), { target: { value: 'a@b.de' } });
  fireEvent.submit(screen.getByTestId('forgot-submit-btn').closest('form'));
  expect(screen.getByTestId('forgot-submit-btn')).toHaveTextContent('Wird gesendet...');
  expect(await screen.findByTestId('forgot-error')).toHaveTextContent('api error');
  first.unmount();
  render(<ForgotPassword />);
  fireEvent.change(screen.getByTestId('forgot-email-input'), { target: { value: 'a@b.de' } });
  fireEvent.submit(screen.getByTestId('forgot-submit-btn').closest('form'));
  expect(await screen.findByTestId('forgot-success')).toBeInTheDocument();
  expect(screen.getByText(/Falls ein Konto/)).toHaveTextContent('a@b.de');
});

function fillReset(password, confirmation = password) {
  fireEvent.change(screen.getByTestId('reset-password-input'), { target: { value: password } });
  fireEvent.change(screen.getByTestId('reset-confirm-password-input'), { target: { value: confirmation } });
  fireEvent.submit(screen.getByTestId('reset-submit-btn').closest('form'));
}

test('reset-password rejects missing tokens, mismatch and short passwords', () => {
  const missing = render(<ResetPassword />); expect(screen.getByText('Ungültiger Link')).toBeInTheDocument(); missing.unmount();
  mockQuery = { token: 'token' };
  const mismatch = render(<ResetPassword />); fillReset('secret', 'different'); expect(screen.getByTestId('reset-error')).toHaveTextContent('Passwords do not match'); mismatch.unmount();
  render(<ResetPassword />); fillReset('short'); expect(screen.getByTestId('reset-error')).toHaveTextContent('at least 6');
});

test('reset-password handles success and formatted API failure', async () => {
  mockQuery = { token: 'token' };
  const success = render(<ResetPassword />); fillReset('secret');
  expect(screen.getByTestId('reset-submit-btn')).toHaveTextContent('Wird geändert...');
  await waitFor(() => expect(authAPI.resetPassword).toHaveBeenCalledWith('token', 'secret'));
  expect(toast.success).toHaveBeenCalledWith('Passwort erfolgreich geändert.');
  expect(mockNavigate).toHaveBeenCalledWith('/login?passwordReset=success'); success.unmount();
  authAPI.resetPassword.mockRejectedValueOnce(new Error('reset'));
  render(<ResetPassword />); fillReset('secret');
  expect(await screen.findByTestId('reset-error')).toHaveTextContent('api error');
  expect(screen.getByTestId('reset-submit-btn')).not.toBeDisabled();
});
