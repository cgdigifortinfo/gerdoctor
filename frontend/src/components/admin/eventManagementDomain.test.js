import {
  appendEventHandler, filterEvents, nonLayoutTemplates, toggleChannel, updateEventConfig, updateEventHandler,
} from './eventManagementDomain';

const configs = [
  { event_type: 'created', enabled: true, handlers: [{ id: 'mail', enabled: true }] },
  { event_type: 'done', enabled: true },
];

test('normalizes templates and immutably updates event configurations', () => {
  expect(nonLayoutTemplates(undefined)).toEqual([]);
  expect(nonLayoutTemplates([{ key: 'layout', category: 'layout' }, { key: 'welcome', category: 'user' }])).toEqual([{ key: 'welcome', category: 'user' }]);
  expect(updateEventConfig(configs, 'created', (config) => ({ ...config, enabled: false }))[0].enabled).toBe(false);
  expect(updateEventConfig(configs, 'missing', (config) => ({ ...config, enabled: false }))).toEqual(configs);
  expect(updateEventHandler(configs, 'created', 'mail', { enabled: false })[0].handlers[0].enabled).toBe(false);
  expect(updateEventHandler(configs, 'created', 'missing', { enabled: false })[0].handlers[0].enabled).toBe(true);
});

test('builds each handler type with explicit defaults', () => {
  const email = appendEventHandler(configs, 'done', 'email', 'welcome', 'email-1')[1].handlers[0];
  expect(email).toEqual({ id: 'email-1', type: 'email', label: 'User per E-Mail informieren', enabled: true, recipient: 'user', template_key: 'welcome' });
  const notification = appendEventHandler(configs, 'done', 'notification', '', 'notification-1')[1].handlers[0];
  expect(notification).toEqual({ id: 'notification-1', type: 'notification', label: 'Browser/App Notification', enabled: false, recipient: 'user', template_key: '', channels: ['browser', 'app'], provider: 'unconfigured' });
});

test('filters both dimensions and toggles unique channels', () => {
  const events = [{ event_type: 'created', status: 'failed' }, { event_type: 'done', status: 'processed' }];
  expect(filterEvents(events, 'all', 'all')).toEqual(events);
  expect(filterEvents(events, 'created', 'all')).toEqual([events[0]]);
  expect(filterEvents(events, 'all', 'processed')).toEqual([events[1]]);
  expect(filterEvents(events, 'created', 'processed')).toEqual([]);
  expect(toggleChannel(undefined, 'browser', true)).toEqual(['browser']);
  expect(toggleChannel(['browser'], 'browser', true)).toEqual(['browser']);
  expect(toggleChannel(['browser', 'app'], 'browser', false)).toEqual(['app']);
});
