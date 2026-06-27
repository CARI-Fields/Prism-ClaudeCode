import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AppStateProvider, useFilter } from '../state/AppStateProvider';
import { Section3View } from './Section3View';
import type { Manifest } from '../types';

vi.mock('../components/EChart', () => ({ EChart: () => <div data-testid="chart" /> }));
vi.mock('../components/ContextTextPanel', () => ({ ContextTextPanel: () => <div /> }));
const manifest: Manifest = { variants: [{ key: 'r1', eyebrow: '', title: 'R1', lede: '', conditions: ['goal', 'subagents'], tasks: ['coding'] }], strategy_desc: {}, task_meta: {}, available: [] };
vi.mock('../data/DataContext', () => ({ useData: () => ({ data: { manifest, runs: [], turns: [], components: [] } }) }));
function Probe() { const f = useFilter(); return <span>s3cond:{f.effective('s3').condition.join(',')}</span>; }

describe('Section3View Feature override', () => {
  it('is single-select: picking a second Feature replaces the first', async () => {
    render(<AppStateProvider manifest={manifest}><Section3View /><Probe /></AppStateProvider>);
    await userEvent.click(screen.getByRole('button', { name: 'goal' }));
    expect(screen.getByText('s3cond:goal')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'subagents' }));
    expect(screen.getByText('s3cond:subagents')).toBeInTheDocument();
  });
});
