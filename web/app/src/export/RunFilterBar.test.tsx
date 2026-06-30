import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RunFilterBar } from './RunFilterBar';

const domains = {
  task: ['coding', 'research'],
  condition: ['goal', 'subagents'],
  rep: ['r1', 'r2'],
};
const filter = { task: [], condition: [], rep: [], query: '' };

describe('RunFilterBar', () => {
  it('renders chip groups + search and reports changes', async () => {
    const onToggle = vi.fn();
    const onClear = vi.fn();
    const onQuery = vi.fn();
    render(
      <RunFilterBar
        domains={domains}
        filter={filter}
        onToggle={onToggle}
        onClear={onClear}
        onQuery={onQuery}
      />,
    );
    await userEvent.click(screen.getByRole('button', { name: 'coding' }));
    expect(onToggle).toHaveBeenCalledWith('task', 'coding');
    await userEvent.click(screen.getByRole('button', { name: 'goal' }));
    expect(onToggle).toHaveBeenCalledWith('condition', 'goal');
    await userEvent.click(screen.getByRole('button', { name: 'r2' }));
    expect(onToggle).toHaveBeenCalledWith('rep', 'r2');
    await userEvent.type(screen.getByRole('searchbox', { name: /search runs/i }), 'x');
    expect(onQuery).toHaveBeenCalledWith('x');
  });
});
