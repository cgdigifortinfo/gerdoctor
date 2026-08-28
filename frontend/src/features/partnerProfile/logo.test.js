import { MAX_PARTNER_LOGO_BYTES, validatePartnerLogo } from './logo';

describe('validatePartnerLogo', () => {
    it('requires a file', () => expect(validatePartnerLogo(null)).toMatch('aus'));
    it('rejects unsupported file types', () => {
        expect(validatePartnerLogo({ type: 'image/svg+xml', size: 10 })).toMatch('PNG');
    });
    it('rejects files larger than 2 MB', () => {
        expect(validatePartnerLogo({ type: 'image/png', size: MAX_PARTNER_LOGO_BYTES + 1 })).toMatch('2 MB');
    });
    it('accepts supported images within the limit', () => {
        expect(validatePartnerLogo({ type: 'image/webp', size: 100 })).toBeNull();
        expect(validatePartnerLogo({ type: 'image/jpeg', size: 100 })).toBeNull();
        expect(validatePartnerLogo({ type: 'image/png', size: MAX_PARTNER_LOGO_BYTES })).toBeNull();
    });
});
