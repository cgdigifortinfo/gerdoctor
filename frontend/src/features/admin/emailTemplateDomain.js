import { asString } from '../../lib/valueNormalization';

const COOKIE_MAX_AGE_SECONDS = 31536000;

const DEFAULT_DUMMY = Object.freeze({
    user_name: 'Dr. Maria Mustermann',
    user_email: 'dr.mustermann@chrizz1001.de',
    partner_name: 'ILS Berlin',
    field_of_study: 'Innere Medizin',
    bundesland: 'Berlin',
    step_order: 4,
    step_title: 'Dokumente Antragstellung Approbation',
    step_description: 'Laden Sie die benötigten Nachweise für die Approbation hoch.',
    total_steps: 24,
    milestone_title: 'Antragstellung Approbation',
    rejection_reason: 'Bitte reichen Sie den fehlenden Nachweis erneut ein.',
    reopened_step_title: 'Service Kenntnisprüfung',
    open_user_link: 'https://ihca.de/partner-dashboard?openUser=DEMO-USER-ID',
    reset_link: 'https://ihca.de/reset-password?token=DEMO-TOKEN',
    app_url: 'https://ihca.de',
});

export function readCookie(name, cookie = document.cookie) {
    const match = cookie.split('; ').find(candidate => candidate.startsWith(`${name}=`));
    return match ? decodeURIComponent(match.split('=')[1] || '') : '';
}

export function writeCookie(name, value, target = document) {
    target.cookie = `${name}=${encodeURIComponent(value)}; Max-Age=${COOKIE_MAX_AGE_SECONDS}; Path=/; SameSite=Lax`;
}

const NO_CLIPBOARD = Object.freeze({ writeText: () => undefined });

export const copyTextSafely = (clipboard = NO_CLIPBOARD, text) => Promise.resolve()
    .then(() => clipboard.writeText(text))
    .catch(() => undefined);

export function buildPreviewVariables(users, steps, userId, stepId, origin = window.location.origin) {
    const variables = { ...DEFAULT_DUMMY };
    const user = users.find(item => item.id === userId);
    if (user) {
        variables.user_name = user.name || user.email;
        variables.user_email = user.email;
        variables.partner_name = user.partner_names?.[0] || user.partner_name || variables.partner_name;
        variables.open_user_link = `${origin}/partner-dashboard?openUser=${user.id}`;
    }
    const step = steps.find(item => item.id === stepId);
    if (step) {
        variables.step_title = step.title;
        variables.step_order = step.order;
        variables.step_description = step.description || '';
    }
    return variables;
}

export const parseRecipients = value => asString(value)
    .split(/[,;\n]/)
    .map(recipient => recipient.trim())
    .filter(Boolean);

export const invalidRecipients = recipients => recipients.filter(
    email => !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email),
);

export const renderLayoutPreview = (html, variables) => `<div style="padding:16px;background:#f8fafc;">${
    asString(html).replace(/{{\s*([\w.]+)\s*}}/g, (_, key) => (
        asString(variables[key])
    ))
}</div>`;
