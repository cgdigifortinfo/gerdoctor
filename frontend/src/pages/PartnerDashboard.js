import { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { partnerDashboardAPI, formatApiError } from '../lib/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { SignOut, FileText, Gear, Eye } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { ThemeLangToggle } from '../components/ThemeLangToggle';
import { Logo } from '../components/Logo';

export default function PartnerDashboard() {
    const { user, logout } = useAuth();
    const { t } = useLanguage();
    const navigate = useNavigate();
    const [submissions, setSubmissions] = useState([]);
    const [profile, setProfile] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('submissions');
    const [selectedSubmission, setSelectedSubmission] = useState(null);
    const [editingProfile, setEditingProfile] = useState(false);
    const [profileForm, setProfileForm] = useState({});

    const loadData = useCallback(async () => {
        try {
            const [subsRes, profileRes] = await Promise.all([
                partnerDashboardAPI.getSubmissions(),
                partnerDashboardAPI.getProfile()
            ]);
            setSubmissions(subsRes.data);
            setProfile(profileRes.data);
            setProfileForm(profileRes.data);
        } catch (error) {
            console.error('Failed to load data:', error);
            if (error.response?.status === 400) {
                toast.error('Your account is not linked to a partner');
            }
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

    const handleSaveProfile = async () => {
        try {
            await partnerDashboardAPI.updateProfile(profileForm);
            toast.success('Profile updated');
            setEditingProfile(false);
            loadData();
        } catch (error) {
            toast.error(formatApiError(error));
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center">
                <div className="text-muted-foreground">Loading...</div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-background">
            {/* Header */}
            <header className="sticky top-0 z-50 glass">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        <div className="flex items-center gap-4">
                            <Logo />
                            <span className="text-xs font-bold tracking-wider uppercase text-green-700 px-2 py-1 bg-green-50 rounded">
                                Partner
                            </span>
                        </div>
                        <div className="flex items-center gap-3">
                            <span className="text-sm text-muted-foreground hidden sm:block">
                                {profile?.name || user?.name}
                            </span>
                            <ThemeLangToggle />
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={handleLogout}
                                className="text-muted-foreground"
                                data-testid="partner-logout-btn"
                            >
                                <SignOut size={20} />
                            </Button>
                        </div>
                    </div>
                </div>
            </header>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {!profile ? (
                    <div className="bg-card border border-border rounded-sm p-8 text-center">
                        <h2 className="text-xl font-semibold text-foreground mb-4">Account Not Linked</h2>
                        <p className="text-muted-foreground">
                            Your account is not yet linked to a partner organization. Please contact an administrator.
                        </p>
                    </div>
                ) : (
                    <Tabs value={activeTab} onValueChange={setActiveTab}>
                        <TabsList className="mb-6 bg-card border border-border">
                            <TabsTrigger value="submissions" className="data-[state=active]:bg-[#114f55] data-[state=active]:text-white">
                                <FileText size={18} className="mr-2" />
                                Submissions
                            </TabsTrigger>
                            <TabsTrigger value="profile" className="data-[state=active]:bg-[#114f55] data-[state=active]:text-white">
                                <Gear size={18} className="mr-2" />
                                Profile
                            </TabsTrigger>
                        </TabsList>

                        {/* Submissions Tab */}
                        <TabsContent value="submissions">
                            <div className="bg-card border border-border rounded-sm">
                                <div className="p-4 border-b border-border">
                                    <h2 className="text-lg font-semibold text-foreground">User Submissions</h2>
                                    <p className="text-sm text-muted-foreground">
                                        View all submissions from users who selected your organization
                                    </p>
                                </div>
                                
                                {submissions.length === 0 ? (
                                    <div className="p-8 text-center text-muted-foreground">
                                        No submissions yet
                                    </div>
                                ) : (
                                    <div className="overflow-x-auto">
                                        <table className="w-full">
                                            <thead className="bg-background">
                                                <tr>
                                                    <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">User</th>
                                                    <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Email</th>
                                                    <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Date</th>
                                                    <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Status</th>
                                                    <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">Actions</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {submissions.map((sub) => (
                                                    <tr key={sub.id} className="border-t border-border table-row-hover">
                                                        <td className="px-4 py-3 text-sm text-foreground">{sub.user_name}</td>
                                                        <td className="px-4 py-3 text-sm text-muted-foreground">{sub.user_email}</td>
                                                        <td className="px-4 py-3 text-sm text-muted-foreground">
                                                            {new Date(sub.created_at).toLocaleDateString()}
                                                        </td>
                                                        <td className="px-4 py-3">
                                                            <span className={`px-2 py-1 text-xs rounded-sm ${
                                                                sub.status === 'submitted' ? 'bg-blue-100 text-blue-700' :
                                                                sub.status === 'reviewed' ? 'bg-green-100 text-green-700' :
                                                                'bg-gray-100 text-gray-700'
                                                            }`}>
                                                                {sub.status}
                                                            </span>
                                                        </td>
                                                        <td className="px-4 py-3">
                                                            <Button
                                                                variant="ghost"
                                                                size="sm"
                                                                onClick={() => setSelectedSubmission(sub)}
                                                                data-testid={`view-submission-${sub.id}`}
                                                            >
                                                                <Eye size={18} />
                                                            </Button>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </div>
                        </TabsContent>

                        {/* Profile Tab */}
                        <TabsContent value="profile">
                            <div className="bg-card border border-border rounded-sm">
                                <div className="p-4 border-b border-border flex justify-between items-center">
                                    <h2 className="text-lg font-semibold text-foreground">Partner Profile</h2>
                                    {!editingProfile && (
                                        <Button
                                            variant="outline"
                                            onClick={() => setEditingProfile(true)}
                                            data-testid="edit-profile-btn"
                                        >
                                            Edit Profile
                                        </Button>
                                    )}
                                </div>
                                
                                <div className="p-6">
                                    {editingProfile ? (
                                        <div className="space-y-4 max-w-lg">
                                            <div>
                                                <Label>Organization Name</Label>
                                                <Input
                                                    value={profileForm.name || ''}
                                                    onChange={(e) => setProfileForm({ ...profileForm, name: e.target.value })}
                                                    className="mt-1"
                                                    data-testid="profile-name-input"
                                                />
                                            </div>
                                            <div>
                                                <Label>Description</Label>
                                                <Textarea
                                                    value={profileForm.description || ''}
                                                    onChange={(e) => setProfileForm({ ...profileForm, description: e.target.value })}
                                                    className="mt-1"
                                                    data-testid="profile-description-input"
                                                />
                                            </div>
                                            <div>
                                                <Label>Logo URL</Label>
                                                <Input
                                                    value={profileForm.logo_url || ''}
                                                    onChange={(e) => setProfileForm({ ...profileForm, logo_url: e.target.value })}
                                                    className="mt-1"
                                                    data-testid="profile-logo-input"
                                                />
                                            </div>
                                            <div>
                                                <Label>Website</Label>
                                                <Input
                                                    value={profileForm.website || ''}
                                                    onChange={(e) => setProfileForm({ ...profileForm, website: e.target.value })}
                                                    className="mt-1"
                                                    data-testid="profile-website-input"
                                                />
                                            </div>
                                            <div>
                                                <Label>Contact Email</Label>
                                                <Input
                                                    type="email"
                                                    value={profileForm.contact_email || ''}
                                                    onChange={(e) => setProfileForm({ ...profileForm, contact_email: e.target.value })}
                                                    className="mt-1"
                                                    data-testid="profile-email-input"
                                                />
                                            </div>
                                            <div>
                                                <Label>Category</Label>
                                                <Input
                                                    value={profileForm.category || ''}
                                                    onChange={(e) => setProfileForm({ ...profileForm, category: e.target.value })}
                                                    className="mt-1"
                                                    data-testid="profile-category-input"
                                                />
                                            </div>
                                            <div className="flex gap-3 pt-4">
                                                <Button
                                                    variant="outline"
                                                    onClick={() => {
                                                        setEditingProfile(false);
                                                        setProfileForm(profile);
                                                    }}
                                                >
                                                    Cancel
                                                </Button>
                                                <Button
                                                    onClick={handleSaveProfile}
                                                    className="bg-[#114f55] hover:bg-[#0d3d42] text-white"
                                                    data-testid="save-profile-btn"
                                                >
                                                    Save Changes
                                                </Button>
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="space-y-6">
                                            <div className="flex items-start gap-6">
                                                {profile.logo_url && (
                                                    <img 
                                                        src={profile.logo_url} 
                                                        alt={profile.name}
                                                        className="w-24 h-24 object-cover rounded-sm"
                                                    />
                                                )}
                                                <div>
                                                    <h3 className="text-xl font-semibold text-foreground">{profile.name}</h3>
                                                    {profile.category && (
                                                        <span className="inline-block mt-1 px-2 py-1 text-xs bg-background text-muted-foreground rounded-sm">
                                                            {profile.category}
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                            <div>
                                                <Label className="text-muted-foreground">Description</Label>
                                                <p className="mt-1">{profile.description}</p>
                                            </div>
                                            <div className="grid md:grid-cols-2 gap-4">
                                                <div>
                                                    <Label className="text-muted-foreground">Website</Label>
                                                    <p className="mt-1">
                                                        {profile.website ? (
                                                            <a href={profile.website} target="_blank" rel="noopener noreferrer" className="text-[#114f55] hover:underline">
                                                                {profile.website}
                                                            </a>
                                                        ) : '-'}
                                                    </p>
                                                </div>
                                                <div>
                                                    <Label className="text-muted-foreground">Contact Email</Label>
                                                    <p className="mt-1">{profile.contact_email || '-'}</p>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </TabsContent>
                    </Tabs>
                )}
            </div>

            {/* Submission Detail Dialog */}
            <Dialog open={!!selectedSubmission} onOpenChange={() => setSelectedSubmission(null)}>
                <DialogContent className="max-w-lg">
                    <DialogHeader>
                        <DialogTitle>Submission Details</DialogTitle>
                    </DialogHeader>
                    {selectedSubmission && (
                        <div className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <Label className="text-muted-foreground">User Name</Label>
                                    <p className="font-medium">{selectedSubmission.user_name}</p>
                                </div>
                                <div>
                                    <Label className="text-muted-foreground">Email</Label>
                                    <p className="font-medium">{selectedSubmission.user_email}</p>
                                </div>
                                <div>
                                    <Label className="text-muted-foreground">Submitted</Label>
                                    <p className="font-medium">{new Date(selectedSubmission.created_at).toLocaleString()}</p>
                                </div>
                                <div>
                                    <Label className="text-muted-foreground">Status</Label>
                                    <p className="font-medium capitalize">{selectedSubmission.status}</p>
                                </div>
                            </div>
                            
                            {selectedSubmission.data && Object.keys(selectedSubmission.data).length > 0 && (
                                <div>
                                    <Label className="text-muted-foreground">Submission Data</Label>
                                    <div className="mt-2 p-4 bg-background rounded-sm">
                                        {Object.entries(selectedSubmission.data).map(([key, value]) => (
                                            <div key={key} className="py-2 border-b border-border last:border-0">
                                                <span className="text-xs text-muted-foreground uppercase">{key.replace(/_/g, ' ')}</span>
                                                <p className="font-medium">{String(value)}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </DialogContent>
            </Dialog>
        </div>
    );
}
