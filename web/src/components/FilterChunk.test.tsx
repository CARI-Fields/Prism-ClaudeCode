import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { FilterChunk } from './FilterChunk';

describe('FilterChunk', () => {
  it('renders a tag, an "all" toggle, and a chip per item with active state', () => {
    render(<FilterChunk tag="Feature" items={['single_agent', 'subagents']} active={['subagents']} onToggle={() => {}} onClear={() => {}} />);
    expect(screen.getByText('Feature')).toBeInTheDocument();
    expect(screen.getByText('all')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'subagents' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'single_agent' })).toHaveAttribute('aria-pressed', 'false');
  });
  it('calls onToggle(item) and onClear()', async () => {
    const onToggle = vi.fn(); const onClear = vi.fn();
    render(<FilterChunk tag="Feature" items={['single_agent']} active={[]} onToggle={onToggle} onClear={onClear} />);
    await userEvent.click(screen.getByRole('button', { name: 'single_agent' }));
    expect(onToggle).toHaveBeenCalledWith('single_agent');
    await userEvent.click(screen.getByText('all'));
    expect(onClear).toHaveBeenCalled();
  });
});
