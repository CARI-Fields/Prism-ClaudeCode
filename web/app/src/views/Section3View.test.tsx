import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AppStateProvider, useFilter } from '../state/AppStateProvider';
import { Section3View } from './Section3View';
import type { Manifest } from '../types';

// AppStateProvider persists filter state to the URL hash; reset it so tests don't leak.
beforeEach(() => {
  window.location.hash = '';
});

vi.mock('../components/EChart', () => ({ EChart: () => <div data-testid="chart" /> }));
vi.mock('../components/ContextTextPanel', () => ({ ContextTextPanel: () => <div /> }));
const manifest: Manifest = {
  variants: [
    {
      key: 'r1',
      eyebrow: '',
      title: 'R1',
      lede: '',
      conditions: ['goal', 'subagents'],
      tasks: ['coding'],
    },
  ],
  strategy_desc: {},
  task_meta: {},
  available: [],
};
vi.mock('../data/DataContext', () => ({
  useData: () => ({ data: { manifest, runs: [], turns: [], components: [] } }),
}));

function Probe() {
  const f = useFilter();
  return (
    <div>
      <span>s3cond:{f.effective('s3').condition.join(',')}</span>
      <button onClick={() => f.toggle('condition', 'goal')}>add-goal</button>
      <button onClick={() => f.toggle('condition', 'subagents')}>add-subagents</button>
    </div>
  );
}

describe('Section3View Feature filter', () => {
  it('reads the global (left-rail) Feature filter and supports multi-select', async () => {
    render(
      <AppStateProvider manifest={manifest}>
        <Section3View />
        <Probe />
      </AppStateProvider>,
    );
    expect(screen.getByText('s3cond:')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'add-goal' }));
    expect(screen.getByText('s3cond:goal')).toBeInTheDocument();
    // Multi-select: a second Feature adds to the selection, it does not replace it.
    await userEvent.click(screen.getByRole('button', { name: 'add-subagents' }));
    expect(screen.getByText('s3cond:goal,subagents')).toBeInTheDocument();
  });

  it('no longer renders an in-view Feature selector (merged into the rail)', () => {
    render(
      <AppStateProvider manifest={manifest}>
        <Section3View />
      </AppStateProvider>,
    );
    expect(screen.queryByText('Feature (single run)')).not.toBeInTheDocument();
  });
});
