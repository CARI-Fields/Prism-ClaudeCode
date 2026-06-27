import { describe, expect, it, beforeEach } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import { AppStateProvider, useTheme, useView, useFilter } from './AppStateProvider';
import type { Manifest } from '../types';

const manifest: Manifest = { variants: [{ key: 'r1', eyebrow: '', title: 'R1', lede: '', conditions: ['goal'], tasks: ['coding'] }],
  strategy_desc: {}, task_meta: {}, available: [] };

function Probe() {
  const { mode, toggle } = useTheme();
  const { view, setView } = useView();
  return (<div>
    <span>mode:{mode}</span><span>view:{view}</span>
    <button onClick={toggle}>t</button><button onClick={() => setView('s2')}>v</button>
  </div>);
}

function FilterProbe() {
  const { effective, setOverrideSingle } = useFilter();
  const cond = effective('s3').condition;
  return (<div>
    <span>s3cond:{cond.join(',')}</span>
    <button onClick={() => setOverrideSingle('s3', 'condition', 'goal')}>pin-goal</button>
  </div>);
}

beforeEach(() => { window.location.hash = ''; localStorage.clear(); });

describe('AppStateProvider', () => {
  it('defaults to overview + light and toggles theme + view', () => {
    render(<AppStateProvider manifest={manifest}><Probe /></AppStateProvider>);
    expect(screen.getByText('mode:light')).toBeInTheDocument();
    expect(screen.getByText('view:overview')).toBeInTheDocument();
    expect(document.querySelector('.app-root')).not.toHaveClass('bp5-dark');
    act(() => screen.getByText('t').click());
    expect(screen.getByText('mode:dark')).toBeInTheDocument();
    expect(document.querySelector('.app-root')).toHaveClass('bp5-dark');
    expect(window.location.hash).toContain('theme=dark');
    act(() => screen.getByText('v').click());
    expect(window.location.hash).toContain('view=s2');
  });
  it('hydrates from the URL hash', () => {
    window.location.hash = '#report=r1&theme=dark&view=s2';
    render(<AppStateProvider manifest={manifest}><Probe /></AppStateProvider>);
    expect(screen.getByText('mode:dark')).toBeInTheDocument();
    expect(screen.getByText('view:s2')).toBeInTheDocument();
  });
  it('hydrates §3 Feature override from s3cond in URL hash', () => {
    window.location.hash = '#report=r1&s3cond=goal';
    render(<AppStateProvider manifest={manifest}><FilterProbe /></AppStateProvider>);
    expect(screen.getByText('s3cond:goal')).toBeInTheDocument();
  });
  it('write-through: §3 Feature override updates URL hash', () => {
    render(<AppStateProvider manifest={manifest}><FilterProbe /></AppStateProvider>);
    act(() => screen.getByText('pin-goal').click());
    expect(window.location.hash).toContain('s3cond=goal');
  });
});
