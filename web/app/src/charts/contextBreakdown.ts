import type { Component, Turn } from '../types';
import type { Ordered } from './ordered';
import { promptTokens } from './cacheTimeline';
import { SOURCE_COLORS } from '../theme';

export interface ComposeMode {
  key: 'context' | 'source' | 'token';
  bucketOf: (c: string) => string | null;
  order: string[];
  colors: Record<string, string>;
  clickable: boolean;
}
const n = (v: unknown): number => (typeof v === 'number' && Number.isFinite(v) ? v : 0);

const CONTEXT_BUCKET: Record<string, string> = {
  'base system prompt': 'System prompt',
  'builtin tool definitions': 'System tools',
  'MCP / extension tool definitions': 'MCP tools',
  'custom agent definitions': 'Custom agents',
  'auto memory': 'Memory files',
  'CLAUDE.md / project instructions': 'Memory files',
  'skills listing': 'Skills',
};
const SOURCE_ORDER = [
  'base system prompt', 'builtin tool definitions', 'MCP / extension tool definitions',
  'custom agent definitions', 'CLAUDE.md / project instructions', 'skills listing',
  'invoked skill bodies', 'auto memory', 'hooks / system reminders', 'user input',
  'assistant / conversation history', 'tool results / file reads', 'subagent summaries', 'uncategorized context',
];
const TOKEN_BUCKET: Record<string, string> = {
  'input tokens': 'input', 'prefix cache read': 'cache read',
  'prefix cache write 5m': 'cache write', 'prefix cache write 1h': 'cache write',
};

export const COMPOSE_MODES: Record<'context' | 'source' | 'token', ComposeMode> = {
  context: {
    key: 'context', bucketOf: (c) => CONTEXT_BUCKET[c] ?? 'Messages',
    order: ['System prompt', 'System tools', 'MCP tools', 'Custom agents', 'Memory files', 'Skills', 'Messages'],
    colors: { 'System prompt': '#3b5bdb', 'System tools': '#0c8599', 'MCP tools': '#15aabf', 'Custom agents': '#f76707', 'Memory files': '#2f9e44', Skills: '#7048e8', Messages: '#495057' },
    clickable: false,
  },
  source: { key: 'source', bucketOf: (c) => c, order: SOURCE_ORDER, colors: SOURCE_COLORS, clickable: true },
  token: {
    key: 'token', bucketOf: (c) => TOKEN_BUCKET[c] ?? null,
    order: ['input', 'cache read', 'cache write'],
    colors: { input: '#3b5bdb', 'cache read': '#0c8599', 'cache write': '#e8590c' },
    clickable: false,
  },
};

export interface Breakdown {
  buckets: string[]; byKey: Map<string, number>; colors: Record<string, string>; clickable: boolean;
}

export function breakdownData(mode: ComposeMode, rowsForRun: Turn[], componentsForRun: Component[]): Breakdown {
  const byKey = new Map<string, number>();
  const add = (pos: number, bucket: string | null, tokens: number) => {
    if (bucket == null) return;
    byKey.set(`${pos}:${bucket}`, (byKey.get(`${pos}:${bucket}`) ?? 0) + tokens);
  };
  if (mode.key === 'token') {
    rowsForRun.forEach((t, pos) => {
      add(pos, 'input', n(t.input_tokens));
      add(pos, 'cache read', n(t.cache_read));
      add(pos, 'cache write', n(t.cache_creation_5m) + n(t.cache_creation_1h));
    });
  } else {
    const posOf = new Map<number, number>();
    rowsForRun.forEach((t, i) => posOf.set(t.request_index, i));
    for (const c of componentsForRun) {
      const pos = posOf.get(c.request_index);
      if (pos == null) continue;
      add(pos, mode.bucketOf(c.component), n(c.est_tokens));
    }
  }
  const buckets = mode.order.filter((b) => [...byKey.keys()].some((k) => k.endsWith(`:${b}`)));
  return { buckets, byKey, colors: mode.colors, clickable: mode.clickable };
}

export function hitRateData(rowsForRun: Turn[], o: Ordered): (number | null)[] {
  return o.indexes.map((pos) => {
    const t = rowsForRun[pos];
    if (!t) return null;
    const ctx = promptTokens(t);
    return ctx > 0 ? (100 * n(t.cache_read)) / ctx : null;
  });
}
