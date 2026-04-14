import { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { adminAPI, formatApiError } from '../lib/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Switch } from '../components/ui/switch';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { 
    SignOut, Users, ListChecks, Buildings, Plus, Pencil, Trash, 
    Eye, X, CaretDown, CaretUp
} from '@phosphor-icons/react';
import { toast } from 'sonner';

export default function AdminDashboard() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState('users');
    const [users, setUsers] = useState([]);
    const [steps, setSteps] = useState([]);
    const [partners, setPartners] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedUser, setSelectedUser] = useState(null);
    const [editingStep, setEditingStep] = useState(null);
    const [editingPartner, setEditingPartner] = useState(null);
    const [showStepDialog, setShowStepDialog] = useState(false);
    const [showPartnerDialog, setShowPartnerDialog] = useState(false);
    const [showUserDialog, setShowUserDialog] = useState(false);

    const loadData = useCallback(async () => {
        try {
            const [usersRes, stepsRes, partnersRes] = await Promise.all([
                adminAPI.getUsers(),
                adminAPI.getSteps(),
                adminAPI.getPartners()
            ]);
            setUsers(usersRes.data);
            setSteps(stepsRes.data);
            setPartners(partnersRes.data);
        } catch (error) {
            toast.error('Failed to load data');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadData();
    }, [loadData]);

    const handleLogout = async () => {
        await logout();
        navigate('/');
    };

    const handleViewUser = async (userId) => {
        try {
            const response = await adminAPI.getUser(userId);
            setSelectedUser(response.data);
            setShowUserDialog(true);
        } catch (error) {
            toast.error('Failed to load user details');
        }
    };

    const handleUpdateUserRole = async (userId, role) => {
        try {
            await adminAPI.updateUserRole(userId, role);
            toast.success('User role updated');
            loadData();
        } catch (error) {
            toast.error(formatApiError(error));
        }
    };

    // Step Management
    const handleSaveStep = async (stepData) => {
        try {
            if (editingStep?.id) {
                await adminAPI.updateStep(editingStep.id, stepData);
                toast.success('Step updated');
            } else {
                await adminAPI.createStep(stepData);
                toast.success('Step created');
            }
            setShowStepDialog(false);
            setEditingStep(null);
            loadData();
        } catch (error) {
            toast.error(formatApiError(error));
        }
    };

    const handleDeleteStep = async (stepId) => {
        if (!window.confirm('Are you sure you want to delete this step?')) return;
        try {
            await adminAPI.deleteStep(stepId);
            toast.success('Step deleted');
            loadData();
        } catch (error) {
            toast.error(formatApiError(error));
        }
    };

    // Partner Management
    const handleSavePartner = async (partnerData) => {
        try {
            if (editingPartner?.id) {
                await adminAPI.updatePartner(editingPartner.id, partnerData);
                toast.success('Partner updated');
            } else {
                await adminAPI.createPartner(partnerData);
                toast.success('Partner created');
            }
            setShowPartnerDialog(false);
            setEditingPartner(null);
            loadData();
        } catch (error) {
            toast.error(formatApiError(error));
        }
    };

    const handleDeletePartner = async (partnerId) => {
        if (!window.confirm('Are you sure you want to delete this partner?')) return;
        try {
            await adminAPI.deletePartner(partnerId);
            toast.success('Partner deleted');
            loadData();
        } catch (error) {
            toast.error(formatApiError(error));
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-[#FAFAFA] flex items-center justify-center">
                <div className="text-[#52525B]">Loading...</div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[#FAFAFA]">
            {/* Header */}
            <header className="sticky top-0 z-50 glass">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        <div className="flex items-center gap-4">
                            <Link to="/" className="font-black text-xl tracking-tight text-[#0A0A0A]">
                                GuidedJourney
                            </Link>
                            <span className="text-xs font-bold tracking-wider uppercase text-[#002FA7] px-2 py-1 bg-blue-50 rounded">
                                Admin
                            </span>
                        </div>
                        <div className="flex items-center gap-4">
                            <span className="text-sm text-[#52525B] hidden sm:block">
                                {user?.name}
                            </span>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={handleLogout}
                                className="text-[#52525B]"
                                data-testid="admin-logout-btn"
                            >
                                <SignOut size={20} />
                            </Button>
                        </div>
                    </div>
                </div>
            </header>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Tabs value={activeTab} onValueChange={setActiveTab}>
                    <TabsList className="mb-6 bg-white border border-[#E4E4E7]">
                        <TabsTrigger value="users" className="data-[state=active]:bg-[#002FA7] data-[state=active]:text-white">
                            <Users size={18} className="mr-2" />
                            Users
                        </TabsTrigger>
                        <TabsTrigger value="steps" className="data-[state=active]:bg-[#002FA7] data-[state=active]:text-white">
                            <ListChecks size={18} className="mr-2" />
                            Steps
                        </TabsTrigger>
                        <TabsTrigger value="partners" className="data-[state=active]:bg-[#002FA7] data-[state=active]:text-white">
                            <Buildings size={18} className="mr-2" />
                            Partners
                        </TabsTrigger>
                    </TabsList>

                    {/* Users Tab */}
                    <TabsContent value="users">
                        <div className="bg-white border border-[#E4E4E7] rounded-sm">
                            <div className="p-4 border-b border-[#E4E4E7]">
                                <h2 className="text-lg font-semibold text-[#0A0A0A]">User Management</h2>
                            </div>
                            <div className="overflow-x-auto">
                                <table className="w-full">
                                    <thead className="bg-[#FAFAFA]">
                                        <tr>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-[#52525B]">Name</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-[#52525B]">Email</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-[#52525B]">Role</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-[#52525B]">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {users.map((u) => (
                                            <tr key={u.id} className="border-t border-[#E4E4E7] table-row-hover">
                                                <td className="px-4 py-3 text-sm text-[#0A0A0A]">{u.name}</td>
                                                <td className="px-4 py-3 text-sm text-[#52525B]">{u.email}</td>
                                                <td className="px-4 py-3">
                                                    <Select 
                                                        value={u.role} 
                                                        onValueChange={(val) => handleUpdateUserRole(u.id, val)}
                                                    >
                                                        <SelectTrigger className="w-32 h-8 text-xs border-[#E4E4E7]">
                                                            <SelectValue />
                                                        </SelectTrigger>
                                                        <SelectContent>
                                                            <SelectItem value="user">User</SelectItem>
                                                            <SelectItem value="admin">Admin</SelectItem>
                                                            <SelectItem value="partner">Partner</SelectItem>
                                                        </SelectContent>
                                                    </Select>
                                                </td>
                                                <td className="px-4 py-3">
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={() => handleViewUser(u.id)}
                                                        data-testid={`view-user-${u.id}`}
                                                    >
                                                        <Eye size={18} />
                                                    </Button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </TabsContent>

                    {/* Steps Tab */}
                    <TabsContent value="steps">
                        <div className="bg-white border border-[#E4E4E7] rounded-sm">
                            <div className="p-4 border-b border-[#E4E4E7] flex justify-between items-center">
                                <h2 className="text-lg font-semibold text-[#0A0A0A]">Step Management</h2>
                                <Button
                                    onClick={() => {
                                        setEditingStep(null);
                                        setShowStepDialog(true);
                                    }}
                                    className="bg-[#002FA7] hover:bg-[#002280] text-white"
                                    data-testid="add-step-btn"
                                >
                                    <Plus size={18} className="mr-2" />
                                    Add Step
                                </Button>
                            </div>
                            <div className="p-4 space-y-4">
                                {steps.sort((a, b) => a.order - b.order).map((step) => (
                                    <div key={step.id} className="border border-[#E4E4E7] rounded-sm p-4">
                                        <div className="flex justify-between items-start">
                                            <div>
                                                <div className="flex items-center gap-2">
                                                    <span className="w-8 h-8 rounded-full bg-[#002FA7] text-white flex items-center justify-center text-sm font-bold">
                                                        {step.order}
                                                    </span>
                                                    <h3 className="font-semibold text-[#0A0A0A]">{step.title}</h3>
                                                    <span className={`px-2 py-0.5 text-xs rounded-sm ${
                                                        step.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                                                    }`}>
                                                        {step.is_active ? 'Active' : 'Inactive'}
                                                    </span>
                                                </div>
                                                <p className="text-sm text-[#52525B] mt-1 ml-10">{step.description}</p>
                                                <div className="flex gap-4 mt-2 ml-10 text-xs text-[#52525B]">
                                                    <span>Type: {step.step_type}</span>
                                                    <span>Fields: {step.fields?.length || 0}</span>
                                                </div>
                                            </div>
                                            <div className="flex gap-2">
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => {
                                                        setEditingStep(step);
                                                        setShowStepDialog(true);
                                                    }}
                                                    data-testid={`edit-step-${step.id}`}
                                                >
                                                    <Pencil size={18} />
                                                </Button>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => handleDeleteStep(step.id)}
                                                    className="text-red-500 hover:text-red-700"
                                                    data-testid={`delete-step-${step.id}`}
                                                >
                                                    <Trash size={18} />
                                                </Button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </TabsContent>

                    {/* Partners Tab */}
                    <TabsContent value="partners">
                        <div className="bg-white border border-[#E4E4E7] rounded-sm">
                            <div className="p-4 border-b border-[#E4E4E7] flex justify-between items-center">
                                <h2 className="text-lg font-semibold text-[#0A0A0A]">Partner Management</h2>
                                <Button
                                    onClick={() => {
                                        setEditingPartner(null);
                                        setShowPartnerDialog(true);
                                    }}
                                    className="bg-[#002FA7] hover:bg-[#002280] text-white"
                                    data-testid="add-partner-btn"
                                >
                                    <Plus size={18} className="mr-2" />
                                    Add Partner
                                </Button>
                            </div>
                            <div className="overflow-x-auto">
                                <table className="w-full">
                                    <thead className="bg-[#FAFAFA]">
                                        <tr>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-[#52525B]">Partner</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-[#52525B]">Category</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-[#52525B]">Status</th>
                                            <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-[#52525B]">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {partners.map((partner) => (
                                            <tr key={partner.id} className="border-t border-[#E4E4E7] table-row-hover">
                                                <td className="px-4 py-3">
                                                    <div className="flex items-center gap-3">
                                                        {partner.logo_url && (
                                                            <img src={partner.logo_url} alt="" className="w-10 h-10 rounded-sm object-cover" />
                                                        )}
                                                        <div>
                                                            <p className="font-medium text-[#0A0A0A]">{partner.name}</p>
                                                            <p className="text-xs text-[#52525B]">{partner.contact_email}</p>
                                                        </div>
                                                    </div>
                                                </td>
                                                <td className="px-4 py-3 text-sm text-[#52525B]">{partner.category || '-'}</td>
                                                <td className="px-4 py-3">
                                                    <span className={`px-2 py-1 text-xs rounded-sm ${
                                                        partner.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                                                    }`}>
                                                        {partner.is_active ? 'Active' : 'Inactive'}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-3">
                                                    <div className="flex gap-2">
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => {
                                                                setEditingPartner(partner);
                                                                setShowPartnerDialog(true);
                                                            }}
                                                            data-testid={`edit-partner-${partner.id}`}
                                                        >
                                                            <Pencil size={18} />
                                                        </Button>
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => handleDeletePartner(partner.id)}
                                                            className="text-red-500 hover:text-red-700"
                                                            data-testid={`delete-partner-${partner.id}`}
                                                        >
                                                            <Trash size={18} />
                                                        </Button>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </TabsContent>
                </Tabs>
            </div>

            {/* User Detail Dialog */}
            <Dialog open={showUserDialog} onOpenChange={setShowUserDialog}>
                <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle>User Details</DialogTitle>
                    </DialogHeader>
                    {selectedUser && (
                        <div className="space-y-6">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <Label className="text-[#52525B]">Name</Label>
                                    <p className="font-medium">{selectedUser.name}</p>
                                </div>
                                <div>
                                    <Label className="text-[#52525B]">Email</Label>
                                    <p className="font-medium">{selectedUser.email}</p>
                                </div>
                                <div>
                                    <Label className="text-[#52525B]">Role</Label>
                                    <p className="font-medium capitalize">{selectedUser.role}</p>
                                </div>
                                <div>
                                    <Label className="text-[#52525B]">Created</Label>
                                    <p className="font-medium">{selectedUser.created_at ? new Date(selectedUser.created_at).toLocaleDateString() : '-'}</p>
                                </div>
                            </div>

                            <div>
                                <h4 className="font-semibold mb-3">Progress</h4>
                                <div className="space-y-2">
                                    {selectedUser.progress?.map((p) => {
                                        const step = steps.find(s => s.id === p.step_id);
                                        return (
                                            <div key={p.step_id} className="flex items-center justify-between p-3 bg-[#FAFAFA] rounded-sm">
                                                <span>{step?.title || 'Unknown Step'}</span>
                                                <span className={`px-2 py-1 text-xs rounded-sm ${
                                                    p.status === 'completed' ? 'badge-completed' :
                                                    p.status === 'in_progress' ? 'badge-in-progress' : 'badge-pending'
                                                }`}>
                                                    {p.status}
                                                </span>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>

                            {selectedUser.submissions?.length > 0 && (
                                <div>
                                    <h4 className="font-semibold mb-3">Partner Submissions</h4>
                                    <div className="space-y-2">
                                        {selectedUser.submissions.map((sub) => {
                                            const partner = partners.find(p => p.id === sub.partner_id);
                                            return (
                                                <div key={sub.id} className="p-3 bg-[#FAFAFA] rounded-sm">
                                                    <p className="font-medium">{partner?.name || 'Unknown Partner'}</p>
                                                    <p className="text-sm text-[#52525B]">
                                                        Submitted: {new Date(sub.created_at).toLocaleDateString()}
                                                    </p>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </DialogContent>
            </Dialog>

            {/* Step Edit Dialog */}
            <StepDialog
                open={showStepDialog}
                onClose={() => {
                    setShowStepDialog(false);
                    setEditingStep(null);
                }}
                step={editingStep}
                onSave={handleSaveStep}
                existingSteps={steps}
            />

            {/* Partner Edit Dialog */}
            <PartnerDialog
                open={showPartnerDialog}
                onClose={() => {
                    setShowPartnerDialog(false);
                    setEditingPartner(null);
                }}
                partner={editingPartner}
                onSave={handleSavePartner}
            />
        </div>
    );
}

// Step Dialog Component
function StepDialog({ open, onClose, step, onSave, existingSteps }) {
    const [formData, setFormData] = useState({
        title: '',
        description: '',
        order: existingSteps.length + 1,
        step_type: 'form',
        fields: [],
        email_on_enter: false,
        email_on_edit: false,
        email_on_leave: false,
        is_active: true
    });
    const [showFieldForm, setShowFieldForm] = useState(false);
    const [editingField, setEditingField] = useState(null);

    useEffect(() => {
        if (step) {
            setFormData({
                title: step.title || '',
                description: step.description || '',
                order: step.order || existingSteps.length + 1,
                step_type: step.step_type || 'form',
                fields: step.fields || [],
                email_on_enter: step.email_on_enter || false,
                email_on_edit: step.email_on_edit || false,
                email_on_leave: step.email_on_leave || false,
                is_active: step.is_active !== false
            });
        } else {
            setFormData({
                title: '',
                description: '',
                order: existingSteps.length + 1,
                step_type: 'form',
                fields: [],
                email_on_enter: false,
                email_on_edit: false,
                email_on_leave: false,
                is_active: true
            });
        }
    }, [step, existingSteps.length]);

    const handleSubmit = (e) => {
        e.preventDefault();
        onSave(formData);
    };

    const handleAddField = (field) => {
        if (editingField !== null) {
            const newFields = [...formData.fields];
            newFields[editingField] = field;
            setFormData({ ...formData, fields: newFields });
            setEditingField(null);
        } else {
            setFormData({ ...formData, fields: [...formData.fields, field] });
        }
        setShowFieldForm(false);
    };

    const handleRemoveField = (index) => {
        setFormData({ ...formData, fields: formData.fields.filter((_, i) => i !== index) });
    };

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>{step ? 'Edit Step' : 'Create Step'}</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="col-span-2">
                            <Label>Title</Label>
                            <Input
                                value={formData.title}
                                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                                className="mt-1"
                                required
                                data-testid="step-title-input"
                            />
                        </div>
                        <div className="col-span-2">
                            <Label>Description</Label>
                            <Textarea
                                value={formData.description}
                                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                className="mt-1"
                                required
                                data-testid="step-description-input"
                            />
                        </div>
                        <div>
                            <Label>Order</Label>
                            <Input
                                type="number"
                                min="1"
                                value={formData.order}
                                onChange={(e) => setFormData({ ...formData, order: parseInt(e.target.value) })}
                                className="mt-1"
                                required
                                data-testid="step-order-input"
                            />
                        </div>
                        <div>
                            <Label>Type</Label>
                            <Select value={formData.step_type} onValueChange={(val) => setFormData({ ...formData, step_type: val })}>
                                <SelectTrigger className="mt-1" data-testid="step-type-select">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="form">Form</SelectItem>
                                    <SelectItem value="partner_selection">Partner Selection</SelectItem>
                                    <SelectItem value="info">Information</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    {/* Email Notifications */}
                    <div className="space-y-3">
                        <Label>Email Notifications</Label>
                        <div className="space-y-2">
                            <div className="flex items-center justify-between">
                                <span className="text-sm">On entering step</span>
                                <Switch
                                    checked={formData.email_on_enter}
                                    onCheckedChange={(val) => setFormData({ ...formData, email_on_enter: val })}
                                />
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm">On editing step</span>
                                <Switch
                                    checked={formData.email_on_edit}
                                    onCheckedChange={(val) => setFormData({ ...formData, email_on_edit: val })}
                                />
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm">On leaving step</span>
                                <Switch
                                    checked={formData.email_on_leave}
                                    onCheckedChange={(val) => setFormData({ ...formData, email_on_leave: val })}
                                />
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center justify-between">
                        <Label>Active</Label>
                        <Switch
                            checked={formData.is_active}
                            onCheckedChange={(val) => setFormData({ ...formData, is_active: val })}
                        />
                    </div>

                    {/* Fields for form type */}
                    {formData.step_type === 'form' && (
                        <div>
                            <div className="flex justify-between items-center mb-3">
                                <Label>Form Fields</Label>
                                <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    onClick={() => {
                                        setEditingField(null);
                                        setShowFieldForm(true);
                                    }}
                                    data-testid="add-field-btn"
                                >
                                    <Plus size={16} className="mr-1" />
                                    Add Field
                                </Button>
                            </div>
                            <div className="space-y-2">
                                {formData.fields.map((field, index) => (
                                    <div key={index} className="flex items-center justify-between p-3 bg-[#FAFAFA] rounded-sm">
                                        <div>
                                            <span className="font-medium">{field.label}</span>
                                            <span className="text-xs text-[#52525B] ml-2">({field.field_type})</span>
                                            {field.required && <span className="text-red-500 ml-1">*</span>}
                                        </div>
                                        <div className="flex gap-2">
                                            <Button
                                                type="button"
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => {
                                                    setEditingField(index);
                                                    setShowFieldForm(true);
                                                }}
                                            >
                                                <Pencil size={16} />
                                            </Button>
                                            <Button
                                                type="button"
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => handleRemoveField(index)}
                                                className="text-red-500"
                                            >
                                                <X size={16} />
                                            </Button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    <div className="flex justify-end gap-3">
                        <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
                        <Button type="submit" className="bg-[#002FA7] hover:bg-[#002280] text-white" data-testid="save-step-btn">
                            {step ? 'Update Step' : 'Create Step'}
                        </Button>
                    </div>
                </form>

                {/* Field Form Modal */}
                {showFieldForm && (
                    <FieldForm
                        field={editingField !== null ? formData.fields[editingField] : null}
                        onSave={handleAddField}
                        onCancel={() => {
                            setShowFieldForm(false);
                            setEditingField(null);
                        }}
                    />
                )}
            </DialogContent>
        </Dialog>
    );
}

// Field Form Component
function FieldForm({ field, onSave, onCancel }) {
    const [data, setData] = useState({
        name: field?.name || '',
        field_type: field?.field_type || 'text',
        label: field?.label || '',
        placeholder: field?.placeholder || '',
        required: field?.required || false,
        options: field?.options || []
    });
    const [optionsText, setOptionsText] = useState((field?.options || []).join('\n'));

    const handleSubmit = () => {
        const options = data.field_type === 'select' 
            ? optionsText.split('\n').filter(o => o.trim())
            : undefined;
        onSave({ ...data, options });
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white p-6 rounded-sm w-full max-w-md">
                <h3 className="font-semibold mb-4">{field ? 'Edit Field' : 'Add Field'}</h3>
                <div className="space-y-4">
                    <div>
                        <Label>Field Name (ID)</Label>
                        <Input
                            value={data.name}
                            onChange={(e) => setData({ ...data, name: e.target.value.toLowerCase().replace(/\s/g, '_') })}
                            className="mt-1"
                            placeholder="e.g., phone_number"
                            data-testid="field-name-input"
                        />
                    </div>
                    <div>
                        <Label>Label</Label>
                        <Input
                            value={data.label}
                            onChange={(e) => setData({ ...data, label: e.target.value })}
                            className="mt-1"
                            placeholder="e.g., Phone Number"
                            data-testid="field-label-input"
                        />
                    </div>
                    <div>
                        <Label>Type</Label>
                        <Select value={data.field_type} onValueChange={(val) => setData({ ...data, field_type: val })}>
                            <SelectTrigger className="mt-1" data-testid="field-type-select">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="text">Text</SelectItem>
                                <SelectItem value="email">Email</SelectItem>
                                <SelectItem value="phone">Phone</SelectItem>
                                <SelectItem value="textarea">Text Area</SelectItem>
                                <SelectItem value="select">Dropdown</SelectItem>
                                <SelectItem value="date">Date</SelectItem>
                                <SelectItem value="file">File Upload</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <div>
                        <Label>Placeholder</Label>
                        <Input
                            value={data.placeholder}
                            onChange={(e) => setData({ ...data, placeholder: e.target.value })}
                            className="mt-1"
                            data-testid="field-placeholder-input"
                        />
                    </div>
                    {data.field_type === 'select' && (
                        <div>
                            <Label>Options (one per line)</Label>
                            <Textarea
                                value={optionsText}
                                onChange={(e) => setOptionsText(e.target.value)}
                                className="mt-1"
                                placeholder="Option 1&#10;Option 2&#10;Option 3"
                                data-testid="field-options-input"
                            />
                        </div>
                    )}
                    <div className="flex items-center justify-between">
                        <Label>Required</Label>
                        <Switch
                            checked={data.required}
                            onCheckedChange={(val) => setData({ ...data, required: val })}
                        />
                    </div>
                </div>
                <div className="flex justify-end gap-3 mt-6">
                    <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>
                    <Button onClick={handleSubmit} className="bg-[#002FA7] hover:bg-[#002280] text-white" data-testid="save-field-btn">
                        {field ? 'Update' : 'Add'} Field
                    </Button>
                </div>
            </div>
        </div>
    );
}

// Partner Dialog Component
function PartnerDialog({ open, onClose, partner, onSave }) {
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        logo_url: '',
        website: '',
        contact_email: '',
        category: '',
        is_active: true
    });

    useEffect(() => {
        if (partner) {
            setFormData({
                name: partner.name || '',
                description: partner.description || '',
                logo_url: partner.logo_url || '',
                website: partner.website || '',
                contact_email: partner.contact_email || '',
                category: partner.category || '',
                is_active: partner.is_active !== false
            });
        } else {
            setFormData({
                name: '',
                description: '',
                logo_url: '',
                website: '',
                contact_email: '',
                category: '',
                is_active: true
            });
        }
    }, [partner]);

    const handleSubmit = (e) => {
        e.preventDefault();
        onSave(formData);
    };

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-lg">
                <DialogHeader>
                    <DialogTitle>{partner ? 'Edit Partner' : 'Add Partner'}</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <Label>Name</Label>
                        <Input
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            className="mt-1"
                            required
                            data-testid="partner-name-input"
                        />
                    </div>
                    <div>
                        <Label>Description</Label>
                        <Textarea
                            value={formData.description}
                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            className="mt-1"
                            required
                            data-testid="partner-description-input"
                        />
                    </div>
                    <div>
                        <Label>Logo URL</Label>
                        <Input
                            value={formData.logo_url}
                            onChange={(e) => setFormData({ ...formData, logo_url: e.target.value })}
                            className="mt-1"
                            placeholder="https://..."
                            data-testid="partner-logo-input"
                        />
                    </div>
                    <div>
                        <Label>Website</Label>
                        <Input
                            value={formData.website}
                            onChange={(e) => setFormData({ ...formData, website: e.target.value })}
                            className="mt-1"
                            placeholder="https://..."
                            data-testid="partner-website-input"
                        />
                    </div>
                    <div>
                        <Label>Contact Email</Label>
                        <Input
                            type="email"
                            value={formData.contact_email}
                            onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
                            className="mt-1"
                            data-testid="partner-email-input"
                        />
                    </div>
                    <div>
                        <Label>Category</Label>
                        <Input
                            value={formData.category}
                            onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                            className="mt-1"
                            placeholder="e.g., Investment, Consulting"
                            data-testid="partner-category-input"
                        />
                    </div>
                    <div className="flex items-center justify-between">
                        <Label>Active</Label>
                        <Switch
                            checked={formData.is_active}
                            onCheckedChange={(val) => setFormData({ ...formData, is_active: val })}
                        />
                    </div>
                    <div className="flex justify-end gap-3">
                        <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
                        <Button type="submit" className="bg-[#002FA7] hover:bg-[#002280] text-white" data-testid="save-partner-btn">
                            {partner ? 'Update Partner' : 'Add Partner'}
                        </Button>
                    </div>
                </form>
            </DialogContent>
        </Dialog>
    );
}
