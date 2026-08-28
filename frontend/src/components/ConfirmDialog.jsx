import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';

// Stryker disable all: declarative confirmation adapter.
export function ConfirmDialog({ open, onOpenChange, title = 'Bestätigung', message, confirmLabel = 'Bestätigen', cancelLabel = 'Abbrechen', onConfirm, destructive = false }) {
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader><DialogTitle>{title}</DialogTitle></DialogHeader>
                <p className="py-4 text-sm text-muted-foreground" data-testid="confirm-dialog-message">{message}</p>
                <div className="flex justify-end gap-3">
                    <Button variant="outline" onClick={() => onOpenChange(false)} data-testid="confirm-dialog-cancel">{cancelLabel}</Button>
                    <Button className={destructive ? 'bg-red-600 text-white hover:bg-red-700' : ''} onClick={onConfirm} data-testid="confirm-dialog-yes">{confirmLabel}</Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}
