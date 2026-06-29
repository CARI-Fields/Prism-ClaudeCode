import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AppStateProvider, useTheme } from '../../state/AppStateProvider';
import { TopBar } from './TopBar';
import type { Manifest } from '../../types';

vi.mock('../../data/DataContext', () => ({ useData: () => ({ reload: vi.fn() }) }));
const manifest: Manifest = { variants: [
  { key: 'r1', eyebrow: '', title: 'Report One', lede: '', conditions: ['goal'], tasks: ['coding'] },
  { key: 'r2', eyebrow: '', title: 'Report Two', lede: '', conditions: ['goal'], tasks: ['coding'] }],
  strategy_desc: {}, task_meta: {}, available: [] };
function Mode() { return <span>mode:{useTheme().mode}</span>; }

describe('TopBar', () => {
  it('shows variant tabs and toggles theme', async () => {
    render(<AppStateProvider manifest={manifest}><TopBar manifest={manifest} /><Mode /></AppStateProvider>);
    expect(screen.getByRole('tab', { name: 'Report One' })).toBeInTheDocument();
    expect(screen.getByText('mode:light')).toBeInTheDocument();
    // The theme toggle is a minimal icon button whose aria-label names the action.
    await userEvent.click(screen.getByRole('button', { name: 'Switch to dark theme' }));
    expect(screen.getByText('mode:dark')).toBeInTheDocument();
  });
});
