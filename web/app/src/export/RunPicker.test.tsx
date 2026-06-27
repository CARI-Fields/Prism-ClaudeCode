import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RunPicker } from './RunPicker';

const download = vi.fn();
vi.mock('./useExportDownload', () => ({ useExportDownload: () => ({ download, busy: false, error: null }) }));
vi.mock('../data/DataContext', () => ({
  useData: () => ({ data: { runs: [
    { run_id: 'a1', task: 'coding', condition: 'goal', rep: 1 },
    { run_id: 'b2', task: 'research', condition: 'subagents', rep: 2 },
  ] } }),
}));

describe('RunPicker', () => {
  it('selects runs and downloads with the texts flag', async () => {
    render(<RunPicker />);
    const dl = screen.getByRole('button', { name: /download/i });
    expect(dl).toBeDisabled();                                   // nothing selected
    await userEvent.click(screen.getByLabelText(/coding \/ goal \/ r1 · a1/));
    await userEvent.click(screen.getByRole('checkbox', { name: /include raw context text/i }));
    expect(dl).toBeEnabled();
    await userEvent.click(dl);
    expect(download).toHaveBeenCalledWith(['a1'], true);
  });

  it('select-all toggles every run', async () => {
    render(<RunPicker />);
    await userEvent.click(screen.getByRole('checkbox', { name: /select all/i }));
    await userEvent.click(screen.getByRole('button', { name: /download/i }));
    expect(download).toHaveBeenLastCalledWith(['a1', 'b2'], false);
  });
});
