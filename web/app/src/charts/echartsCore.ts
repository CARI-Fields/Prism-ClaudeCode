// Tree-shaken ECharts: register only the chart types + components the report uses,
// instead of `import * as echarts from 'echarts'` (which pulls the whole library).
// Charts/components registered here cover §1 (heatmap/bar/scatter), §2 (line), and
// §3 (context breakdown); add more to the `use([...])` list as later sections need them.
import * as echarts from 'echarts/core';
import { BarChart, HeatmapChart, LineChart, ScatterChart } from 'echarts/charts';
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TooltipComponent,
  VisualMapComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([
  BarChart,
  HeatmapChart,
  LineChart,
  ScatterChart,
  DataZoomComponent,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  VisualMapComponent,
  MarkLineComponent,
  CanvasRenderer,
]);

export { echarts };
export type { ECharts } from 'echarts/core';
