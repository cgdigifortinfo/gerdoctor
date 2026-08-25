// Static editor fixtures stay separate from executable step-domain logic.
export const SIMULATOR_PROFILES = {
    none: { label: 'Keine Simulation', profile: null },
    fresh: {
        label: 'Frischer User',
        profile: { 1: { data: {
            anerkennungsstatus: 'Die Fachsprachenprüfung Medizin ist geplant',
            fachrichtung_gewuenscht: 'Allgemeinmedizin',
            anerkennungsverfahren_bundesland: 'Bayern',
        }, status: 'completed' } },
    },
    upload_path: {
        label: 'Upload-Pfad (Dokumente)',
        profile: {
            1: { data: {
                anerkennungsstatus: 'Die Fachsprachenprüfung Medizin ist geplant',
                fachrichtung_gewuenscht: 'Innere Medizin',
                anerkennungsverfahren_bundesland: 'Berlin',
            }, status: 'completed' },
            2: { data: { decision: 'upload' }, status: 'completed' },
            3: { data: { documents: [{ file_id: 'sim-doc', document_type: 'Diplom', filename: 'diplom.pdf' }] }, status: 'completed' },
        },
    },
    partner_path: {
        label: 'Partner-Pfad',
        profile: {
            1: { data: {
                anerkennungsstatus: 'Die Fachsprachenprüfung Medizin ist geplant',
                fachrichtung_gewuenscht: 'Pädiatrie',
                anerkennungsverfahren_bundesland: 'Hamburg',
            }, status: 'completed' },
            2: { data: { decision: 'partner' }, status: 'completed' },
        },
    },
    already_approbated: {
        label: 'Bereits approbiert',
        profile: { 1: { data: {
            anerkennungsstatus: 'Ich bin in Deutschland approbiert',
            fachrichtung_gewuenscht: 'Kardiologie',
            anerkennungsverfahren_bundesland: 'Berlin',
        }, status: 'completed' } },
    },
};
