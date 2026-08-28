







import { Progress } from '../../../components/ui/progress';

import { TabsContent } from '../../../components/ui/tabs';





import { PaginationControls } from '../../../components/PaginationControls';

import { StatCard } from '../AdminDashboardComponents/AdminPrimitives';
import { SectionCard } from '../../../components/layout';

// Stryker disable all: declarative React adapter over precomputed analytics data.
export function AnalyticsTab(props) {
    const { analytics, analyticsPagination } = props;
    return (
<TabsContent value="analytics">
                        {analytics && (
                            <div className="space-y-6">
                                {/* Stats Grid */}
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    <StatCard label="Total Users" value={analytics.total_users} />
                                    <StatCard label="Active Partners" value={analytics.total_partners} />
                                    <StatCard label="Submissions" value={analytics.total_submissions} />
                                    <StatCard label="New (7 days)" value={analytics.recent_registrations} />
                                </div>

                                {/* Role Distribution */}
                                <div className="bg-card border border-border rounded-sm p-6">
                                    <h3 className="text-lg font-semibold text-foreground mb-4">User Distribution</h3>
                                    <div className="grid grid-cols-3 gap-4">
                                        <div className="text-center p-4 bg-background rounded-sm">
                                            <p className="text-2xl font-black text-foreground">{analytics.total_users}</p>
                                            <p className="text-sm text-muted-foreground">Regular Users</p>
                                        </div>
                                        <div className="text-center p-4 bg-background rounded-sm">
                                            <p className="text-2xl font-black text-foreground">{analytics.partner_count}</p>
                                            <p className="text-sm text-muted-foreground">Partner Users</p>
                                        </div>
                                        <div className="text-center p-4 bg-background rounded-sm">
                                            <p className="text-2xl font-black text-foreground">{analytics.admin_count}</p>
                                            <p className="text-sm text-muted-foreground">Admins</p>
                                        </div>
                                    </div>
                                </div>

                                {/* Step Completion Rates */}
                                <SectionCard title="Step Completion Rates" contentClassName="p-6" footer={<PaginationControls pagination={analyticsPagination} id="admin-analytics-steps" />}>
                                    <div className="space-y-4">
                                        {analyticsPagination.paginatedItems.map((step) => (
                                            <div key={step.step_id} className="space-y-2">
                                                <div className="flex justify-between items-center">
                                                    <div className="flex items-center gap-2">
                                                        <span className="w-6 h-6 rounded-full bg-[var(--brand-primary)] text-white flex items-center justify-center text-xs font-bold">
                                                            {step.order}
                                                        </span>
                                                        <span className="font-medium text-sm text-foreground">{step.title}</span>
                                                    </div>
                                                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                                                        <span>{step.completed}/{step.total} completed</span>
                                                        <span className="font-bold text-[var(--brand-primary)]">{step.completion_rate}%</span>
                                                    </div>
                                                </div>
                                                <Progress value={step.completion_rate} className="h-2" />
                                            </div>
                                        ))}
                                    </div>
                                </SectionCard>
                            </div>
                        )}
                    </TabsContent>
    );
}
