import React from 'react';
import { act, render, renderHook, screen } from '@testing-library/react';
import { cn } from './utils';
import { useFlowHistory } from '../hooks/useFlowHistory';
import { ThemeProvider, useTheme } from '../contexts/ThemeContext';

test('cn merges conditional Tailwind classes', () => {
  expect(cn('px-1', false && 'hidden', 'px-2')).toBe('px-2');
});

test('flow history covers empty, bounded, undo, redo, and clear states', () => {
  const defaults = renderHook(() => useFlowHistory());
  act(() => defaults.result.current.push({ n: 0 }));
  expect(defaults.result.current.canUndo).toBe(true);
  const { result } = renderHook(() => useFlowHistory(2));
  expect(result.current.undo({})).toBeNull();
  expect(result.current.redo({})).toBeNull();
  act(() => result.current.push(null));
  act(() => result.current.push({ n: 1 }));
  act(() => result.current.push({ n: 2 }));
  act(() => result.current.push({ n: 3 }));
  expect(result.current.canUndo).toBe(true);
  let previous;
  act(() => { previous = result.current.undo({ n: 4 }); });
  expect(previous).toEqual({ n: 3 });
  let next;
  act(() => { next = result.current.redo({ n: 2 }); });
  expect(next).toEqual({ n: 4 });
  act(() => result.current.clear());
  expect(result.current.canUndo).toBe(false);
  expect(result.current.canRedo).toBe(false);
});

function ThemeConsumer() {
  const { theme, isDark, toggleTheme, setTheme } = useTheme();
  return <><span>{theme}:{String(isDark)}</span><button onClick={toggleTheme}>toggle</button><button onClick={() => setTheme('light')}>light</button></>;
}

test('theme provider initializes, toggles, persists, and updates root class', () => {
  localStorage.setItem('gerdoctor_theme', 'dark');
  render(<ThemeProvider><ThemeConsumer /></ThemeProvider>);
  expect(screen.getByText('dark:true')).toBeInTheDocument();
  expect(document.documentElement).toHaveClass('dark');
  act(() => screen.getByText('toggle').click());
  expect(screen.getByText('light:false')).toBeInTheDocument();
  expect(document.documentElement).not.toHaveClass('dark');
  act(() => screen.getByText('toggle').click());
  expect(screen.getByText('dark:true')).toBeInTheDocument();
  act(() => screen.getByText('light').click());
  expect(localStorage.getItem('gerdoctor_theme')).toBe('light');
});

test('theme defaults to light when no preference exists', () => {
  localStorage.removeItem('gerdoctor_theme');
  render(<ThemeProvider><ThemeConsumer /></ThemeProvider>);
  expect(screen.getByText('light:false')).toBeInTheDocument();
});

test('useTheme rejects consumers outside the provider', () => {
  const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
  expect(() => renderHook(() => useTheme())).toThrow('useTheme must be used within ThemeProvider');
  spy.mockRestore();
});
