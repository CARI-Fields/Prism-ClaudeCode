// Mirrors analysis/echarts_report.py conditionColors / sourceColors.
export const CONDITION_COLORS: Record<string, string> = {
  single_agent: '#3b5bdb', goal: '#2f9e44', subagents: '#0c8599',
  ralph_loop: '#e8590c', dynamic_workflow: '#7048e8', loop_dynamic: '#c2255c',
};
export const SOURCE_COLORS: Record<string, string> = {
  'base system prompt': '#3b5bdb', 'builtin tool definitions': '#1098ad',
  'MCP / extension tool definitions': '#15aabf', 'custom agent definitions': '#f76707',
  'CLAUDE.md / project instructions': '#e8590c', 'skills listing': '#7048e8',
  'invoked skill bodies': '#9775fa', 'auto memory': '#2f9e44',
  'hooks / system reminders': '#f59f00', 'user input': '#c2255c',
  'assistant / conversation history': '#868e96', 'tool results / file reads': '#4263eb',
  'subagent summaries': '#a61e4d', 'uncategorized context': '#adb5bd',
};
const PALETTE = ['#3b5bdb', '#0c8599', '#e8590c', '#7048e8', '#c2255c', '#1098ad', '#f59f00'];
export function conditionColor(condition: string, fallbackIndex = 0): string {
  return CONDITION_COLORS[condition] ?? PALETTE[fallbackIndex % PALETTE.length];
}
