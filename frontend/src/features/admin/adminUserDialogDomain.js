export const emptyCreateUser = (defaultSurveyId = '', groupIds = []) => ({
    email: '', password: '', name: '', role: 'user', partner_id: 'none',
    survey_id: defaultSurveyId, group_ids: groupIds,
});

export const systemGroupIdsForRole = (groups = [], role = '') =>
    groups.filter((group) => group.role === role && group.is_system === true).map(({ id }) => id);

export const createUserPayload = (formData, canManagePermissions = false) => {
    const data = { ...formData };
    if (data.partner_id === 'none') delete data.partner_id;
    if (data.role !== 'user') delete data.survey_id;
    if (!canManagePermissions) delete data.group_ids;
    return data;
};

export const groupsForRole = (groups = [], role = '') => groups
    .filter((group) => group.role === role)
    .map((group) => ({
        value: group.id,
        label: group.name,
        description: `${group.permissions?.includes('*') ? 'Alle' : group.permissions?.length ?? 0} Rechte`,
    }));

export const activeSurveys = (surveys = []) => surveys.filter(({ is_active }) => is_active === true);

export const sortedPartners = (partners = []) => [...partners]
    .sort((left, right) => left.name.localeCompare(right.name, undefined, { sensitivity: 'base' }));

export const linkedUserCandidates = (users = [], search = '') => {
    const query = search.trim().toLocaleLowerCase();
    return users
        .filter(({ name, email }) => !query || name.toLocaleLowerCase().includes(query) || email.toLocaleLowerCase().includes(query))
        .sort((left, right) => left.name.localeCompare(right.name, undefined, { sensitivity: 'base' }) || left.email.localeCompare(right.email));
};
