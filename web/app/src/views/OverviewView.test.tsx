import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AppStateProvider } from '../state/AppStateProvider';
import { OverviewView } from './OverviewView';
import type { Manifest, Run } from '../types';

vi.mock('../components/EChart', () => ({ EChart: () => <div data-testid="chart" /> }));
const manifest: Manifest = { variants: [{ key: 'r1', eyebrow: 'E', title: 'R1', lede: 'Lede', conditions: ['goal'], tasks: ['coding'] }],
  strategy_desc: { goal: 'Goal strategy' }, task_meta: { coding: { title: 'Coding', measures: 'speed' } }, available: [] };
const runs: Run[] = [{ run_id: 'a', task: 'coding', condition: 'goal', rep: 1, success: true, speedup: null, total_cost_usd: 1, num_requests: 3, cache_hit_ratio: 0.5, quality_score: 0.8, research_rubric_score: null }];
vi.mock('../data/DataContext', () => ({ useData: () => ({ data: { manifest, runs, turns: [], components: [] } }) }));

describe('OverviewView', () => {
  it('renders KPI cards, the strategy legend, and a headline chart', () => {
    render(<AppStateProvider manifest={manifest}><OverviewView /></AppStateProvider>);
    expect(screen.getByText('Runs')).toBeInTheDocument();
    expect(screen.getByText('Goal strategy')).toBeInTheDocument();
    expect(screen.getByTestId('chart')).toBeInTheDocument();
  });
});
