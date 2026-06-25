import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { initState } from '../state/appState';
import { Section2 } from './Section2';

const variant = { key: 'multi_agent', eyebrow: '', title: '', lede: '', conditions: ['single_agent', 'subagents'], tasks: ['coding'] };

describe('Section2', () => {
  it('renders Feature/Rollout/Agent chunks and reports toggles with the dimension', async () => {
    const onToggle = vi.fn();
    render(<Section2 variant={variant} state={initState('multi_agent', [])} reps={['r1', 'r2']} agentTypes={['main-agent']} onToggle={onToggle} onClear={() => {}} />);
    expect(screen.getByText('Feature')).toBeInTheDocument();
    expect(screen.getByText('Rollout')).toBeInTheDocument();
    expect(screen.getByText('Agent')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'subagents' }));
    expect(onToggle).toHaveBeenCalledWith('condition', 'subagents');
    await userEvent.click(screen.getByRole('button', { name: 'r2' }));
    expect(onToggle).toHaveBeenCalledWith('rep', 'r2');
  });
});
