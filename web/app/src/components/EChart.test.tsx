import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import { EChart } from './EChart';

const init = vi.fn();
vi.mock('../charts/echartsCore', () => {
  const chart = { setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn(), on: vi.fn(), off: vi.fn() };
  return { echarts: { init: (...a: unknown[]) => { init(...a); return chart; }, registerTheme: vi.fn() } };
});

afterEach(() => { cleanup(); init.mockClear(); });

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
