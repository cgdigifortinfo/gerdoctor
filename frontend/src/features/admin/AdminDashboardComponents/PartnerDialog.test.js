import React from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { PartnerDialog } from './PartnerDialog';

jest.mock('../../../components/ui/dialog', () => ({ Dialog: ({ open, children }) => open ? <div>{children}</div> : null, DialogContent: ({ children }) => <div>{children}</div>, DialogHeader: ({ children }) => <header>{children}</header>, DialogTitle: ({ children }) => <h2>{children}</h2> }));
jest.mock('../../../components/ui/select', () => ({ Select: ({ children, onValueChange }) => <div>{children}<button type="button" data-testid="billing-select" onClick={() => onValueChange('active')}>active status</button></div>, SelectContent: ({ children }) => <>{children}</>, SelectItem: ({ children }) => <span>{children}</span>, SelectTrigger: ({ children }) => <div>{children}</div>, SelectValue: () => null }));
jest.mock('../../../components/ui/checkbox', () => ({ Checkbox: ({ checked, onCheckedChange }) => <button type="button" role="checkbox" aria-checked={checked} onClick={onCheckedChange}>check</button> }));

const change = (id, value) => fireEvent.change(screen.getByTestId(id), { target: { value } });

test('partner editor exercises fields, tags, users, surveys, prices, Stripe and submit', () => {
  jest.useFakeTimers();
  const onSave = jest.fn(), onClose = jest.fn();
  const partner = { id: 'p', name: 'School', description: 'Desc', logo_url: '/logo', website: 'https://x', contact_email: 'x@y.de', category: 'Language', tags: ['Existing'], is_active: false, linked_user_ids: ['u1'], survey_ids: ['s1'], step_user_fee_cents: { step1: 50 }, stripe_customer_id: 'cus', stripe_subscription_id: 'sub', billing_status: 'paid', service_steps: [{ id: 'step1', order: 1, title: 'Start', filter_tag: 'Tag', step_user_fee_cents: 25 }, { id: 'step2', order: 2, title: 'Next' }] };
  const users = [{ id: 'admin', role: 'admin', name: 'Admin', email: 'a@x' }, { id: 'u1', role: 'user', name: 'Zulu', email: 'z@x' }, { id: 'u2', role: 'user', name: 'Alpha', email: 'same@x' }, { id: 'u3', role: 'user', name: 'Alpha', email: 'other@x' }];
  render(<PartnerDialog open onClose={onClose} partner={partner} onSave={onSave} allUsers={users} allPartners={[partner, { tags: ['Suggested', 'Existing'] }]} surveys={[{ id: 's1', name: 'One' }, { id: 's2', name: 'Two' }]} defaultUserFeeCents={100} t={x => x} />);
  ['partner-name-input','partner-description-input','partner-logo-input','partner-website-input','partner-email-input','partner-category-input'].forEach(id => change(id, 'Changed'));
  fireEvent.click(screen.getByTestId('remove-tag-Existing')); change('partner-tags-input', 'Sug'); expect(screen.getByTestId('tag-suggestions')).toBeInTheDocument(); fireEvent.mouseDown(screen.getAllByText('Suggested')[1]); fireEvent.click(screen.getByTestId('remove-tag-Suggested')); change('partner-tags-input', 'Sug'); fireEvent.mouseDown(screen.getAllByText('Suggested')[0]);
  change('partner-tags-input', 'Brand New'); fireEvent.keyDown(screen.getByTestId('partner-tags-input'), { key: 'Enter' }); change('partner-tags-input', 'Another'); fireEvent.focus(screen.getByTestId('partner-tags-input')); fireEvent.blur(screen.getByTestId('partner-tags-input')); fireEvent.mouseDown(screen.getByTestId('create-new-tag')); act(() => jest.runAllTimers());
  fireEvent.click(screen.getByTestId('partner-link-user-u1').querySelector('input')); fireEvent.click(screen.getByTestId('partner-link-user-u2').querySelector('input'));
  change('partner-user-search', 'nobody'); expect(screen.getByText('partner_no_results')).toBeInTheDocument(); change('partner-user-search', '');
  screen.getAllByRole('checkbox').slice(-2).forEach(box => fireEvent.click(box));
  change('partner-step-price-step1', ''); change('partner-step-price-step2', '125');
  const stripeInputs = screen.getByTestId('partner-stripe-fields').querySelectorAll('input'); fireEvent.change(stripeInputs[0], { target: { value: ' cus_new ' } }); fireEvent.change(stripeInputs[1], { target: { value: ' sub_new ' } }); fireEvent.click(screen.getByTestId('billing-select'));
  fireEvent.click(screen.getByTestId('save-partner-btn')); fireEvent.click(screen.getByText('cancel'));
  expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ name: 'Changed', billing_status: 'active', stripe_customer_id: 'cus_new' })); expect(onClose).toHaveBeenCalled(); jest.useRealTimers();
});

test('new and sparse partner reset defaults and show no-user/no-step variants', () => {
  const onSave = jest.fn();
  const { rerender } = render(<PartnerDialog open onClose={jest.fn()} partner={null} onSave={onSave} allUsers={[]} allPartners={undefined} surveys={undefined} t={x => x} />);
  expect(screen.getByText('partner_no_users')).toBeInTheDocument(); change('partner-tags-input', 'x'); change('partner-tags-input', ''); fireEvent.keyDown(screen.getByTestId('partner-tags-input'), { key: 'Enter' }); fireEvent.keyDown(screen.getByTestId('partner-tags-input'), { key: 'Escape' }); fireEvent.focus(screen.getByTestId('partner-tags-input')); fireEvent.click(screen.getByTestId('save-partner-btn')); expect(onSave).toHaveBeenCalled();
  rerender(<PartnerDialog open onClose={jest.fn()} partner={{ name: 'Sparse', service_steps: [] }} onSave={onSave} allUsers={[]} allPartners={[]} surveys={[]} t={x => x} />); expect(screen.getByText(/noch kein Partner-Step/)).toBeInTheDocument();
  rerender(<PartnerDialog open onClose={jest.fn()} partner={{ tags: ['Same'] }} onSave={onSave} allUsers={[]} allPartners={[]} surveys={[]} t={x => x} />); change('partner-tags-input', 'Same'); fireEvent.keyDown(screen.getByTestId('partner-tags-input'), { key: 'Enter' }); expect(screen.getByText('partner_edit')).toBeInTheDocument();
});
