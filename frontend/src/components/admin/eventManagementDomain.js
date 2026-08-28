import { asArray } from '../../lib/valueNormalization';

export const nonLayoutTemplates = (templates) => asArray(templates).filter((template) => template.category !== 'layout');

export const updateEventConfig = (configs, eventType, updater) => configs.map((config) => (
    config.event_type === eventType ? updater(config) : config
));

export const updateEventHandler = (configs, eventType, handlerId, patch) => updateEventConfig(
    configs,
    eventType,
    (config) => ({
        ...config,
        handlers: asArray(config.handlers).map((handler) => handler.id === handlerId ? { ...handler, ...patch } : handler),
    }),
);

export function appendEventHandler(configs, eventType, type, templateKey, id) {
    const handler = {
        id,
        type,
        label: type === 'email' ? 'User per E-Mail informieren' : 'Browser/App Notification',
        enabled: type === 'email',
        recipient: 'user',
        template_key: templateKey,
        ...(type === 'notification' ? { channels: ['browser', 'app'], provider: 'unconfigured' } : {}),
    };
    return updateEventConfig(configs, eventType, (config) => ({ ...config, handlers: [...asArray(config.handlers), handler] }));
}

export const filterEvents = (events, eventType, status) => events.filter((event) => (
    (eventType === 'all' || event.event_type === eventType)
    && (status === 'all' || event.status === status)
));

export function toggleChannel(channels, channel, checked) {
    const current = asArray(channels);
    return checked ? [...new Set([...current, channel])] : current.filter((value) => value !== channel);
}
