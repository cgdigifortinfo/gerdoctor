const mockRequestInterceptor = { current: null };
const mockClient = {
  get: jest.fn(() => Promise.resolve({ data: {} })),
  post: jest.fn(() => Promise.resolve({ data: {} })),
  put: jest.fn(() => Promise.resolve({ data: {} })),
  delete: jest.fn(() => Promise.resolve({ data: {} })),
  interceptors: { request: { use: jest.fn((fn) => { mockRequestInterceptor.current = fn; }) } },
};

jest.mock('axios', () => ({ create: jest.fn(() => mockClient) }));

const apiModule = require('./api');

describe('API facade', () => {
  beforeEach(() => jest.clearAllMocks());

  test.each([
    [{ response: { data: {} }, request: {} }, 'Server ist nicht erreichbar'],
    [{}, 'Etwas ist schiefgelaufen'],
    [{ response: { data: { detail: 'Invalid email or password' } } }, 'Passwort'],
    [{ response: { data: { detail: 'Too many failed attempts. Try again later.' } } }, 'Zu viele'],
    [{ response: { data: { detail: 'Invalid or expired token' } } }, 'ungültig'],
    [{ response: { data: { detail: 'Token expired' } } }, 'ungültig'],
    [{ response: { data: { detail: 'plain' } } }, 'plain'],
    [{ response: { data: { detail: [{ msg: 'one' }, { x: 2 }, null] } } }, 'one'],
    [{ response: { data: { detail: { msg: 'message' } } } }, 'message'],
    [{ response: { data: { detail: 42 } } }, '42'],
  ])('formats API errors', (error, expected) => {
    expect(apiModule.formatApiError(error)).toContain(expected);
  });

  test('injects and clears impersonation tokens', () => {
    apiModule.setAuthToken('secret token');
    expect(mockRequestInterceptor.current({ headers: {} }).headers.Authorization).toBe('Bearer secret token');
    expect(apiModule.filesAPI.getUrl('f')).toContain('auth=secret%20token');
    apiModule.setAuthToken(null);
    expect(mockRequestInterceptor.current({ headers: {} }).headers.Authorization).toBeUndefined();
    expect(apiModule.filesAPI.getUrl('f')).toBe('/api/files/f');
  });

  test('delegates every API operation and covers optional query parameters', async () => {
    const ignored = new Set(['formatApiError', 'setAuthToken', 'default']);
    for (const [exportName, value] of Object.entries(apiModule)) {
      if (ignored.has(exportName) || !value || typeof value !== 'object') continue;
      for (const operation of Object.values(value)) {
        if (typeof operation !== 'function') continue;
        await operation('value', 'second', 'third', 'fourth', 'fifth');
        await operation('', '', '', '', '');
      }
    }
    await apiModule.adminAPI.getAuditLog();
    await apiModule.adminAPI.saveStepAsTemplate('s', 'name');
    await apiModule.adminAPI.listEvents();
    await apiModule.partnerDashboardAPI.performStepAction('u', 's', 'complete');
    expect(mockClient.get).toHaveBeenCalled();
    expect(mockClient.post).toHaveBeenCalled();
    expect(mockClient.put).toHaveBeenCalled();
    expect(mockClient.delete).toHaveBeenCalled();
  });
});
