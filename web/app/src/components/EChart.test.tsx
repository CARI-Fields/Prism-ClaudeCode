import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import { EChart } from './EChart';

type ClickPayload = { seriesName?: string; dataIndex?: number };
type ChartStub = {
  setOption: ReturnType<typeof vi.fn>;
  resize: ReturnType<typeof vi.fn>;
  dispose: ReturnType<typeof vi.fn>;
  on: (event: string, cb: (p: ClickPayload) => void) => void;
  off: ReturnType<typeof vi.fn>;
  clickHandler?: (p: ClickPayload) => void;
};

const init = vi.fn();
// Each init() returns a FRESH stub so we can assert the post-re-init instance
// (not a stale one) actually received its click binding.
const charts: ChartStub[] = [];

vi.mock('../charts/echartsCore', () => ({
  echarts: {
    init: (...a: unknown[]) => {
      init(...a);
      const chart: ChartStub = {
        setOption: vi.fn(),
        resize: vi.fn(),
        dispose: vi.fn(),
        on: (event, cb) => { if (event === 'click') chart.clickHandler = cb; },
        off: vi.fn(),
      };
      charts.push(chart);
      return chart;
    },
    registerTheme: vi.fn(),
  },
}));

afterEach(() => { cleanup(); init.mockClear(); charts.length = 0; });

describe('EChart theming', () => {
  it('initializes under the report theme for the active mode', () => {
    render(<EChart option={{}} themeMode="dark" />);
    expect(init).toHaveBeenCalledWith(expect.anything(), 'report-dark');
  });
  it('re-initializes when the theme mode changes', () => {
    const { rerender } = render(<EChart option={{}} themeMode="light" />);
    expect(init).toHaveBeenLastCalledWith(expect.anything(), 'report-light');
    rerender(<EChart option={{}} themeMode="dark" />);
    expect(init).toHaveBeenLastCalledWith(expect.anything(), 'report-dark');
  });
});

describe('EChart option propagation', () => {
  it('applies the option on mount', () => {
    render(<EChart option={{ series: [1] }} />);
    expect(charts[0].setOption).toHaveBeenCalledWith({ series: [1] }, true);
  });
  it('re-applies the option when it changes', () => {
    const { rerender } = render(<EChart option={{ a: 1 }} />);
    rerender(<EChart option={{ a: 2 }} />);
    const latest = charts[charts.length - 1];
    expect(latest.setOption).toHaveBeenLastCalledWith({ a: 2 }, true);
  });
});

describe('EChart click handler', () => {
  it('keeps the click handler live on the instance created by a theme re-init', () => {
    const onClick = vi.fn();
    const { rerender } = render(<EChart option={{}} themeMode="light" onClick={onClick} />);
    rerender(<EChart option={{}} themeMode="dark" onClick={onClick} />);
    // A new instance was created by the re-init, and it must carry the click binding.
    expect(charts).toHaveLength(2);
    const reinited = charts[charts.length - 1];
    reinited.clickHandler?.({ seriesName: 'series-a', dataIndex: 3 });
    expect(onClick).toHaveBeenCalledWith({ seriesName: 'series-a', dataIndex: 3 });
  });
});
