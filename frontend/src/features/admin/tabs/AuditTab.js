

import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select';



import { TabsContent } from '../../../components/ui/tabs';





import { PaginationControls } from '../../../components/PaginationControls';
import { DataTable, TableCell, TableEmptyState, TableHeader, TableHeading, TableRow } from '../../../components/collections';

import { AuditActionBadge } from '../AdminDashboardComponents/AdminPrimitives';
import { auditRowKey, auditTargetSuffix } from '../adminTabViewModels';

// Stryker disable all: declarative adapter; presentation derivations live in adminTabViewModels.
export function AuditTab(props) {
    const { t, auditLogs, auditActionTypes, auditFilter, setAuditFilter, auditDateFrom, setAuditDateFrom, auditDateTo, setAuditDateTo, auditPagination, handleAuditFilter, handleClearAuditFilter } = props;
    return (
<TabsContent value="audit">
                        <div className="bg-card border border-border rounded-sm">
                            <div className="p-4 border-b border-border">
                                <h2 className="text-lg font-semibold mb-3">{t('admin_audit')}</h2>
                                <div className="flex flex-col sm:flex-row gap-2 items-start sm:items-end">
                                    <div>
                                        <Label className="text-xs text-muted-foreground">Action Type</Label>
                                        <Select value={auditFilter} onValueChange={setAuditFilter}>
                                            <SelectTrigger className="w-44 h-9 text-sm border-border" data-testid="audit-action-filter">
                                                <SelectValue placeholder="All actions" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="all">All actions</SelectItem>
                                                {auditActionTypes.map(a => (
                                                    <SelectItem key={a} value={a}>{a.replace(/_/g, ' ')}</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div>
                                        <Label className="text-xs text-muted-foreground">From</Label>
                                        <Input type="date" value={auditDateFrom} onChange={e => setAuditDateFrom(e.target.value)} className="h-9 text-sm border-border w-40" data-testid="audit-date-from" />
                                    </div>
                                    <div>
                                        <Label className="text-xs text-muted-foreground">To</Label>
                                        <Input type="date" value={auditDateTo} onChange={e => setAuditDateTo(e.target.value)} className="h-9 text-sm border-border w-40" data-testid="audit-date-to" />
                                    </div>
                                    <Button size="sm" onClick={handleAuditFilter} className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white h-9" data-testid="audit-apply-filter">
                                        Filter
                                    </Button>
                                    <Button variant="ghost" size="sm" onClick={handleClearAuditFilter} className="text-muted-foreground h-9" data-testid="audit-clear-filter">
                                        {t('admin_clear')}
                                    </Button>
                                </div>
                            </div>
                            <DataTable>
                                    <TableHeader className="bg-muted">
                                        <tr>
                                            <TableHeading>Time</TableHeading><TableHeading>Actor</TableHeading><TableHeading>Action</TableHeading><TableHeading>Target</TableHeading><TableHeading>Details</TableHeading>
                                        </tr>
                                    </TableHeader>
                                    <tbody>
                                        {auditPagination.paginatedItems.map((log, idx) => (
                                            <TableRow key={auditRowKey(log, auditPagination.startIndex + idx)}>
                                                <TableCell className="text-sm text-muted-foreground whitespace-nowrap">
                                                    {log.timestamp ? new Date(log.timestamp).toLocaleString() : '-'}
                                                </TableCell>
                                                <TableCell className="text-sm font-medium">{log.actor_email}</TableCell>
                                                <TableCell>
                                                    <AuditActionBadge action={log.action} />
                                                </TableCell>
                                                <TableCell className="text-sm text-muted-foreground">
                                                    <span className="capitalize">{log.target_type}</span>
                                                    {log.target_id && <span className="text-xs ml-1 opacity-60">{auditTargetSuffix(log.target_id)}</span>}
                                                </TableCell>
                                                <TableCell className="text-sm text-muted-foreground max-w-[200px] truncate">
                                                    {log.details ? Object.entries(log.details).map(([k, v]) => `${k}: ${JSON.stringify(v)}`).join(', ') : '-'}
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                        {auditLogs.length === 0 && <TableEmptyState colSpan={5} title="No audit logs yet" description="Actions will appear here as admins make changes." />}
                                    </tbody>
                            </DataTable>
                            <PaginationControls pagination={auditPagination} id="admin-audit" />
                        </div>
                    </TabsContent>
    );
}
