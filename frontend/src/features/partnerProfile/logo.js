export const MAX_PARTNER_LOGO_BYTES = 2 * 1024 * 1024;
export const PARTNER_LOGO_TYPES = ['image/png', 'image/jpeg', 'image/webp'];

export function validatePartnerLogo(file) {
    if (!file) return 'Bitte wählen Sie ein Logo aus.';
    if (!PARTNER_LOGO_TYPES.includes(file.type)) return 'Bitte verwenden Sie PNG, JPEG oder WebP.';
    if (file.size > MAX_PARTNER_LOGO_BYTES) return 'Das Logo darf maximal 2 MB groß sein.';
    return null;
}
