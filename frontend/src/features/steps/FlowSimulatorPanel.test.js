import { fireEvent, render, screen } from '@testing-library/react';

import FlowSimulatorPanel from '../../components/FlowSimulatorPanel';


describe('Steps flow simulator control', () => {
    test('renders the inactive default and forwards a selected profile', () => {
        const onChange = jest.fn();
        render(<FlowSimulatorPanel value="none" onChange={onChange} />);

        expect(screen.getByTestId('flow-simulator-select')).toHaveValue('none');
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
    });
});
