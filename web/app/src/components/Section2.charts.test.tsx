import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { initState, toggleTask } from '../state/appState';
import type { Turn } from '../types';

vi.mock('./EChart', () => ({ EChart: ({ className }: { className?: string }) => <div data-testid="echart" className={className} /> }));
import { Section2 } from './Section2';

const variant = { key: 'multi_agent', eyebrow: '', title: '', lede: '', conditions: ['single_agent', 'subagents'], tasks: ['coding', 'research'] };
const turns = [
  { run_id: 'a', task: 'coding', condition: 'single_agent', rep: 1, request_type: 'main-agent', request_index: 0, input_tokens: 0, cache_read: 100, cache_creation_5m: 0, cache_creation_1h: 0 },
] as unknown as Turn[];

describe('Section2 charts', () => {
  it('renders a cache panel per selected task + the scatter', () => {
    // global task = coding only -> 1 cache panel + 1 scatter = 2 charts
    const state = toggleTask(initState('multi_agent', []), 'coding');
    render(<Section2 variant={variant} state={state} turns={turns} reps={['r1']} agentTypes={['main-agent']} onToggle={() => {}} onClear={() => {}} />);
    expect(screen.getAllByTestId('echart')).toHaveLength(2);
    expect(screen.getByText('coding')).toBeInTheDocument(); // cache-sub label
  });
  it('shows a cache panel for every variant task when no task is selected', () => {
    render(<Section2 variant={variant} state={initState('multi_agent', [])} turns={turns} reps={['r1']} agentTypes={['main-agent']} onToggle={() => {}} onClear={() => {}} />);
    // 2 tasks -> 2 cache panels + 1 scatter = 3 charts
    expect(screen.getAllByTestId('echart')).toHaveLength(3);
  });
});
