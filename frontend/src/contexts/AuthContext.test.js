import React from 'react';
import { act, renderHook, waitFor } from '@testing-library/react';
import axios from 'axios';
import { AuthProvider, useAuth } from './AuthContext';
import { setAuthToken } from '../lib/api';

jest.mock('axios', () => ({ get: jest.fn(), post: jest.fn() }));
jest.mock('../lib/api', () => ({ setAuthToken: jest.fn() }));

const wrapper = ({ children }) => <AuthProvider>{children}</AuthProvider>;

beforeEach(() => {
  jest.clearAllMocks();
  sessionStorage.clear();
  axios.get.mockResolvedValue({ data: { id: 'admin', role: 'admin' } });
  axios.post.mockResolvedValue({ data: {} });
});

test('checks an existing session and exposes every account operation', async () => {
  const { result } = renderHook(() => useAuth(), { wrapper });
  await waitFor(() => expect(result.current.loading).toBe(false));
  expect(result.current.user.role).toBe('admin');

  axios.post.mockResolvedValueOnce({ data: { access_token: 'login-token', role: 'user' } });
  await act(async () => expect(await result.current.login('u@test', 'pw')).toEqual({ access_token: 'login-token', role: 'user' }));
  expect(setAuthToken).toHaveBeenCalledWith('login-token');

  axios.post.mockResolvedValueOnce({ data: { role: 'user' } });
  await act(async () => result.current.login('u@test', 'pw'));
  axios.post.mockResolvedValueOnce({ data: { access_token: 'register-token', role: 'user' } });
  await act(async () => result.current.register('u@test', 'pw', 'User', 'survey'));
  axios.post.mockResolvedValueOnce({ data: { role: 'user' } });
  await act(async () => result.current.register('u@test', 'pw', 'User', null));

  await act(async () => result.current.impersonate('target-token', { id: 'target', role: 'partner' }));
  expect(result.current.impersonating).toBe(true);
  expect(sessionStorage.getItem('impersonate_token')).toBe('target-token');
  act(() => result.current.stopImpersonation());
  expect(result.current.impersonating).toBe(false);

  axios.get.mockResolvedValueOnce({ data: { id: 'refreshed' } });
  await act(async () => result.current.refreshToken());
  expect(result.current.user.id).toBe('refreshed');

  await act(async () => result.current.logout());
  expect(result.current.user).toBe(false);
  expect(setAuthToken).toHaveBeenLastCalledWith(null);
});

test('refreshes an expired cookie during initial authentication', async () => {
  axios.get.mockRejectedValueOnce({ response: { status: 401 } }).mockResolvedValueOnce({ data: { id: 'after-refresh' } });
  const { result } = renderHook(() => useAuth(), { wrapper });
  await waitFor(() => expect(result.current.loading).toBe(false));
  expect(result.current.user.id).toBe('after-refresh');
  expect(axios.post).toHaveBeenCalledWith('/api/auth/refresh', {}, { withCredentials: true });
});

test('clears auth when refresh or ordinary authentication fails', async () => {
  axios.get.mockRejectedValueOnce({ response: { status: 401 } });
  axios.post.mockRejectedValueOnce(new Error('refresh failed'));
  const first = renderHook(() => useAuth(), { wrapper });
  await waitFor(() => expect(first.result.current.loading).toBe(false));
  expect(first.result.current.user).toBe(false);
  first.unmount();

  axios.get.mockRejectedValueOnce(new Error('offline'));
  const second = renderHook(() => useAuth(), { wrapper });
  await waitFor(() => expect(second.result.current.loading).toBe(false));
  expect(second.result.current.user).toBe(false);
});

test('restores valid impersonation state with and without its target token', async () => {
  sessionStorage.setItem('admin_impersonate', JSON.stringify({ token: 'admin-token', user: { role: 'admin' } }));
  sessionStorage.setItem('impersonate_token', 'target-token');
  const first = renderHook(() => useAuth(), { wrapper });
  await waitFor(() => expect(first.result.current.loading).toBe(false));
  expect(first.result.current.impersonating).toBe(true);
  expect(setAuthToken).toHaveBeenCalledWith('target-token');
  first.unmount();

  jest.clearAllMocks(); sessionStorage.clear();
  sessionStorage.setItem('admin_impersonate', JSON.stringify({ token: 'admin-token', user: { role: 'admin' } }));
  axios.get.mockResolvedValue({ data: { role: 'admin' } });
  const second = renderHook(() => useAuth(), { wrapper });
  await waitFor(() => expect(second.result.current.loading).toBe(false));
  expect(second.result.current.impersonating).toBe(true);
});

test('ignores malformed impersonation state and tolerates logout and refresh failures', async () => {
  sessionStorage.setItem('admin_impersonate', '{invalid');
  const { result } = renderHook(() => useAuth(), { wrapper });
  await waitFor(() => expect(result.current.loading).toBe(false));
  expect(result.current.impersonating).toBe(false);
  axios.post.mockRejectedValueOnce(new Error('logout failed'));
  await act(async () => result.current.logout());
  axios.post.mockRejectedValueOnce(new Error('refresh failed'));
  await act(async () => result.current.refreshToken());
  expect(result.current.user).toBe(false);
});

test('requires an AuthProvider', () => {
  const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
  expect(() => renderHook(() => useAuth())).toThrow('useAuth must be used within AuthProvider');
  spy.mockRestore();
});
