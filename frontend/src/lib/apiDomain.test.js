import { auditLogQuery, eventsQuery, formatApiError, userSearchQuery } from './apiDomain';

test('formatApiError handles transport, authentication, validation and fallback details', () => {
  expect(formatApiError({ request: {} })).toContain('nicht erreichbar');
  expect(formatApiError({ response: {}, request: {} })).toContain('nicht erreichbar');
  expect(formatApiError()).toContain('schiefgelaufen');
  expect(formatApiError({ response: { data: { detail: 'Invalid email or password' } } })).toContain('Passwort');
  expect(formatApiError({ response: { data: { detail: 'Too many failed attempts. Try again later.' } } })).toContain('Versuche');
  expect(formatApiError({ response: { data: { detail: 'Invalid or expired token' } } })).toContain('abgelaufen');
  expect(formatApiError({ response: { data: { detail: 'Token expired' } } })).toContain('abgelaufen');
  expect(formatApiError({ response: { data: { detail: 'Custom' } } })).toBe('Custom');
  expect(formatApiError({ response: { data: { detail: [{ msg: 'First' }, { code: 2 }, null] } } })).toBe('First {"code":2} null');
  expect(formatApiError({ response: { data: { detail: [undefined, { msg: 'Only' }] } } })).toBe('Only');
  expect(formatApiError({ response: { data: { detail: { msg: 'Object message' } } } })).toBe('Object message');
  expect(formatApiError({ response: { data: { detail: 42 } } })).toBe('42');
});

test('query builders encode provided values and omit empty filters', () => {
  expect(userSearchQuery('A B', 'partner/admin')).toBe('q=A%20B&role=partner%2Fadmin');
  expect(userSearchQuery()).toBe('q=&role=');
  expect(auditLogQuery()).toBe('limit=100&skip=0');
  expect(auditLogQuery(5, 2, 'login', '2026-01-01', '2026-02-01')).toBe('limit=5&skip=2&action=login&date_from=2026-01-01&date_to=2026-02-01');
  expect(eventsQuery()).toBe('limit=0');
  expect(eventsQuery(10, 'mail.sent', 'failed')).toBe('limit=10&event_type=mail.sent&status=failed');
});
