export const dialogIsOpen = (value) => Boolean(value);

export const partnerUsers = (users = []) => users.filter(({ role }) => role === 'user');

export const partnerUserFeeCents = (siteSettings = {}) =>
    siteSettings.stripe_partner_user_fee_cents ?? 0;

export const defaultSurveyId = (activeSurveyId = '', surveys = []) => {
    if (activeSurveyId) return activeSurveyId;
    const defaultSurvey = surveys.find(({ is_default }) => is_default);
    return defaultSurvey?.id ?? surveys[0]?.id ?? '';
};
