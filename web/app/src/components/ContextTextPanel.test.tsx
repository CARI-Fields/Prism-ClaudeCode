import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import * as client from '../api/client';
import { ContextTextPanel } from './ContextTextPanel';

afterEach(() => {
  vi.restoreAllMocks();
});

describe('ContextTextPanel', () => {
  it('shows the default prompt when nothing is selected', () => {
    render(<ContextTextPanel runId="a" selection={null} />);
    expect(screen.getByText(/click a stacked segment/i)).toBeInTheDocument();
  });
  it('lazily fetches and shows the selected component text (stable key)', async () => {
    vi.spyOn(client, 'getComponentTexts').mockResolvedValue([
      {
        run_id: 'a',
        request_index: 0,
        component: 'base system prompt',
        request_type: 'main-agent',
        text: 'SYS',
        truncated: false,
        bytes: 3,
        stable: true,
      },
    ] as never);
    render(
      <ContextTextPanel
        runId="a"
        selection={{
          component: 'base system prompt',
          requestIndex: 5,
          type: 'main-agent',
          tokens: 100,
        }}
      />,
    );
    await waitFor(() => expect(screen.getByText('SYS')).toBeInTheDocument()); // resolved via run|*|component (stable)
    expect(client.getComponentTexts).toHaveBeenCalledWith('a');
  });
});
