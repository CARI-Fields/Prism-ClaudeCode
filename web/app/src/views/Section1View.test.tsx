import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AppStateProvider } from '../state/AppStateProvider';
import { Section1View } from './Section1View';
import type { Manifest, Run } from '../types';

vi.mock('../components/EChart', () => ({ EChart: () => <div data-testid="chart" /> }));
const manifest: Manifest = {
  variants: [
    {
      key: 'r1',
      eyebrow: '',
      title: 'R1',
      lede: '',
      conditions: ['single_agent', 'goal'],
      tasks: ['coding'],
    },
  ],
  strategy_desc: {},
  task_meta: {},
  available: [],
};
const runs: Run[] = [
  {
    run_id: 'a',
    task: 'coding',
    condition: 'goal',
    rep: 1,
    success: true,
    speedup: 1,
    total_cost_usd: 1,
    num_requests: 3,
    cache_hit_ratio: 0.5,
    quality_score: 0.8,
    research_rubric_score: null,
  },
];
vi.mock('../data/DataContext', () => ({
  useData: () => ({ data: { manifest, runs, turns: [], components: [] } }),
}));

describe('Section1View', () => {
  it('renders comparison + overhead + efficiency panels, with no Experiment matrix (that lives in Overview)', () => {
    render(
      <AppStateProvider manifest={manifest}>
        <Section1View />
      </AppStateProvider>,
    );
    expect(screen.queryByText('Experiment matrix')).not.toBeInTheDocument();
    expect(screen.getByText('Condition comparison')).toBeInTheDocument();
    expect(screen.getByText('Overhead vs single agent')).toBeInTheDocument();
    expect(screen.getByText('Quality vs cost map')).toBeInTheDocument();
    expect(screen.getAllByTestId('chart').length).toBe(3);
  });
});
