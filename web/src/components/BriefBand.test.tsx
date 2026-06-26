import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { Manifest, Variant } from '../types';
import { BriefBand } from './BriefBand';

const variant: Variant = {
  key: 'multi_agent',
  eyebrow: '',
  title: '',
  lede: '',
  conditions: ['single_agent', 'subagents'],
  tasks: ['coding'],
};

const manifest: Manifest = {
  variants: [variant],
  strategy_desc: { single_agent: 'baseline desc', subagents: 'sub desc' },
  task_meta: { coding: { title: 'Fused kernel', measures: 'measures text' } },
  available: [],
};

describe('BriefBand', () => {
  it('renders the §0 band-label and one brief card per task', () => {
    render(<BriefBand variant={variant} manifest={manifest} />);
    expect(screen.getByText('Tasks & strategies')).toBeInTheDocument();
    expect(screen.getByText('§0')).toBeInTheDocument();
    expect(document.querySelectorAll('.brief')).toHaveLength(1);
    expect(screen.getByText('Fused kernel')).toBeInTheDocument();
  });

  it('shows each condition in the strategy legend with single_agent carrying a baseline tag', () => {
    render(<BriefBand variant={variant} manifest={manifest} />);
    expect(screen.getByText('single_agent')).toBeInTheDocument();
    expect(screen.getByText('subagents')).toBeInTheDocument();
    const baselineTags = document.querySelectorAll('.strat-base');
    expect(baselineTags).toHaveLength(1);
    expect(baselineTags[0].textContent).toBe('baseline');
  });
});
