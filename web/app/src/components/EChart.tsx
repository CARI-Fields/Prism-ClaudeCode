import { useEffect, useRef } from 'react';
import { echarts } from '../charts/echartsCore';
import { registerReportThemes, reportThemeName } from '../charts/echartsThemes';
import type { ECharts } from 'echarts/core';

interface EChartProps {
  option: unknown;
  themeMode?: 'light' | 'dark';
  className?: string;
  onClick?: (p: { seriesName: string; dataIndex: number }) => void;
}

export function EChart({ option, themeMode = 'light', className, onClick }: EChartProps) {
  const elRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<ECharts | null>(null);

  useEffect(() => {
    if (!elRef.current) return;
    registerReportThemes();
    const chart = echarts.init(elRef.current, reportThemeName(themeMode));
    chartRef.current = chart;
    chart.setOption(option as Parameters<ECharts['setOption']>[0], true);
    const onResize = () => chart.resize();
    window.addEventListener('resize', onResize);
    return () => { window.removeEventListener('resize', onResize); chart.dispose(); chartRef.current = null; };
  }, [themeMode]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    chartRef.current?.setOption(option as Parameters<ECharts['setOption']>[0], true);
  }, [option]);

  useEffect(() => {
    if (!chartRef.current) return;
    chartRef.current.off('click');
    if (onClick) chartRef.current.on('click', (p) => onClick({ seriesName: String(p.seriesName ?? ''), dataIndex: Number(p.dataIndex) }));
  }, [onClick]);

  return <div ref={elRef} className={className ?? 'chart'} />;
}
