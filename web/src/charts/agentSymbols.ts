// Verbatim maps from analysis/echarts_report.py:1010,1021-1030,1091-1096
// -------------------------------------------------------------------

export const REP_LINE_TYPES: Record<number, string> = { 1: 'solid', 2: 'dashed', 3: 'dotted' };

export const REQUEST_TYPE_SYMBOLS: Record<string, string> = {
  'main-agent': 'circle',
  'security-monitor': 'diamond',
  'workflow-subagent': 'triangle',
  'task-subagent': 'rect',
  'web-search-subagent':
    'path://M50,5 L60.6,35.4 L92.8,36.1 L67.1,55.6 L76.4,86.4 L50,68 L23.6,86.4 L32.9,55.6 L7.2,36.1 L39.4,35.4 Z',
  'web-fetch-subagent': 'arrow',
  'stop-condition-eval': 'pin',
  'subagent-internal': 'roundRect',
};

export function agentDotSpec(type: string): { size: number; hollow: boolean } {
  const t = type || 'main-agent';
  if (t === 'main-agent') return { size: 6, hollow: false };      // solid circle
  if (t === 'security-monitor') return { size: 7, hollow: true }; // hollow diamond
  return { size: 8, hollow: false };                              // subagents -- own shape
}
