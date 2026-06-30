import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AppStateProvider } from '../state/AppStateProvider';
import { Section2View } from './Section2View';
import type { Manifest } from '../types';

vi.mock('../components/EChart', () => ({ EChart: () => <div data-testid="chart" /> }));
const manifest: Manifest = {
  variants: [
    { key: 'r1', eyebrow: '', title: 'R1', lede: '', conditions: ['goal'], tasks: ['coding'] },
  ],
  strategy_desc: {},
  task_meta: {},
  available: [],
};
vi.mock('../data/DataContext', () => ({
  useData: () => ({
    data: {
      manifest,
      runs: [],
      turns: [
        {
          run_id: 'a',
          task: 'coding',
          condition: 'goal',
          rep: 1,
          request_index: 0,
          request_type: 'main-agent',
          input_tokens: 1,
          output_tokens: 1,
          cache_read: 1,
          cache_creation_5m: 0,
          cache_creation_1h: 0,
          ttft_s: null,
          total_s: null,
        },
      ],
      components: [],
    },
  }),
}));

describe('Section2View', () => {
  it('renders the distribution panels', () => {
    render(
      <AppStateProvider manifest={manifest}>
        <Section2View />
      </AppStateProvider>,
    );
    expect(screen.getByText(/Prefix cache hit rate \(accumulated\)/)).toBeInTheDocument();
    expect(screen.getAllByTestId('chart')).toHaveLength(2);
  });
});
