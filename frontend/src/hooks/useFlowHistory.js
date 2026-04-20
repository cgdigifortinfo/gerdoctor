import { useState, useCallback } from 'react';

/**
 * Simple undo/redo history hook used by the StepsFlowBuilder.
 *
 * Stores opaque snapshots (positions map) on a past/future stack.
 * Caller is responsible for:
 *   - calling `push(snapshot)` BEFORE mutating state
 *   - calling `undo(currentSnapshot)` / `redo(currentSnapshot)` and applying the
 *     returned snapshot to its own state
 *
 * @param {number} maxSize - maximum number of snapshots kept on each stack
 */
export function useFlowHistory(maxSize = 50) {
    const [past, setPast] = useState([]);
    const [future, setFuture] = useState([]);

    const push = useCallback((snapshot) => {
        if (!snapshot) return;
        setPast((p) => {
            const next = [...p, snapshot];
            return next.length > maxSize ? next.slice(-maxSize) : next;
        });
        setFuture([]);
    }, [maxSize]);

    const undo = useCallback((current) => {
        if (past.length === 0) return null;
        const prev = past[past.length - 1];
        setPast((p) => p.slice(0, -1));
        setFuture((f) => [...f, current]);
        return prev;
    }, [past]);

    const redo = useCallback((current) => {
        if (future.length === 0) return null;
        const next = future[future.length - 1];
        setFuture((f) => f.slice(0, -1));
        setPast((p) => [...p, current]);
        return next;
    }, [future]);

    const clear = useCallback(() => {
        setPast([]);
        setFuture([]);
    }, []);

    return {
        push,
        undo,
        redo,
        clear,
        canUndo: past.length > 0,
        canRedo: future.length > 0,
    };
}
