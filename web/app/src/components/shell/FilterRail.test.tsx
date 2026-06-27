import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AppStateProvider, useFilter } from '../../state/AppStateProvider';
import { FilterRail } from './FilterRail';
import type { Manifest } from '../../types';

const manifest: Manifest = { variants: [{ key: 'r1', eyebrow: '', title: 'R1', lede: '', conditions: ['goal', 'subagents'], tasks: ['coding'] }],
  strategy_desc: {}, task_meta: {}, available: [] };
vi.mock('../../data/DataContext', () => ({ useData: () => ({ data: { manifest, runs: [{ run_id: 'a', task: 'coding', condition: 'goal', rep: 1 }], turns: [] } }) }));
function Probe() { const f = useFilter(); return <span>cond:{f.filter.condition.join(',')}</span>; }

describe('FilterRail', () => {
  it('toggles a global condition filter', async () => {
    render(<AppStateProvider manifest={manifest}><FilterRail /><Probe /></AppStateProvider>);
    await userEvent.click(screen.getByRole('button', { name: 'goal' }));
    expect(screen.getByText('cond:goal')).toBeInTheDocument();
  });
});
