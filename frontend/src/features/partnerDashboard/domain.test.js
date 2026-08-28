import {
  EMPTY_PARTNER_INSIGHTS, EMPTY_PARTNER_PROFILE, EMPTY_USAGE_BILLING, isPartnerAwaitingAssignment, normalizePartnerBilling,
  normalizePartnerInsights, normalizePartnerProfile,
} from './domain';

test('defines partner activation from the complete assignment contract', () => {
  expect(isPartnerAwaitingAssignment(EMPTY_PARTNER_PROFILE)).toBe(false);
  expect(isPartnerAwaitingAssignment({ linked: true, registration_status: 'active', is_active: true, survey_ids: ['survey'] })).toBe(false);
  expect(isPartnerAwaitingAssignment({ linked: true, registration_status: 'pending', is_active: true, survey_ids: ['survey'] })).toBe(true);
  expect(isPartnerAwaitingAssignment({ linked: true, registration_status: 'active', is_active: false, survey_ids: ['survey'] })).toBe(true);
  expect(isPartnerAwaitingAssignment({ linked: true, registration_status: 'active', is_active: true })).toBe(true);
  expect(isPartnerAwaitingAssignment({ linked: true, registration_status: 'active', is_active: true, survey_ids: [] })).toBe(true);
});

test('normalizes partner API models once', () => {
  expect(normalizePartnerProfile(null)).toEqual(EMPTY_PARTNER_PROFILE);
  expect(normalizePartnerProfile()).toEqual({ linked: true, tags: [], survey_ids: [] });
  expect(normalizePartnerProfile({ tags: ['tag'], survey_ids: ['survey'] })).toEqual({ linked: true, tags: ['tag'], survey_ids: ['survey'] });
  expect(normalizePartnerBilling()).toEqual({ settings: {}, usage: EMPTY_USAGE_BILLING, pricing: [] });
  expect(normalizePartnerBilling({ settings: { enabled: true }, usage: { currency: 'usd' }, pricing: [1] })).toEqual({ settings: { enabled: true }, usage: { currency: 'usd' }, pricing: [1] });
  expect(normalizePartnerInsights(null)).toEqual(EMPTY_PARTNER_INSIGHTS);
  expect(normalizePartnerInsights({ total: 2 })).toEqual({ total: 2, total_linked_users: 0, by_fachrichtung: [], by_bundesland: [], timeline_30d: [], conversion_funnel: { received: 0, accepted: 0, completed: 0 } });
  expect(normalizePartnerInsights({ by_fachrichtung: [1], by_bundesland: [2], timeline_30d: [3], conversion_funnel: { accepted: 4 } })).toEqual({ total_linked_users: 0, by_fachrichtung: [1], by_bundesland: [2], timeline_30d: [3], conversion_funnel: { received: 0, accepted: 4, completed: 0 } });
});
