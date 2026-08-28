import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import AdminDashboard from './AdminDashboard';
import { adminAPI, settingsAPI } from '../lib/api';

const mockNavigate = jest.fn();
const mockLogout = jest.fn();
const mockImpersonate = jest.fn();
let mockAuthUser = { name: 'Admin', permissions: ['*'] };
jest.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
  useLocation: () => ({ search: '' }),
  Link: ({ children, to, ...props }) => <a href={to} {...props}>{children}</a>,
}), { virtual: true });
jest.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ user: mockAuthUser, logout: mockLogout, impersonate: mockImpersonate }) }));
jest.mock('../contexts/LanguageContext', () => ({ useLanguage: () => ({ t: (key) => key }) }));
jest.mock('../lib/api', () => {
  const methods = ['applyStepTemplate','auditStripeConnections','bulkUpdateRole','createPartner','createStep','createSurvey','createUser','deletePartner','deleteStep','deleteStepTemplate','exportUsersCsv','getAnalytics','getAuditLog','getBilling','getCmsContent','getPartners','getPermissionCatalog','getPermissionGroups','getSteps','getSurveys','getUser','getUsers','impersonateUser','linkPartnerUser','listStepTemplates','repairAllStripeConnections','repairStripeConnection','saveStepAsTemplate','saveStepLayout','unlinkPartnerUser','updateCmsContent','updatePartner','updateStep','updateUserPermissions','updateUserProgress','updateUserRole','reorderSteps'];
  return { adminAPI: Object.fromEntries(methods.map((name) => [name, jest.fn()])), settingsAPI: { getAdmin: jest.fn(), update: jest.fn() }, filesAPI: { getUrl: jest.fn((id) => `/files/${id}`) }, formatApiError: jest.fn(() => 'api error') };
});
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock('@phosphor-icons/react', () => new Proxy({}, { get: () => () => <i /> }));
jest.mock('../components/ThemeLangToggle', () => ({ ThemeLangToggle: () => <i /> }));
jest.mock('../components/Logo', () => ({ Logo: () => <i /> }));
jest.mock('../components/ui/button', () => ({ Button: ({ children, asChild, ...props }) => asChild ? <>{children}</> : <button {...props}>{children}</button> }));
jest.mock('../components/ui/select', () => ({ Select: ({ children, onValueChange }) => <div>{children}<button data-testid="select-control" onClick={() => onValueChange?.('value')}>select</button></div>, SelectContent: ({ children }) => <div>{children}</div>, SelectItem: ({ children }) => <span>{children}</span>, SelectTrigger: ({ children, ...props }) => <div {...props}>{children}</div>, SelectValue: () => <i /> }));
jest.mock('../components/ui/switch', () => ({ Switch: ({ checked, onCheckedChange }) => <button onClick={() => onCheckedChange(!checked)}>{String(checked)}</button> }));
jest.mock('../components/ui/checkbox', () => ({ Checkbox: ({ checked, onCheckedChange, ...props }) => <button {...props} onClick={() => onCheckedChange?.(!checked)}>{String(checked)}</button> }));
jest.mock('../components/ui/dialog', () => ({ Dialog: ({ open, children }) => open ? <div>{children}</div> : null, DialogContent: ({ children }) => <div>{children}</div>, DialogHeader: ({ children }) => <div>{children}</div>, DialogTitle: ({ children }) => <h2>{children}</h2> }));
jest.mock('../components/ui/tabs', () => ({ Tabs: ({ children }) => <div>{children}</div>, TabsList: ({ children }) => <div>{children}</div>, TabsTrigger: ({ children, ...props }) => <button {...props}>{children}</button>, TabsContent: ({ children }) => <section>{children}</section> }));
jest.mock('../components/StepsFlowBuilder', () => () => <div data-testid="steps-flow" />);
jest.mock('../components/admin/EmailTemplateEditor', () => () => <div data-testid="email-editor" />);
jest.mock('../components/admin/EventManagement', () => () => <div data-testid="events" />);
jest.mock('../components/admin/SurveyFormBuilder', () => ({ __esModule: true, default: () => <div data-testid="survey-builder" />, CONTENT_FIELD_TYPES: new Set(['heading','paragraph','html','image','divider']) }));
jest.mock('../components/admin/PermissionGroupsManager', () => () => <div data-testid="groups" />);
jest.mock('../components/admin/EntityPickers', () => ({ SearchableMultiSelect: () => <i />, SearchableSelect: () => <i /> }));
jest.mock('../components/PaginationControls', () => ({ usePagination: (items) => ({ paginatedItems: items }), PaginationControls: () => <i /> }));
jest.mock('../components/ui/help-tooltip', () => ({ HelpLabel: ({ children }) => <>{children}</>, HelpTooltip: () => <i /> }));

const response = (data) => Promise.resolve({ data });

beforeEach(() => {
  jest.clearAllMocks();
  mockAuthUser = { name: 'Admin', permissions: ['*'] };
  mockLogout.mockResolvedValue();
  adminAPI.getSurveys.mockReturnValue(response([{ id: 'survey', name: 'Survey', is_default: true }]));
  adminAPI.getUsers.mockReturnValue(response([]));
  adminAPI.getSteps.mockReturnValue(response([]));
  adminAPI.getPartners.mockReturnValue(response([{ id: 'pending', name: 'New', registration_status: 'pending' }]));
  adminAPI.getAnalytics.mockReturnValue(response({ total_users: 0, active_users: 0, completed_users: 0, avg_completion: 0, users_by_role: {}, users_by_status: {}, recent_registrations: [] }));
  adminAPI.getCmsContent.mockImplementation(() => response({ content: {}, translations: {} }));
  adminAPI.getAuditLog.mockReturnValue(response({ logs: [], action_types: [] }));
  adminAPI.listStepTemplates.mockReturnValue(response([]));
  adminAPI.getPermissionGroups.mockReturnValue(response([]));
  adminAPI.getPermissionCatalog.mockReturnValue(response({ categories: [], all_permissions: [] }));
  adminAPI.getBilling.mockReturnValue(response({ partners: [], totals: {} }));
  settingsAPI.getAdmin.mockReturnValue(response({}));
});

test('renders combined tabs when only the secondary permission is granted', async () => {
  mockAuthUser = { name: 'Limited', permissions: ['groups.view', 'surveys.view'] };
  render(<AdminDashboard />); await waitFor(() => expect(screen.queryByText('Loading...')).not.toBeInTheDocument()); expect(screen.getByTestId('admin-users-tab')).toBeInTheDocument(); expect(screen.getByTestId('admin-steps-tab')).toBeInTheDocument();
});

test('loads and renders every permitted admin section and logs out', async () => {
  render(<AdminDashboard />);
  expect(screen.getByText('Loading...')).toBeInTheDocument();
  await waitFor(() => expect(screen.queryByText('Loading...')).not.toBeInTheDocument());
  expect(screen.getByTestId('admin-users-tab')).toBeInTheDocument();
  expect(screen.getByTestId('admin-steps-tab')).toBeInTheDocument();
  expect(screen.getByTestId('admin-partners-tab')).toBeInTheDocument();
  expect(screen.getByTestId('email-editor')).toBeInTheDocument();
  expect(screen.getByTestId('events')).toBeInTheDocument();
  fireEvent.click(screen.getByTestId('admin-logout-btn'));
  await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/'));
});
