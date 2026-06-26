import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { Run } from '../types';
import { KpiBand } from './KpiBand';

describe('KpiBand', () => {
  it('renders five labelled cards with computed run count', () => {
    const runs = [{ num_requests: 4, total_cost_usd: 0.2, quality_score: 2, cache_hit_ratio: 0.5 }] as unknown as Run[];
    render(<KpiBand runs={runs} />);
    expect(screen.getByText('Runs')).toBeInTheDocument();
    expect(screen.getByText('Mean cache hit')).toBeInTheDocument();
    expect(screen.getByText('50%')).toBeInTheDocument();
    expect(document.querySelectorAll('.kpi')).toHaveLength(5);
  });
});
