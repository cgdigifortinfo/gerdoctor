import { asArray } from '../../lib/valueNormalization';

export const auditRowKey = (log, absoluteIndex) => `${log.timestamp || 'log'}-${absoluteIndex}`;
export const auditTargetSuffix = (targetId) => targetId ? `#${targetId.slice(-6)}` : '';

export const pendingPartnerCount = (partners) => asArray(partners).filter((partner) => partner.registration_status === 'pending').length;
export const partnerServiceLabel = (partner) => asArray(partner.service_steps)
    .map((step) => `Step ${step.order} ${step.title}`)
    .join(', ') || 'keine Step-Zuordnung';

export function registrationBadge(count, role = 'partner') {
    const total = Number(count) || 0;
    if (role === 'admin') return { kind: 'admin', count: 0, title: '' };
    if (total <= 0) return { kind: 'empty', count: 0, title: '' };
    const title = role === 'partner'
        ? `${total} offene Anmeldung${total === 1 ? '' : 'en'} im Partner-Dashboard`
        : `Gesamtzahl offener Anmeldungen bei allen gewählten Partnern: ${total}`;
    return { kind: 'pending', count: total, title };
}

export const allUsersSelected = (selectedIds, filteredUsers) => filteredUsers.length > 0 && selectedIds.length === filteredUsers.length;
export const userCompletion = (user) => Number(user.completion_pct) || 0;
export const hasItems = (items) => asArray(items).length > 0;
