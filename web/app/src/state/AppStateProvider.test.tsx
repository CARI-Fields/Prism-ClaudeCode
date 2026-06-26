import { describe, expect, it, beforeEach } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import { AppStateProvider, useTheme, useView } from './AppStateProvider';
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
});
