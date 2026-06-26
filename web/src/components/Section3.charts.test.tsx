import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { initState } from '../state/appState';
import type { Run, Turn } from '../types';

vi.mock('./EChart', () => ({ EChart: ({ className }: { className?: string }) => <div data-testid="echart" className={className} /> }));
import { Section3 } from './Section3';

const variant = { key: 'multi_agent', eyebrow: '', title: '', lede: '', conditions: ['single_agent', 'subagents'], tasks: ['coding'] };
const runs = [
  { run_id: 'a', task: 'coding', condition: 'single_agent', rep: 1 },
  { run_id: 'b', task: 'coding', condition: 'single_agent', rep: 2 },
] as unknown as Run[];
const turns = [
  { run_id: 'a', task: 'coding', condition: 'single_agent', rep: 1, request_type: 'main-agent', request_index: 0, input_tokens: 1, cache_read: 0, cache_creation_5m: 0, cache_creation_1h: 0, output_tokens: 0, ttft_s: 0.1, total_s: 0.2 },
] as unknown as Turn[];

describe('Section3 cost timeline', () => {
  it('renders one block (with a cost-timeline chart) per scoped run', () => {
    render(<Section3 variant={variant} state={initState('multi_agent', ['coding'])} runs={runs} turns={turns} reps={['r1', 'r2']} agentTypes={['main-agent']} onToggle={() => {}} onClear={() => {}} />);
    expect(screen.getAllByTestId('echart')).toHaveLength(2); // 2 runs -> 2 cost-timeline charts
    expect(screen.getByText('a')).toBeInTheDocument(); // run-tag run_id
    expect(screen.getAllByText('Per-Run Request Cost Timeline')).toHaveLength(2);
  });
});
