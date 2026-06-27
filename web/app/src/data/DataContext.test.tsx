import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import * as client from '../api/client';
import { DataProvider, useData } from './DataContext';
import { TokenGate } from '../components/TokenGate';

function Probe() {
  const { status, data } = useData();
  return (
    <div>
      status:{status} runs:{data ? data.runs.length : 0}
    </div>
  );
}
const manifest = { variants: [], strategy_desc: {}, task_meta: {}, available: [] };
function stubAll(impl: () => Promise<unknown>) {
  for (const fn of [
    'getManifest',
    'getRuns',
    'getTurns',
    'getComponents',
    'getTokenRates',
  ] as const) {
    vi.spyOn(client, fn).mockImplementation(impl as never);
  }
}
afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe('DataProvider', () => {
  it('loads and exposes ready data', async () => {
    vi.spyOn(client, 'getManifest').mockResolvedValue(manifest as never);
    vi.spyOn(client, 'getRuns').mockResolvedValue([{ run_id: 'r1' }] as never);
    vi.spyOn(client, 'getTurns').mockResolvedValue([] as never);
    vi.spyOn(client, 'getComponents').mockResolvedValue([] as never);
    vi.spyOn(client, 'getTokenRates').mockResolvedValue({} as never);
    render(
      <DataProvider>
        <Probe />
      </DataProvider>,
    );
    await waitFor(() => expect(screen.getByText(/status:ready/)).toBeInTheDocument());
    expect(screen.getByText(/runs:1/)).toBeInTheDocument();
  });
  it('enters need-token on 401 and recovers after the gate submits', async () => {
    stubAll(() => Promise.reject(new client.ApiError(401, 'unauthorized')));
    render(
      <DataProvider>
        <TokenGate />
        <Probe />
      </DataProvider>,
    );
    await waitFor(() => expect(screen.getByText(/status:need-token/)).toBeInTheDocument());
    stubAll(() => Promise.resolve([] as never));
    vi.spyOn(client, 'getManifest').mockResolvedValue(manifest as never);
    await userEvent.type(screen.getByLabelText(/access token/i), 'secret123');
    await userEvent.click(screen.getByRole('button', { name: /enter/i }));
    await waitFor(() => expect(screen.getByText(/status:ready/)).toBeInTheDocument());
    expect(localStorage.getItem('cc_report_token')).toBe('secret123');
  });
});
