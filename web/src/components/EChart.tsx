import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

export function EChart({ option, className }: { option: unknown; className?: string }) {
  const elRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!elRef.current) return;
    const chart = echarts.init(elRef.current);
    chartRef.current = chart;
    const onResize = () => chart.resize();
    window.addEventListener('resize', onResize);
    return () => { window.removeEventListener('resize', onResize); chart.dispose(); chartRef.current = null; };
  }, []);

  useEffect(() => {
    chartRef.current?.setOption(option as echarts.EChartsOption, true);
  }, [option]);

  return <div ref={elRef} className={className ?? 'chart'} />;
}
