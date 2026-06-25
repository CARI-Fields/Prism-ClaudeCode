export interface Run {
  run_id: string; task: string; condition: string; rep: number;
  success: boolean; speedup: number | null; total_cost_usd: number | null;
  num_requests: number | null; cache_hit_ratio: number | null;
  quality_score: number | null; research_rubric_score: number | null;
  [key: string]: unknown;
}
export interface Turn {
  run_id: string; task: string; condition: string; rep: number;
  request_index: number; request_type: string | null;
  input_tokens: number; output_tokens: number; cache_read: number;
  cache_creation_5m: number; cache_creation_1h: number;
  ttft_s: number | null; total_s: number | null;
  [key: string]: unknown;
}
export interface Component {
  run_id: string; task: string; condition: string; rep: number;
  request_index: number; request_type: string | null;
  component: string; est_tokens: number; bytes: number;
}
export interface ComponentText {
  run_id: string; request_index: number; component: string;
  request_type: string | null; text: string; truncated: boolean;
  bytes: number; stable: boolean;
}
export interface Variant {
  key: string; eyebrow: string; title: string; lede: string;
  conditions: string[]; tasks: string[];
}
export interface Manifest {
  variants: Variant[];
  strategy_desc: Record<string, string>;
  task_meta: Record<string, { title: string; measures: string }>;
  available: { task: string; condition: string; runs: number }[];
}

export type Dimension = 'condition' | 'rep' | 'agent';
export type ScopeKey = 's1' | 's2' | 's3';
export interface SectionSel { condition: string[]; rep: string[]; agent: string[]; }
export interface AppState {
  report: string;
  task: string[];
  s1: SectionSel; s2: SectionSel; s3: SectionSel;
}
