import { asArray } from '../../lib/valueNormalization';

export const emptyPartnerForm = () => ({
    name: '', description: '', logo_url: '', website: '', contact_email: '', category: '',
    tags: [], is_active: true, linked_user_ids: [], survey_ids: [], step_user_fee_cents: {},
    stripe_customer_id: '', stripe_subscription_id: '', billing_status: '',
});

export const partnerForm = (partner) => partner ? {
    name: partner.name ?? '', description: partner.description ?? '', logo_url: partner.logo_url ?? '',
    website: partner.website ?? '', contact_email: partner.contact_email ?? '', category: partner.category ?? '',
    tags: asArray(partner.tags), is_active: partner.is_active !== false,
    linked_user_ids: asArray(partner.linked_user_ids), survey_ids: asArray(partner.survey_ids),
    step_user_fee_cents: partner.step_user_fee_cents ?? {}, stripe_customer_id: partner.stripe_customer_id ?? '',
    stripe_subscription_id: partner.stripe_subscription_id ?? '', billing_status: partner.billing_status ?? '',
} : emptyPartnerForm();

export const allPartnerTags = (partners = []) => [...new Set(
    asArray(partners).flatMap(({ tags }) => asArray(tags)),
)].sort();

export const matchingTags = (tags = [], selected = [], input = '') => {
    const query = input.trim().toLocaleLowerCase();
    if (!query) return [];
    return tags.filter((tag) => tag.toLocaleLowerCase().includes(query) && !selected.includes(tag));
};

export const addUniqueTag = (tags = [], tag = '') => {
    const trimmed = tag.trim();
    return trimmed && !tags.includes(trimmed) ? [...tags, trimmed] : tags;
};

export const removeTag = (tags = [], tag = '') => tags.filter((entry) => entry !== tag);

export const toggleId = (ids = [], id = '') => {
    if (!id) return ids;
    return ids.includes(id) ? ids.filter((entry) => entry !== id) : [...ids, id];
};

export const partnerUserCandidates = (users = [], search = '', selectedIds = []) => {
    const query = search.trim().toLocaleLowerCase();
    return users
        .filter(({ role }) => role !== 'admin')
        .filter(({ name, email }) => !query || name.toLocaleLowerCase().includes(query) || email.toLocaleLowerCase().includes(query))
        .sort((left, right) => Number(!selectedIds.includes(left.id)) - Number(!selectedIds.includes(right.id))
            || left.name.localeCompare(right.name, undefined, { sensitivity: 'base' })
            || left.email.localeCompare(right.email));
};

export const inheritedStepFee = (serviceStep = {}, defaultFee = 0) =>
    serviceStep.step_user_fee_cents ?? defaultFee;

export const updateStepFee = (prices = {}, stepId = '', rawValue = '') => {
    const next = { ...prices };
    if (rawValue === '') delete next[stepId];
    else next[stepId] = Number(rawValue);
    return next;
};
