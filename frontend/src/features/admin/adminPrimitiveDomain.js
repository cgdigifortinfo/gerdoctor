const ACTION_COLORS = Object.freeze({
    role_change: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
    step_create: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    step_update: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    step_delete: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
    partner_create: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    partner_update: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    partner_delete: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
    cms_update: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
    bulk_role_change: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
});

export const auditActionPresentation = (action = '') => ({
    label: action ? action.replace(/_/g, ' ') : 'unknown',
    colors: ACTION_COLORS[action] ?? 'bg-gray-100 text-gray-700',
});
