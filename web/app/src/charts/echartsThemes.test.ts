import { describe, expect, it } from 'vitest';
import { REPORT_LIGHT, REPORT_DARK, reportThemeName } from './echartsThemes';
import { axisLabelStyle, valueAxis } from './echartsTheme';

describe('report ECharts themes', () => {
  it('names themes by mode', () => {
    expect(reportThemeName('light')).toBe('report-light');
    expect(reportThemeName('dark')).toBe('report-dark');
  });
  it('light and dark differ in neutral surfaces', () => {
    expect(REPORT_LIGHT.backgroundColor).toBe('transparent');
    expect(REPORT_DARK.backgroundColor).toBe('transparent');
    expect(REPORT_LIGHT.textStyle.color).not.toBe(REPORT_DARK.textStyle.color);
    expect(REPORT_LIGHT.valueAxis.splitLine.lineStyle.color).not.toBe(
      REPORT_DARK.valueAxis.splitLine.lineStyle.color,
    );
  });
  it('builders no longer hardcode neutral colors (theme supplies them)', () => {
    expect('color' in axisLabelStyle()).toBe(false);
    expect((valueAxis() as any).splitLine).toBeUndefined();
  });
});
