import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ExportControl } from './ExportControl';

vi.mock('./RunPicker', () => ({ RunPicker: () => <div>RUN PICKER</div> }));

describe('ExportControl', () => {
  it('opens a dialog with the run picker', async () => {
    render(<ExportControl />);
    expect(screen.queryByText('RUN PICKER')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /export traces/i }));
    expect(await screen.findByText('RUN PICKER')).toBeInTheDocument();
  });
});
