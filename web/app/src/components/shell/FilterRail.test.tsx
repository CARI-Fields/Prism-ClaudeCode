import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AppStateProvider, useFilter } from '../../state/AppStateProvider';
import { FilterRail } from './FilterRail';
import type { Manifest } from '../../types';

// AppStateProvider persists filter state to the URL hash; reset it so tests don't leak.
beforeEach(() => {
  window.location.hash = '';
});

const manifest: Manifest = {
  variants: [
    {
      key: 'r1',
      eyebrow: '',
      title: 'R1',
      lede: '',
      conditions: ['goal', 'subagents'],
      tasks: ['coding_longhorizon', 'research_longhorizon'],
    },
  ],
  strategy_desc: {},
  task_meta: {},
  available: [],
};
vi.mock('../../data/DataContext', () => ({
  useData: () => ({
    data: {
      manifest,
      runs: [{ run_id: 'a', task: 'coding_longhorizon', condition: 'goal', rep: 1 }],
      turns: [],
    },
  }),
}));
function Probe() {
  const f = useFilter();
  return (
    <span>
      cond:{f.filter.condition.join(',')}|task:{f.filter.task.join(',')}
    </span>
  );
}

describe('FilterRail', () => {
  it('toggles a global condition filter', async () => {
    render(
      <AppStateProvider manifest={manifest}>
        <FilterRail />
        <Probe />
      </AppStateProvider>,
    );
    await userEvent.click(screen.getByRole('button', { name: 'goal' }));
    expect(screen.getByText('cond:goal|task:')).toBeInTheDocument();
  });

  it('shows long-horizon tasks by their bare domain name but filters by the full key', async () => {
    render(
      <AppStateProvider manifest={manifest}>
        <FilterRail />
        <Probe />
      </AppStateProvider>,
    );
    // Displayed label is the bare domain ("coding"), not the raw "coding_longhorizon" key.
    const codingChip = screen.getByRole('button', { name: 'coding' });
    expect(screen.queryByRole('button', { name: 'coding_longhorizon' })).not.toBeInTheDocument();
    // …but the toggle still filters by the real task key.
    await userEvent.click(codingChip);
    expect(screen.getByText('cond:|task:coding_longhorizon')).toBeInTheDocument();
  });
});
