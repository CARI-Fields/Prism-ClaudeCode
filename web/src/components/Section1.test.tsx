import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { initState } from '../state/appState';
import type { Run } from '../types';

vi.mock('./EChart', () => ({ EChart: ({ className }: { className?: string }) => <div data-testid="echart" className={className} /> }));
import { Section1 } from './Section1';

const variant = { key: 'multi_agent', eyebrow: '', title: '', lede: '', conditions: ['single_agent', 'subagents'], tasks: ['coding'] };
const runs = [
  { run_id: 'a', task: 'coding', condition: 'single_agent', rep: 1, success: true, num_requests: 4 },
] as unknown as Run[];

describe('Section1', () => {
  it('renders four charts and the metric/overhead selects', () => {
    render(<Section1 variant={variant} state={initState('multi_agent', ['coding'])} runs={runs} onToggle={() => {}} onClear={() => {}} />);
    expect(screen.getAllByTestId('echart')).toHaveLength(4); // matrix/condition/overhead/efficiency
    expect(screen.getByDisplayValue('Mean completion time (s)')).toBeInTheDocument();
  });
  it('hides the overhead panel when single_agent is not selected', () => {
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
});
