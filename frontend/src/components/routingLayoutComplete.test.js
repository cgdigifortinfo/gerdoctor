import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { ProtectedRoute, PublicRoute } from './ProtectedRoute';
import { Logo } from './Logo';
import { ThemeLangToggle } from './ThemeLangToggle';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { useLanguage } from '../contexts/LanguageContext';

jest.mock('../contexts/AuthContext', () => ({ useAuth: jest.fn() }));
jest.mock('../contexts/ThemeContext', () => ({ useTheme: jest.fn() }));
jest.mock('../contexts/LanguageContext', () => ({ useLanguage: jest.fn() }));
jest.mock('react-router-dom', () => ({
  Navigate: ({ to }) => <span data-testid="navigate">{to}</span>,
  Link: ({ to, children, ...props }) => <a href={to} {...props}>{children}</a>,
}), { virtual: true });

function renderProtected(value, props = {}) {
  useAuth.mockReturnValue(value);
  return render(<ProtectedRoute {...props}><span>protected</span></ProtectedRoute>);
}

function renderPublic(value) {
  useAuth.mockReturnValue(value);
  return render(<PublicRoute><span>public</span></PublicRoute>);
}

test('protected route covers loading, login, role redirects and permission modes', () => {
  let view = renderProtected({ loading: true, user: null });
  expect(screen.getByText('Loading...')).toBeInTheDocument(); view.unmount();
  view = renderProtected({ loading: false, user: null });
  expect(screen.queryByText('protected')).not.toBeInTheDocument(); view.unmount();
  for (const role of ['admin', 'partner', 'user']) {
    view = renderProtected({ loading: false, user: { role } }, { allowedRoles: ['other'] });
    expect(screen.queryByText('protected')).not.toBeInTheDocument(); view.unmount();
  }
  view = renderProtected({ loading: false, user: { role: 'user', permissions: [] } }, { allowedRoles: ['user'], requiredPermission: 'read' });
  expect(screen.getByText('Keine Berechtigung')).toBeInTheDocument(); view.unmount();
  view = renderProtected({ loading: false, user: { role: 'user', permissions: ['*'] } }, { allowedRoles: ['user'], requiredPermission: 'read' });
  expect(screen.getByText('protected')).toBeInTheDocument(); view.unmount();
  view = renderProtected({ loading: false, user: { role: 'user', permissions: ['read'] } });
  expect(screen.getByText('protected')).toBeInTheDocument();
});

test('public route covers loading, anonymous and every role redirect', () => {
  let view = renderPublic({ loading: true, user: null });
  expect(screen.getByText('Loading...')).toBeInTheDocument(); view.unmount();
  view = renderPublic({ loading: false, user: null });
  expect(screen.getByText('public')).toBeInTheDocument(); view.unmount();
  for (const role of ['admin', 'partner', 'user']) {
    view = renderPublic({ loading: false, user: { role } });
    expect(screen.queryByText('public')).not.toBeInTheDocument(); view.unmount();
  }
});

test('logo supports defaults and custom navigation', () => {
  const { rerender } = render(<Logo />);
  expect(screen.getByTestId('logo')).toHaveAttribute('href', '/');
  rerender(<Logo linkTo="/custom" className="custom" />);
  expect(screen.getByTestId('logo')).toHaveAttribute('href', '/custom');
  expect(screen.getByTestId('logo')).toHaveClass('custom');
});

test('theme and language toggle renders both states and delegates clicks', () => {
  const toggleTheme = jest.fn(); const toggleLang = jest.fn();
  useTheme.mockReturnValue({ isDark: false, toggleTheme });
  useLanguage.mockReturnValue({ lang: 'en', toggleLang });
  const { rerender } = render(<ThemeLangToggle />);
  expect(screen.getByTestId('theme-toggle-btn')).toHaveAttribute('title', 'Switch to dark mode');
  expect(screen.getByTestId('lang-toggle-btn')).toHaveTextContent('DE');
  fireEvent.click(screen.getByTestId('theme-toggle-btn')); fireEvent.click(screen.getByTestId('lang-toggle-btn'));
  expect(toggleTheme).toHaveBeenCalled(); expect(toggleLang).toHaveBeenCalled();
  useTheme.mockReturnValue({ isDark: true, toggleTheme });
  useLanguage.mockReturnValue({ lang: 'de', toggleLang });
  rerender(<ThemeLangToggle />);
  expect(screen.getByTestId('theme-toggle-btn')).toHaveAttribute('title', 'Switch to light mode');
  expect(screen.getByTestId('lang-toggle-btn')).toHaveTextContent('EN');
});
