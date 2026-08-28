import {
  allUsersSelected, auditRowKey, auditTargetSuffix, hasItems, partnerServiceLabel,
  pendingPartnerCount, registrationBadge, userCompletion,
} from './adminTabViewModels';

test('builds stable audit presentation values', () => {
  expect(auditRowKey({ timestamp: '2026-01-01' }, 4)).toBe('2026-01-01-4');
  expect(auditRowKey({}, 0)).toBe('log-0');
  expect(auditTargetSuffix('target-12345678')).toBe('#345678');
  expect(auditTargetSuffix('')).toBe('');
});

test('derives partner counts and service labels from normalized collections', () => {
  expect(pendingPartnerCount(undefined)).toBe(0);
  expect(pendingPartnerCount([{ registration_status: 'pending' }, { registration_status: 'active' }, { registration_status: 'pending' }])).toBe(2);
  expect(partnerServiceLabel({})).toBe('keine Step-Zuordnung');
  expect(partnerServiceLabel({ service_steps: [{ order: 2, title: 'Dokumente' }] })).toBe('Step 2 Dokumente');
});

test('derives registration badges for every role and count boundary', () => {
  expect(registrationBadge(3, 'admin')).toEqual({ kind: 'admin', count: 0, title: '' });
  expect(registrationBadge(undefined)).toEqual({ kind: 'empty', count: 0, title: '' });
  expect(registrationBadge(1)).toEqual({ kind: 'pending', count: 1, title: '1 offene Anmeldung im Partner-Dashboard' });
  expect(registrationBadge(2)).toEqual({ kind: 'pending', count: 2, title: '2 offene Anmeldungen im Partner-Dashboard' });
  expect(registrationBadge(4, 'user')).toEqual({ kind: 'pending', count: 4, title: 'Gesamtzahl offener Anmeldungen bei allen gewählten Partnern: 4' });
});

test('derives exact selection, collection and completion states', () => {
  expect(allUsersSelected([], [])).toBe(false);
  expect(allUsersSelected(['1'], [{ id: '1' }])).toBe(true);
  expect(allUsersSelected([], [{ id: '1' }])).toBe(false);
  expect(hasItems(undefined)).toBe(false);
  expect(hasItems(['x'])).toBe(true);
  expect(userCompletion({})).toBe(0);
  expect(userCompletion({ completion_pct: 42 })).toBe(42);
});
