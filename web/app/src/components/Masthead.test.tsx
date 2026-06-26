import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { Manifest } from '../types';
import { Masthead } from './Masthead';

const manifest: Manifest = {
  variants: [
    { key: 'multi_agent', eyebrow: 'CC · exp', title: 'Multi-agent orchestration', lede: 'lede A', conditions: ['single_agent'], tasks: ['coding'] },
    { key: 'long_horizon', eyebrow: 'CC · exp', title: 'Long-horizon persistence', lede: 'lede B', conditions: ['goal'], tasks: ['coding_longhorizon'] },
  ],
  strategy_desc: {}, task_meta: {}, available: [],
};
describe('Masthead', () => {
  it('renders the active variant and a switcher tab per variant', () => {
    render(<Masthead manifest={manifest} activeKey="multi_agent" onSwitch={() => {}} />);
    expect(screen.getByRole('heading', { name: 'Multi-agent orchestration' })).toBeInTheDocument();
    expect(screen.getByText('lede A')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Long-horizon persistence' })).toBeInTheDocument();
  });
  it('marks the active tab and calls onSwitch on click', async () => {
    const onSwitch = vi.fn();
    render(<Masthead manifest={manifest} activeKey="multi_agent" onSwitch={onSwitch} />);
    expect(screen.getByRole('button', { name: 'Multi-agent orchestration' })).toHaveClass('switch-tab', 'on');
    await userEvent.click(screen.getByRole('button', { name: 'Long-horizon persistence' }));
    expect(onSwitch).toHaveBeenCalledWith('long_horizon');
  });
});
