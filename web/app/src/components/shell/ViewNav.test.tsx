import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AppStateProvider } from '../../state/AppStateProvider';
import { ViewNav } from './ViewNav';
import { ViewCanvas } from './ViewCanvas';
import type { Manifest } from '../../types';

// ViewCanvas renders <ScopeNote>, which reads the data context; this test only
// exercises view switching, so stub it out (no data → ScopeNote renders nothing).
vi.mock('../../data/DataContext', () => ({ useData: () => ({ data: undefined }) }));

const manifest: Manifest = { variants: [{ key: 'r1', eyebrow: '', title: 'R1', lede: '', conditions: ['goal'], tasks: ['coding'] }], strategy_desc: {}, task_meta: {}, available: [] };
const views = { overview: <p>OVERVIEW</p>, s1: <p>S1</p>, s2: <p>S2</p>, s3: <p>S3</p> };

describe('ViewNav + ViewCanvas', () => {
  it('switches the active view', async () => {
    render(<AppStateProvider manifest={manifest}><ViewNav /><ViewCanvas views={views} /></AppStateProvider>);
    expect(screen.getByText('OVERVIEW')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('tab', { name: /Distributions/ }));
    expect(screen.getByText('S2')).toBeInTheDocument();
  });
});
