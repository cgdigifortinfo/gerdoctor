export const EMPTY_USAGE_BILLING = Object.freeze({
    pending_users: 0,
    pending_amount: 0,
    billed_users: 0,
    billed_amount: 0,
    currency: 'eur',
});

export const EMPTY_PARTNER_PROFILE = Object.freeze({ linked: false, tags: [], survey_ids: [] });
export const EMPTY_PARTNER_INSIGHTS = Object.freeze({
    total_linked_users: 0,
    by_fachrichtung: [],
    by_bundesland: [],
    timeline_30d: [],
    conversion_funnel: Object.freeze({ received: 0, accepted: 0, completed: 0 }),
});

export function isPartnerAwaitingAssignment(profile) {
    if (!profile.linked) return false;
    return profile.registration_status !== 'active'
        || profile.is_active !== true
        || !Array.isArray(profile.survey_ids)
        || profile.survey_ids.length === 0;
}

export function normalizePartnerProfile(profile) {
    if (profile === null) return { ...EMPTY_PARTNER_PROFILE };
    const source = profile ?? {};
    return { ...source, linked: true, tags: source.tags ?? [], survey_ids: source.survey_ids ?? [] };
}

export function normalizePartnerBilling(response) {
    const source = response ?? {};
    return {
        settings: source.settings ?? {},
        usage: source.usage ?? { ...EMPTY_USAGE_BILLING },
        pricing: source.pricing ?? [],
    };
}

export function normalizePartnerInsights(insights) {
    if (!insights) return { ...EMPTY_PARTNER_INSIGHTS, conversion_funnel: { ...EMPTY_PARTNER_INSIGHTS.conversion_funnel } };
    return {
        ...insights,
        total_linked_users: insights.total_linked_users ?? 0,
        by_fachrichtung: insights.by_fachrichtung ?? [],
        by_bundesland: insights.by_bundesland ?? [],
        timeline_30d: insights.timeline_30d ?? [],
        conversion_funnel: { ...EMPTY_PARTNER_INSIGHTS.conversion_funnel, ...insights.conversion_funnel },
    };
}
