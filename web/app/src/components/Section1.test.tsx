import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { initState } from '../state/appState';
import type { Run } from '../types';

const capturedOptions = vi.hoisted(() => [] as unknown[]);

vi.mock('./EChart', () => ({
  EChart: ({ className, option }: { className?: string; option?: unknown }) => {
    capturedOptions.push(option);
    return <div data-testid="echart" className={className} />;
  },
}));
import { Section1 } from './Section1';

const variant = { key: 'multi_agent', eyebrow: '', title: '', lede: '', conditions: ['single_agent', 'subagents'], tasks: ['coding'] };
const runs = [
  { run_id: 'a', task: 'coding', condition: 'single_agent', rep: 1, success: true, num_requests: 4 },
] as unknown as Run[];

beforeEach(() => { capturedOptions.length = 0; });

describe('Section1', () => {
  it('renders four charts and the metric/overhead selects', () => {
    render(<Section1 variant={variant} state={initState('multi_agent', ['coding'])} runs={runs} onToggle={() => {}} onClear={() => {}} />);
    expect(screen.getAllByTestId('echart')).toHaveLength(4); // matrix/condition/overhead/efficiency
    expect(screen.getByDisplayValue('Mean completion time (s)')).toBeInTheDocument();
  });
  it('hides the overhead panel when single_agent is not in variant.conditions', () => {
    const noBaseline = { ...variant, conditions: ['subagents', 'dynamic_workflow'] };
    render(<Section1 variant={noBaseline} state={initState('multi_agent', ['coding'])} runs={runs} onToggle={() => {}} onClear={() => {}} />);
    expect(screen.getAllByTestId('echart')).toHaveLength(3); // overhead panel gone
  });
  it('metric select is controlled (changing it keeps the new value)', async () => {
    render(<Section1 variant={variant} state={initState('multi_agent', ['coding'])} runs={runs} onToggle={() => {}} onClear={() => {}} />);
    const select = screen.getByDisplayValue('Mean completion time (s)') as HTMLSelectElement;
    await userEvent.selectOptions(select, 'mean_num_requests');
    expect(select.value).toBe('mean_num_requests');
  });
  it('overhead chart has non-null bars when single_agent is deselected but still in variant.conditions', () => {
    const runsWithBoth = [
      { run_id: 'a', task: 'coding', condition: 'single_agent', rep: 1, success: true, num_requests: 4, completion_time_s: 10, total_cost_usd: 0.1, peak_prompt_tokens: 1000, total_cache_read: 500, output_tokens_total: 200 },
      { run_id: 'b', task: 'coding', condition: 'subagents', rep: 1, success: true, num_requests: 8, completion_time_s: 5, total_cost_usd: 0.2, peak_prompt_tokens: 2000, total_cache_read: 1000, output_tokens_total: 400 },
    ] as unknown as Run[];

    // Simulate user deselecting single_agent from the §1 Feature chips
    const s = { ...initState('multi_agent', ['coding']), s1: { condition: ['subagents'], rep: [], agent: [] } };
    render(<Section1 variant={variant} state={s} runs={runsWithBoth} onToggle={() => {}} onClear={() => {}} />);

    // The overhead chart is identified by markLine (only overheadOption adds it)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const overheadOpt = capturedOptions.find((opt: any) => opt?.series?.[0]?.markLine) as any;
    expect(overheadOpt).toBeDefined();
    // data for the displayed condition ('subagents') must be non-null since the baseline survives
    expect(overheadOpt.series[0].data.some((v: unknown) => v !== null)).toBe(true);
  });
});
