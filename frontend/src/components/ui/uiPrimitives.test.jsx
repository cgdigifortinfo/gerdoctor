import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { Badge, badgeVariants } from './badge';
import { Button, buttonVariants } from './button';
import { Checkbox } from './checkbox';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from './dialog';
import { HelpLabel, HelpTooltip } from './help-tooltip';
import { Input } from './input';
import { Label } from './label';
import { Progress } from './progress';
import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectSeparator, SelectTrigger, SelectValue } from './select';
import { Switch } from './switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './tabs';
import { Textarea } from './textarea';
import { ThemeProvider } from '../../contexts/ThemeContext';
import { Toaster, toast } from './sonner';

beforeAll(() => {
  window.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
  window.HTMLElement.prototype.hasPointerCapture = jest.fn(() => false);
  window.HTMLElement.prototype.setPointerCapture = jest.fn();
  window.HTMLElement.prototype.releasePointerCapture = jest.fn();
  window.HTMLElement.prototype.scrollIntoView = jest.fn();
});

test('badge and button variants render all composition modes', () => {
  expect(badgeVariants({ variant: 'destructive' })).toContain('destructive');
  expect(buttonVariants({ variant: 'link', size: 'icon' })).toContain('underline');
  render(<><Badge className="custom">badge</Badge><Button>button</Button><Button asChild variant="outline" size="sm"><a href="/x">child</a></Button></>);
  expect(screen.getByText('badge')).toHaveClass('custom');
  expect(screen.getByText('button').tagName).toBe('BUTTON');
  expect(screen.getByText('child').tagName).toBe('A');
});

test('form primitives forward props, state, refs, and values', () => {
  const ref = React.createRef();
  render(<div>
    <Label htmlFor="field" className="label">Field</Label>
    <Input id="field" type="email" className="input" ref={ref} defaultValue="a@b.test" />
    <Textarea aria-label="notes" className="textarea" defaultValue="text" />
    <Checkbox aria-label="check" className="check" defaultChecked />
    <Switch aria-label="switch" className="switch" defaultChecked />
    <Progress aria-label="progress-zero" value={0} className="progress" />
    <Progress aria-label="progress" value={40} />
  </div>);
  expect(ref.current.value).toBe('a@b.test');
  expect(screen.getByLabelText('notes')).toHaveValue('text');
  expect(screen.getByLabelText('progress').firstChild).toHaveStyle('transform: translateX(-60%)');
  expect(screen.getByLabelText('progress-zero').firstChild).toHaveStyle('transform: translateX(-100%)');
});

test('dialog wrappers compose a complete accessible dialog', () => {
  render(<Dialog defaultOpen><DialogTrigger>open</DialogTrigger><DialogContent className="content"><DialogHeader className="header"><DialogTitle>Title</DialogTitle><DialogDescription>Description</DialogDescription></DialogHeader><DialogFooter className="footer">actions</DialogFooter></DialogContent></Dialog>);
  expect(screen.getByRole('dialog')).toHaveClass('content');
  expect(screen.getByText('Title')).toBeInTheDocument();
  fireEvent.click(screen.getByText('Close'));
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});

test('select wrappers open and display grouped content', () => {
  render(<Select defaultValue="a"><SelectTrigger aria-label="choice"><SelectValue /></SelectTrigger><SelectContent position="item-aligned" className="content"><SelectGroup><SelectLabel className="label">Group</SelectLabel><SelectItem value="a" className="item">Alpha</SelectItem><SelectSeparator className="separator" /></SelectGroup></SelectContent></Select>);
  fireEvent.click(screen.getByLabelText('choice'));
  expect(screen.getAllByText('Alpha')).toHaveLength(2);
  render(<Select open><SelectTrigger aria-label="popper choice"><SelectValue placeholder="pick" /></SelectTrigger><SelectContent><SelectItem value="b">Beta</SelectItem></SelectContent></Select>);
  expect(screen.getByText('Beta')).toBeInTheDocument();
});

test('toaster uses the active theme and re-exports toast', () => {
  expect(toast).toBeDefined();
  render(<ThemeProvider><Toaster data-testid="toaster" /></ThemeProvider>);
});

test('tabs wrappers switch visible panels', () => {
  const view = (value) => <Tabs value={value}><TabsList className="list"><TabsTrigger value="a" className="trigger">A</TabsTrigger><TabsTrigger value="b">B</TabsTrigger></TabsList><TabsContent value="a" className="content">Panel A</TabsContent><TabsContent value="b">Panel B</TabsContent></Tabs>;
  const { rerender } = render(view('a'));
  expect(screen.getByText('Panel A')).toBeVisible();
  rerender(view('b'));
  expect(screen.getByText('Panel B')).toBeVisible();
});

test('help tooltip handles mouse, focus, keyboard, positioning and cleanup', () => {
  const { rerender } = render(<HelpTooltip content={null} />);
  expect(screen.queryByRole('button')).not.toBeInTheDocument();
  rerender(<><HelpTooltip content="Help" testId="help" /><HelpTooltip content="Right" side="right" label="right help" /><HelpLabel help="Label help" className="label" testId="label-help">Label</HelpLabel></>);
  const trigger = screen.getByTestId('help');
  trigger.getBoundingClientRect = () => ({ left: 100, right: 120, top: 80, width: 20, height: 20 });
  fireEvent.mouseEnter(trigger);
  expect(screen.getByTestId('help-content')).toHaveTextContent('Help');
  fireEvent(window, new Event('resize'));
  fireEvent.scroll(window);
  fireEvent.keyDown(trigger, { key: 'Enter' });
  expect(screen.getByRole('tooltip')).toBeInTheDocument();
  fireEvent.keyDown(trigger, { key: 'Escape' });
  expect(screen.queryByTestId('help-content')).not.toBeInTheDocument();
  fireEvent.focus(screen.getByLabelText('right help'));
  expect(screen.getByText('Right')).toBeInTheDocument();
  fireEvent.blur(screen.getByLabelText('right help'));
  fireEvent.mouseLeave(trigger);
  rerender(<HelpLabel help="Default label">Default</HelpLabel>);
  expect(screen.getByText('Default')).toBeInTheDocument();
});
