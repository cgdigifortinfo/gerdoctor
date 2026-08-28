import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowClockwise, BellRinging, Browser, DeviceMobile, FloppyDisk, PencilSimple, Plus } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { adminAPI, formatApiError } from '../../lib/api';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Switch } from '../ui/switch';
import { PaginationControls, usePagination } from '../PaginationControls';
import { asArray } from '../../lib/valueNormalization';
import {
    appendEventHandler, filterEvents, nonLayoutTemplates, toggleChannel, updateEventConfig, updateEventHandler,
} from './eventManagementDomain';

// Stryker disable all: event-management adapter; transformations live in eventManagementDomain.


const STATUS_STYLES = {
    processed: 'bg-emerald-100 text-emerald-800',
    failed: 'bg-red-100 text-red-800',
    skipped: 'bg-amber-100 text-amber-800',
    pending: 'bg-blue-100 text-blue-800',
};


export default function EventManagement() {
    const [configs, setConfigs] = useState([]);
    const [events, setEvents] = useState([]);
    const [templates, setTemplates] = useState([]);
    const [eventTypeFilter, setEventTypeFilter] = useState('all');
    const [statusFilter, setStatusFilter] = useState('all');
    const [loading, setLoading] = useState(true);
    const [savingType, setSavingType] = useState('');

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            const [configResponse, eventResponse, templateResponse] = await Promise.all([
                adminAPI.listEventConfigs(),
                adminAPI.listEvents(0),
                adminAPI.listEmailTemplates(),
            ]);
            setConfigs(configResponse.data || []);
            setEvents(eventResponse.data?.events || []);
            setTemplates(nonLayoutTemplates(templateResponse.data?.templates));
        } catch (error) {
            toast.error(formatApiError(error));
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadData(); }, [loadData]);

    const updateConfig = (eventType, updater) => {
        setConfigs(current => updateEventConfig(current, eventType, updater));
    };

    const updateHandler = (eventType, handlerId, patch) => {
        setConfigs(current => updateEventHandler(current, eventType, handlerId, patch));
    };

    const addHandler = (eventType, type) => {
        setConfigs(current => appendEventHandler(current, eventType, type, templates[0]?.key || '', `notify-user-${type}-${Date.now()}`));
    };

    const saveConfig = async (config) => {
        setSavingType(config.event_type);
        try {
            const response = await adminAPI.updateEventConfig(config.event_type, {
                enabled: config.enabled,
                handlers: config.handlers || [],
            });
            updateConfig(config.event_type, () => response.data);
            toast.success(`Event „${config.label}“ gespeichert`);
        } catch (error) {
            toast.error(formatApiError(error));
        } finally {
            setSavingType('');
        }
    };

    const filteredEvents = useMemo(() => filterEvents(events, eventTypeFilter, statusFilter), [events, eventTypeFilter, statusFilter]);
    const pagination = usePagination(filteredEvents, 'admin-domain-events', {
        resetKey: `${eventTypeFilter}|${statusFilter}`,
    });

    const retryEvent = async (eventId) => {
        try {
            await adminAPI.retryEvent(eventId);
            toast.success('Event erneut verarbeitet');
            loadData();
        } catch (error) {
            toast.error(formatApiError(error));
        }
    };

    if (loading) {
        return <div className="rounded-sm border border-border bg-card p-8 text-center text-muted-foreground">Events werden geladen …</div>;
    }

    return (
        <div className="space-y-6" data-testid="event-management">
            <div className="rounded-sm border border-border bg-card">
                <div className="flex flex-col gap-3 border-b border-border p-5 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                        <div className="flex items-center gap-2">
                            <BellRinging size={22} className="text-[var(--brand-primary)]" />
                            <h2 className="text-lg font-semibold text-foreground">Events & Reaktionen</h2>
                        </div>
                        <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
                            Fachliche Ereignisse werden dauerhaft protokolliert. Hier steuern Sie E-Mails sowie providerfähige Browser- und App-Notifications.
                        </p>
                    </div>
                    <Button variant="outline" onClick={loadData} data-testid="events-refresh-btn">
                        <ArrowClockwise size={16} className="mr-1" /> Aktualisieren
                    </Button>
                </div>

                <div className="grid gap-4 p-5 lg:grid-cols-2">
                    {configs.map(config => (
                        <section key={config.event_type} className="rounded-sm border border-border p-4" data-testid={`event-config-${config.event_type}`}>
                            <div className="flex items-start justify-between gap-4">
                                <div>
                                    <h3 className="font-semibold text-foreground">{config.label}</h3>
                                    <code className="mt-1 block text-xs text-muted-foreground">{config.event_type}</code>
                                </div>
                                <div className="flex items-center gap-2">
                                    <Label className="text-xs">Aktiv</Label>
                                    <Switch
                                        checked={config.enabled !== false}
                                        onCheckedChange={checked => updateConfig(config.event_type, current => ({ ...current, enabled: checked }))}
                                        data-testid={`event-enabled-${config.event_type}`}
                                    />
                                </div>
                            </div>
                            <p className="mt-3 text-sm text-muted-foreground">{config.description}</p>

                            <div className="mt-4 space-y-3">
                                {asArray(config.handlers).map(handler => (
                                    <div key={handler.id} className="rounded-sm bg-muted/40 p-3" data-testid={`event-handler-${config.event_type}-${handler.id}`}>
                                        <div className="flex items-center justify-between gap-3">
                                            <div className="flex items-center gap-2">
                                                {handler.type === 'notification' ? <DeviceMobile size={17} /> : <BellRinging size={17} />}
                                                <p className="text-sm font-medium text-foreground">{handler.label}</p>
                                            </div>
                                            <Switch
                                                checked={handler.enabled !== false}
                                                onCheckedChange={checked => updateHandler(config.event_type, handler.id, { enabled: checked })}
                                                data-testid={`event-handler-enabled-${config.event_type}-${handler.type}`}
                                            />
                                        </div>
                                        <div className="mt-3">
                                            <Label className="text-xs text-muted-foreground">Message-Vorlage</Label>
                                            <div className="mt-1 flex flex-col gap-2 sm:flex-row">
                                                <Select value={handler.template_key || ''} onValueChange={value => updateHandler(config.event_type, handler.id, { template_key: value })}>
                                                    <SelectTrigger className="flex-1" data-testid={`event-template-${config.event_type}-${handler.type}`}>
                                                        <SelectValue placeholder="Vorlage wählen" />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        {templates.map(template => <SelectItem key={template.key} value={template.key}>{template.key}</SelectItem>)}
                                                    </SelectContent>
                                                </Select>
                                                {handler.template_key && (
                                                    <Button asChild variant="outline" size="sm" className="h-9" data-testid={`event-edit-template-${config.event_type}-${handler.type}`}>
                                                        <Link to={`/admin?tab=email-templates&template=${encodeURIComponent(handler.template_key)}&channel=${handler.type === 'notification' ? 'notification' : 'email'}`}>
                                                            <PencilSimple size={14} className="mr-1" /> Bearbeiten
                                                        </Link>
                                                    </Button>
                                                )}
                                            </div>
                                        </div>
                                        {handler.type === 'notification' && (
                                            <div className="mt-3 rounded-sm border border-border bg-card p-3">
                                                <Label className="text-xs text-muted-foreground">Zielkanäle</Label>
                                                <div className="mt-2 flex flex-wrap gap-4">
                                                    {[
                                                        { key: 'browser', label: 'Browser', icon: Browser },
                                                        { key: 'app', label: 'App', icon: DeviceMobile },
                                                    ].map(channel => {
                                                        const Icon = channel.icon;
                                                        const channels = handler.channels || [];
                                                        return (
                                                            <label key={channel.key} className="flex items-center gap-2 text-sm">
                                                                <Switch
                                                                    checked={channels.includes(channel.key)}
                                                                    onCheckedChange={checked => updateHandler(config.event_type, handler.id, {
                                                                        channels: toggleChannel(channels, channel.key, checked),
                                                                    })}
                                                                    data-testid={`event-channel-${config.event_type}-${channel.key}`}
                                                                />
                                                                <Icon size={15} /> {channel.label}
                                                            </label>
                                                        );
                                                    })}
                                                </div>
                                                <p className="mt-2 text-[11px] text-muted-foreground">Provider: noch nicht konfiguriert · Nachrichten werden bis zur Provider-Anbindung in der Outbox vorgemerkt.</p>
                                            </div>
                                        )}
                                    </div>
                                ))}
                                {(config.handlers || []).length === 0 && (
                                    <p className="rounded-sm bg-muted/30 p-3 text-xs text-muted-foreground">Dieses Event wird aktuell nur protokolliert.</p>
                                )}
                                <div className="flex flex-wrap justify-between gap-2">
                                    <div className="flex flex-wrap gap-1">
                                        {!asArray(config.handlers).some(handler => handler.type === 'email') && (
                                            <Button variant="ghost" size="sm" onClick={() => addHandler(config.event_type, 'email')} data-testid={`event-add-email-handler-${config.event_type}`}>
                                                <Plus size={14} className="mr-1" /> E-Mail-Reaktion
                                            </Button>
                                        )}
                                        {!asArray(config.handlers).some(handler => handler.type === 'notification') && (
                                            <Button variant="ghost" size="sm" onClick={() => addHandler(config.event_type, 'notification')} data-testid={`event-add-notification-handler-${config.event_type}`}>
                                                <Plus size={14} className="mr-1" /> Browser/App-Reaktion
                                            </Button>
                                        )}
                                    </div>
                                    <Button size="sm" onClick={() => saveConfig(config)} disabled={savingType === config.event_type} data-testid={`event-save-${config.event_type}`}>
                                        <FloppyDisk size={14} className="mr-1" /> Speichern
                                    </Button>
                                </div>
                            </div>
                        </section>
                    ))}
                </div>
            </div>

            <div className="rounded-sm border border-border bg-card">
                <div className="flex flex-col gap-3 border-b border-border p-4 sm:flex-row sm:items-end sm:justify-between">
                    <div>
                        <h2 className="font-semibold text-foreground">Ereignisverlauf</h2>
                        <p className="text-xs text-muted-foreground">Ausgelöste Events mit Verarbeitungs- und Zustellstatus.</p>
                    </div>
                    <div className="flex flex-wrap gap-3">
                        <Select value={eventTypeFilter} onValueChange={setEventTypeFilter}>
                            <SelectTrigger className="w-64" data-testid="events-type-filter"><SelectValue /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">Alle Eventtypen</SelectItem>
                                {configs.map(config => <SelectItem key={config.event_type} value={config.event_type}>{config.label}</SelectItem>)}
                            </SelectContent>
                        </Select>
                        <Select value={statusFilter} onValueChange={setStatusFilter}>
                            <SelectTrigger className="w-40" data-testid="events-status-filter"><SelectValue /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">Alle Status</SelectItem>
                                {['processed', 'failed', 'skipped', 'pending'].map(status => <SelectItem key={status} value={status}>{status}</SelectItem>)}
                            </SelectContent>
                        </Select>
                    </div>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full" data-testid="events-history-table">
                        <thead className="bg-background">
                            <tr>
                                <th className="px-4 py-3 text-left text-xs font-bold uppercase text-muted-foreground">Zeit</th>
                                <th className="px-4 py-3 text-left text-xs font-bold uppercase text-muted-foreground">Event</th>
                                <th className="px-4 py-3 text-left text-xs font-bold uppercase text-muted-foreground">User / Step</th>
                                <th className="px-4 py-3 text-left text-xs font-bold uppercase text-muted-foreground">Status</th>
                                <th className="px-4 py-3 text-left text-xs font-bold uppercase text-muted-foreground">Reaktionen</th>
                                <th className="px-4 py-3 text-left text-xs font-bold uppercase text-muted-foreground">Aktion</th>
                            </tr>
                        </thead>
                        <tbody>
                            {pagination.paginatedItems.map(event => (
                                <tr key={event.id} className="border-t border-border" data-testid={`event-row-${event.event_type}`}>
                                    <td className="whitespace-nowrap px-4 py-3 text-xs text-muted-foreground">{new Date(event.created_at).toLocaleString('de-DE')}</td>
                                    <td className="px-4 py-3"><code className="text-xs text-foreground">{event.event_type}</code></td>
                                    <td className="px-4 py-3 text-sm">
                                        <p className="font-medium text-foreground">{event.payload?.user_name || '—'}</p>
                                        <p className="text-xs text-muted-foreground">{event.payload?.step_title || event.payload?.filename || '—'}</p>
                                    </td>
                                    <td className="px-4 py-3"><Badge className={STATUS_STYLES[event.status] || ''}>{event.status}</Badge></td>
                                    <td className="px-4 py-3 text-xs text-muted-foreground">
                                        {(event.handler_results || []).length === 0 ? 'Keine' : event.handler_results.map(result => `${result.type}: ${result.status}`).join(', ')}
                                    </td>
                                    <td className="px-4 py-3">
                                        {(event.status === 'failed' || event.status === 'skipped') && (
                                            <Button variant="outline" size="sm" onClick={() => retryEvent(event.event_id)} data-testid={`event-retry-${event.event_id}`}>
                                                <ArrowClockwise size={14} className="mr-1" /> Wiederholen
                                            </Button>
                                        )}
                                    </td>
                                </tr>
                            ))}
                            {filteredEvents.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-sm text-muted-foreground">Noch keine Ereignisse vorhanden.</td></tr>}
                        </tbody>
                    </table>
                </div>
                <PaginationControls pagination={pagination} id="admin-domain-events" />
            </div>
        </div>
    );
}
