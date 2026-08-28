import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { AuditActionBadge, ElementToggle, StatCard } from './AdminPrimitives';
import { StatusBadge } from '../../../components/ui/entity-badges';

jest.mock('../../../components/ui/switch', () => ({ Switch: ({ onCheckedChange, ...props }) => <button {...props} onClick={() => onCheckedChange(false)}>toggle</button> }));

test('admin primitives render values, known, fallback and missing actions', () => {
  const onChange = jest.fn();
  const { rerender } = render(<><StatCard label="Users" value={7} /><AuditActionBadge action="role_change" /><ElementToggle id="feature" label="Feature" description="Description" checked onChange={onChange} /></>);
  fireEvent.click(screen.getByTestId('element-toggle-feature')); expect(onChange).toHaveBeenCalledWith(false); expect(screen.getByText('role change')).toBeInTheDocument();
  rerender(<><AuditActionBadge action="custom_action" /><ElementToggle id="plain" label="Plain" checked={false} onChange={onChange} /></>); expect(screen.getByText('custom action')).toBeInTheDocument();
  rerender(<AuditActionBadge />); expect(screen.getByText('unknown')).toBeInTheDocument();
  rerender(<StatusBadge>Default</StatusBadge>); expect(screen.getByText('Default')).toBeInTheDocument();
});
