import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RunPicker } from './RunPicker';

const download = vi.fn();
vi.mock('./useExportDownload', () => ({
  useExportDownload: () => ({ download, busy: false, error: null }),
}));
vi.mock('../data/DataContext', () => ({
  useData: () => ({
    data: {
      runs: [
        { run_id: 'a1', task: 'coding', condition: 'goal', rep: 1 },
        { run_id: 'b2', task: 'research', condition: 'subagents', rep: 2 },
        { run_id: 'c3', task: 'coding', condition: 'subagents', rep: 1 },
      ],
    },
  }),
}));

describe('RunPicker', () => {
  it('selects a run and downloads with the texts flag', async () => {
    render(<RunPicker />);
    const dl = screen.getByRole('button', { name: /download/i });
    expect(dl).toBeDisabled();
    await userEvent.click(screen.getByLabelText(/coding \/ goal \/ r1 · a1/));
    await userEvent.click(screen.getByRole('checkbox', { name: /include raw context text/i }));
    expect(dl).toBeEnabled();
    await userEvent.click(dl);
    expect(download).toHaveBeenCalledWith(['a1'], true);
  });

  it('select-all selects every visible run', async () => {
    render(<RunPicker />);
    await userEvent.click(screen.getByRole('checkbox', { name: /select all shown/i }));
    await userEvent.click(screen.getByRole('button', { name: /download/i }));
    expect(download).toHaveBeenLastCalledWith(['a1', 'b2', 'c3'], false);
  });

  it('a filter hides non-matching runs', async () => {
    render(<RunPicker />);
    await userEvent.click(screen.getByRole('button', { name: 'goal' })); // Feature chip → condition=goal
    expect(screen.getByLabelText(/· a1/)).toBeInTheDocument();
    expect(screen.queryByLabelText(/· b2/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/· c3/)).not.toBeInTheDocument();
  });

  it('search narrows the list', async () => {
    render(<RunPicker />);
    await userEvent.type(screen.getByRole('searchbox', { name: /search runs/i }), 'c3');
    expect(screen.getByLabelText(/· c3/)).toBeInTheDocument();
    expect(screen.queryByLabelText(/· a1/)).not.toBeInTheDocument();
  });

  it('select-all acts on visible runs and selection persists across filter changes', async () => {
    render(<RunPicker />);
    // Filter A: task=research → only b2 visible; select all shown
    await userEvent.click(screen.getByRole('button', { name: 'research' }));
    expect(screen.queryByLabelText(/· a1/)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('checkbox', { name: /select all shown/i }));
    // Switch to filter B: clear research, set Feature=goal → only a1 visible; select it
    await userEvent.click(screen.getByRole('button', { name: 'research' })); // toggle off
    await userEvent.click(screen.getByRole('button', { name: 'goal' }));
    await userEvent.click(screen.getByLabelText(/coding \/ goal \/ r1 · a1/));
    // Download has both (b2 from filter A persisted, a1 from filter B), in run order
    await userEvent.click(screen.getByRole('button', { name: /download/i }));
    expect(download).toHaveBeenLastCalledWith(['a1', 'b2'], false);
  });
});
