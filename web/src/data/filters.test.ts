import { describe, expect, it } from 'vitest';
import type { Run, SectionSel, Turn } from '../types';
import { presentAgentTypes, scopeRuns, scopeTurns } from './filters';

const runs = [
  { run_id: 'a', task: 'coding', condition: 'single_agent', rep: 1 },
  { run_id: 'b', task: 'coding', condition: 'subagents', rep: 2 },
  { run_id: 'c', task: 'research', condition: 'single_agent', rep: 1 },
] as unknown as Run[];
const turns = [
  { run_id: 'a', task: 'coding', condition: 'single_agent', rep: 1, request_type: 'main-agent' },
  { run_id: 'b', task: 'coding', condition: 'subagents', rep: 2, request_type: 'task-subagent' },
  { run_id: 'b', task: 'coding', condition: 'subagents', rep: 2, request_type: null },
] as unknown as Turn[];
const sec = (o: Partial<SectionSel>): SectionSel => ({ condition: [], rep: [], agent: [], ...o });

describe('filters', () => {
  it('empty section + empty task returns all', () => {
    expect(scopeRuns(runs, [], sec({}))).toHaveLength(3);
  });
  it('global task + section condition narrow runs', () => {
    expect(scopeRuns(runs, ['coding'], sec({ condition: ['subagents'] })).map((r) => r.run_id)).toEqual(['b']);
  });
  it('rep matches r-prefixed token', () => {
    expect(scopeRuns(runs, [], sec({ rep: ['r1'] })).map((r) => r.run_id)).toEqual(['a', 'c']);
  });
  it('scopeTurns filters by agent and drops null when agent set', () => {
    expect(scopeTurns(turns, [], sec({ agent: ['task-subagent'] })).map((t) => t.run_id)).toEqual(['b']);
  });
  it('presentAgentTypes returns sorted distinct non-null', () => {
    expect(presentAgentTypes(turns)).toEqual(['main-agent', 'task-subagent']);
  });
});
