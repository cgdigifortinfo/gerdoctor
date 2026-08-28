import { useState } from 'react';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';





import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../../components/ui/dialog';
import {   MagnifyingGlass, Link as LinkIcon } from '@phosphor-icons/react';
import { linkedUserCandidates } from '../adminUserDialogDomain';




// Stryker disable all: declarative search adapter; filtering and ordering live in adminUserDialogDomain.
export function LinkUserDialog({ open, onClose, partner, users, onLink }) {
    const [search, setSearch] = useState('');
    const filtered = linkedUserCandidates(users, search);

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-md max-h-[85vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Link User to {partner?.name}</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                    <div className="relative">
                        <MagnifyingGlass size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                        <Input
                            placeholder="Search users..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="pl-9 border-border rounded-sm"
                            data-testid="link-user-search"
                        />
                    </div>
                    <div className="max-h-[300px] overflow-y-auto space-y-2">
                        {filtered.map((u) => (
                            <div key={u.id} className="flex items-center justify-between p-3 bg-background rounded-sm hover:bg-gray-100 transition-colors">
                                <div>
                                    <p className="font-medium text-sm">{u.name}</p>
                                    <p className="text-xs text-muted-foreground">{u.email}</p>
                                </div>
                                <Button
                                    size="sm"
                                    onClick={() => onLink(partner?.id, u.id)}
                                    className="bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-hover)] text-white"
                                    data-testid={`link-select-user-${u.id}`}
                                >
                                    <LinkIcon size={14} className="mr-1" /> Link
                                </Button>
                            </div>
                        ))}
                        {filtered.length === 0 && (
                            <p className="text-sm text-center text-muted-foreground py-4">
                                No available users found
                            </p>
                        )}
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}
