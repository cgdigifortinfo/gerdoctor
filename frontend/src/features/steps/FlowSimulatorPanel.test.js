import { fireEvent, render, screen } from '@testing-library/react';

import FlowSimulatorPanel, { normalizeSimulatorProfile } from '../../components/FlowSimulatorPanel';

let mockPlayProps;
jest.mock('@phosphor-icons/react', () => ({ Play: props => { mockPlayProps = props; return <span data-testid="play-icon" />; } }));


describe('Steps flow simulator control', () => {
    test('renders the inactive default and forwards a selected profile', () => {
        const onChange = jest.fn();
        render(<FlowSimulatorPanel value="none" onChange={onChange} />);

        expect(screen.getByTestId('flow-simulator-select')).toHaveValue('none');
        expect(mockPlayProps).toEqual({ size: 14, className: 'text-[var(--brand-primary)]', weight: 'regular' });
        expect(screen.queryByText('sichtbar')).not.toBeInTheDocument();
        fireEvent.change(screen.getByTestId('flow-simulator-select'), { target: { value: 'partner_path' } });
        expect(onChange).toHaveBeenCalledWith('partner_path');
    });

    test('shows the legend for an active simulation', () => {
        render(<FlowSimulatorPanel value="upload_path" onChange={() => {}} />);

        expect(screen.getByText('sichtbar')).toBeInTheDocument();
        expect(screen.getByText('versteckt')).toBeInTheDocument();
        expect(screen.getByText('blockiert')).toBeInTheDocument();
        expect(screen.getByText('auto-abgeschlossen')).toBeInTheDocument();
        expect(mockPlayProps).toEqual({ size: 14, className: 'text-emerald-600', weight: 'fill' });
        expect(screen.getByText('sichtbar').firstElementChild).toHaveStyle({ background: '#2dd4bf' });
        expect(screen.getByText('versteckt').firstElementChild).toHaveStyle({ background: '#94a3b8' });
        expect(screen.getByText('blockiert').firstElementChild).toHaveStyle({ background: '#dc2626' });
        expect(screen.getByText('auto-abgeschlossen').firstElementChild).toHaveStyle({ background: '#10b981' });
    });

    test('falls back to the inactive option for an omitted value', () => {
        render(<FlowSimulatorPanel onChange={jest.fn()} />);
        expect(screen.getByTestId('flow-simulator-select')).toHaveValue('none');
    });

    test('normalizes only omitted and empty profiles to the inactive key', () => {
        expect(normalizeSimulatorProfile(undefined)).toBe('none');
        expect(normalizeSimulatorProfile('')).toBe('none');
        expect(normalizeSimulatorProfile('upload_path')).toBe('upload_path');
    });
});
