import { render } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

const inst = { setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn() };
vi.mock('echarts', () => ({ init: vi.fn(() => inst) }));

import * as echarts from 'echarts';
import { EChart } from './EChart';

afterEach(() => { vi.clearAllMocks(); });

describe('EChart', () => {
  it('inits on mount and applies the option', () => {
    render(<EChart option={{ series: [] }} className="chart" />);
    expect(echarts.init).toHaveBeenCalledTimes(1);
    expect(inst.setOption).toHaveBeenCalledWith({ series: [] }, true);
  });
  it('re-applies the option when it changes', () => {
    const { rerender } = render(<EChart option={{ a: 1 }} />);
    rerender(<EChart option={{ a: 2 }} />);
    expect(inst.setOption).toHaveBeenLastCalledWith({ a: 2 }, true);
  });
});
